"""
Final Settlement Service
========================
All business logic lives here — routers stay thin.

Key responsibilities:
  • Auto-generate settlement_code (FS-YYYY-NNNN)
  • Full recalculate()  — recomputes every sub-block and header totals
  • Workflow transitions: Draft → Pending → Approved → Paid / Cancelled
  • Approval log insertion on every status change
  • Timeline milestone management
  • Asset penalty computation
  • Gratuity eligibility check (≥ 5 completed years)
  • Leave encashment (earned leave only, unless policy overrides)
  • Notice period shortfall recovery
  • Document generation stubs (Form16, Form19, Form10C, letters)
  • Export helpers (PDF/CSV) — returns raw bytes for the router to stream
"""

from __future__ import annotations

import calendar
import io
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from model.Payroll.final_settlement import (
    ApprovalAction,
    AssetCondition,
    AssetReturnStatus,
    FinalSettlement,
    SettlementApprovalLog,
    SettlementAsset,
    SettlementBonus,
    SettlementDeduction,
    SettlementDocument,
    SettlementGratuity,
    SettlementLeaveEncashment,
    SettlementNoticePeriod,
    SettlementPayment,
    SettlementSalaryBreakdown,
    SettlementStatus,
    SettlementTimeline,
    TimelineEvent,
)
from schema.Payroll.final_settlement import (
    ApprovalPayload,
    AssetCreate,
    AssetUpdate,
    BonusCreate,
    BonusUpdate,
    DeductionCreate,
    DeductionUpdate,
    DocumentCreate,
    DocumentUpdate,
    FinalSettlementCreate,
    FinalSettlementUpdate,
    GratuityCreate,
    GratuityUpdate,
    LeaveEncashmentCreate,
    LeaveEncashmentUpdate,
    NoticePeriodCreate,
    NoticePeriodUpdate,
    PaymentCreate,
    PaymentProcessPayload,
    PaymentUpdate,
    RejectionPayload,
    SalaryBreakdownCreate,
    SalaryBreakdownUpdate,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

TWO_PLACES = Decimal("0.01")


def _round2(value) -> Decimal:
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _get_or_404(db: Session, model, record_id: int, label: str = "Record"):
    obj = db.get(model, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def _load_full(db: Session, settlement_id: int) -> FinalSettlement:
    """Load settlement with all eager relationships."""
    stmt = (
        select(FinalSettlement)
        .where(FinalSettlement.id == settlement_id)
        .options(
            selectinload(FinalSettlement.notice_period),
            selectinload(FinalSettlement.salary_breakdown),
            selectinload(FinalSettlement.leave_encashment),
            selectinload(FinalSettlement.bonus),
            selectinload(FinalSettlement.gratuity),
            selectinload(FinalSettlement.deduction),
            selectinload(FinalSettlement.assets),
            selectinload(FinalSettlement.payment),
            selectinload(FinalSettlement.documents),
            selectinload(FinalSettlement.timeline),
            selectinload(FinalSettlement.approval_logs),
        )
    )
    obj = db.execute(stmt).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Final settlement not found")
    return obj


def _generate_settlement_code(db: Session) -> str:
    year = datetime.utcnow().year
    prefix = f"FS-{year}-"
    count = db.execute(
        select(func.count(FinalSettlement.id)).where(
            FinalSettlement.settlement_code.like(f"{prefix}%")
        )
    ).scalar() or 0
    return f"{prefix}{str(count + 1).zfill(4)}"


def _add_log(
    db: Session,
    settlement: FinalSettlement,
    action: ApprovalAction,
    from_status: str,
    to_status: str,
    actioned_by: Optional[int] = None,
    actioned_by_name: Optional[str] = None,
    remarks: Optional[str] = None,
) -> None:
    log = SettlementApprovalLog(
        settlement_id=settlement.id,
        action=action,
        actioned_by=actioned_by,
        actioned_by_name=actioned_by_name,
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
        actioned_at=datetime.utcnow(),
    )
    db.add(log)


def _seed_timeline(db: Session, settlement: FinalSettlement) -> None:
    """Insert default timeline milestones for a new settlement."""
    events = [
        (TimelineEvent.NOTICE_PERIOD_INITIATED, settlement.resignation_date, True),
        (TimelineEvent.DOCUMENT_COLLECTION, None, False),
        (TimelineEvent.SETTLEMENT_CALCULATION, None, False),
        (TimelineEvent.PAYMENT_PROCESSING, None, False),
    ]
    for event, event_date, completed in events:
        db.add(
            SettlementTimeline(
                settlement_id=settlement.id,
                event=event,
                event_date=event_date,
                is_completed=completed,
            )
        )


def _seed_documents(db: Session, settlement: FinalSettlement) -> None:
    """Insert default document checklist items."""
    doc_types = ["Form16", "Form19", "Form10C", "Experience Letter", "Relieving Letter"]
    for doc_type in doc_types:
        db.add(
            SettlementDocument(
                settlement_id=settlement.id,
                document_type=doc_type,
                pf_account_no=settlement.pf_number if doc_type in ("Form19", "Form10C") else None,
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# Computation Engine
# ─────────────────────────────────────────────────────────────────────────────

def _compute_asset_penalty(assets: List[SettlementAsset]) -> Decimal:
    """
    Penalty matrix:
      Lost     Laptop=50000, Mobile=20000, Others=5000
      Damaged  Laptop=10000, Mobile=5000,  Others=2000
      Pending  Laptop=5000,  Mobile=2000,  Others=1000
    """
    penalty = Decimal("0")
    for asset in assets:
        cat = (asset.category or "").lower()
        is_laptop = "laptop" in cat
        is_mobile = "mobile" in cat or "phone" in cat

        cond = asset.condition
        ret  = asset.return_status

        if cond == AssetCondition.LOST or ret == AssetReturnStatus.LOST:
            penalty += Decimal("50000") if is_laptop else (Decimal("20000") if is_mobile else Decimal("5000"))
        elif cond == AssetCondition.DAMAGED or ret == AssetReturnStatus.DAMAGED:
            penalty += Decimal("10000") if is_laptop else (Decimal("5000") if is_mobile else Decimal("2000"))
        elif ret == AssetReturnStatus.PENDING:
            penalty += Decimal("5000") if is_laptop else (Decimal("2000") if is_mobile else Decimal("1000"))

        # Update individual asset penalty too
        asset.penalty = (
            Decimal("50000") if (cond == AssetCondition.LOST or ret == AssetReturnStatus.LOST) and is_laptop
            else Decimal("20000") if (cond == AssetCondition.LOST or ret == AssetReturnStatus.LOST) and is_mobile
            else Decimal("5000") if (cond == AssetCondition.LOST or ret == AssetReturnStatus.LOST)
            else Decimal("10000") if (cond == AssetCondition.DAMAGED or ret == AssetReturnStatus.DAMAGED) and is_laptop
            else Decimal("5000") if (cond == AssetCondition.DAMAGED or ret == AssetReturnStatus.DAMAGED) and is_mobile
            else Decimal("2000") if (cond == AssetCondition.DAMAGED or ret == AssetReturnStatus.DAMAGED)
            else Decimal("5000") if ret == AssetReturnStatus.PENDING and is_laptop
            else Decimal("2000") if ret == AssetReturnStatus.PENDING and is_mobile
            else Decimal("1000") if ret == AssetReturnStatus.PENDING
            else Decimal("0")
        )
    return _round2(penalty)


def recalculate(db: Session, settlement: FinalSettlement) -> FinalSettlement:
    """
    Master recalculate — recomputes every monetary field bottom-up and
    updates header totals.  Call after any sub-block change.
    """
    np   = settlement.notice_period
    sal  = settlement.salary_breakdown
    lv   = settlement.leave_encashment
    bon  = settlement.bonus
    grat = settlement.gratuity
    ded  = settlement.deduction
    assets = settlement.assets or []

    # 1. Salary for days worked
    sal_for_days = Decimal("0")
    daily_rate   = Decimal("0")
    if sal:
        gross = _round2(
            (sal.basic or 0) + (sal.hra or 0) +
            (sal.special_allowance or 0) + (sal.other_allowances or 0)
        )
        wdays = int(sal.working_days_in_month or 30)
        daily_rate = _round2(gross / wdays) if wdays else Decimal("0")
        sal_for_days = _round2(daily_rate * int(sal.days_worked or 0))
        sal.daily_rate    = daily_rate
        sal.salary_for_days = sal_for_days

    # 2. Notice period shortfall
    notice_recovery = Decimal("0")
    if np:
        shortfall = max(0, int(np.required_days or 0) - int(np.days_served or 0))
        if np.waiver_approved:
            shortfall = 0
        notice_recovery = _round2(daily_rate * shortfall)
        np.shortfall_days    = shortfall
        np.recovery_amount   = notice_recovery

    # 3. Leave encashment  (earned leave only by default)
    leave_enc = Decimal("0")
    if lv:
        enc_days   = _round2(lv.earned_leave_balance or 0)
        enc_rate   = _round2(lv.encashment_rate or 0)
        leave_enc  = _round2(enc_days * enc_rate)
        lv.encashable_days   = enc_days
        lv.total_encashment  = leave_enc

    # 4. Pro-rata bonus
    pro_rata_bonus = Decimal("0")
    if bon and bon.is_eligible:
        annual = _round2(bon.annual_bonus or 0)
        days   = int(bon.pro_rata_days or 0)
        pro_rata_bonus = _round2((annual / 365) * days) if days else Decimal("0")
        bon.pro_rata_bonus = pro_rata_bonus

    # 5. Gratuity  (15/26 × basic × completed full years, only if ≥ eligibility_years)
    gratuity_amt = Decimal("0")
    if grat:
        years     = float(grat.completed_years or 0)
        elig_yrs  = int(grat.eligibility_years or 5)
        basic     = _round2(grat.last_drawn_basic or 0)
        is_elig   = years >= elig_yrs
        if is_elig and basic:
            full_years  = int(years)
            gratuity_amt = _round2((basic / 26) * 15 * full_years)
        grat.gratuity_amount = gratuity_amt
        grat.is_eligible     = is_elig

    # 6. Approved reimbursements (sourced from deduction block for now)
    approved_reimbursements = Decimal("0")
    if ded:
        # reimbursements are additions, stored separately in the FE but we
        # add them via total_additions path — use pending_reimbursements if present
        pass

    # 7. Asset penalties
    asset_penalty = _compute_asset_penalty(assets) if assets else Decimal("0")

    # 8. Aggregate totals
    total_additions = _round2(
        sal_for_days
        + leave_enc
        + pro_rata_bonus
        + gratuity_amt
        + (sal.arrears if sal else Decimal("0"))
        + approved_reimbursements
    )

    if ded:
        ded.notice_period_recovery = notice_recovery
        ded.asset_penalty          = asset_penalty
        total_ded = _round2(
            (ded.loan_outstanding or 0)
            + (ded.advance_amount or 0)
            + notice_recovery
            + asset_penalty
            + (ded.id_card_deduction or 0)
            + (ded.uniform_deduction or 0)
            + (ded.other_deductions or 0)
            + (ded.tds_deduction or 0)
            + (ded.penalty_amount or 0)
        )
        ded.total_deductions = total_ded
    else:
        total_ded = notice_recovery + asset_penalty

    net = _round2(max(Decimal("0"), total_additions - total_ded))

    # 9. Update header
    settlement.total_additions  = total_additions
    settlement.total_deductions = total_ded
    settlement.net_settlement   = net
    settlement.last_calculated_at = datetime.utcnow()

    # 10. Mark timeline: Settlement Calculation done
    for tl in (settlement.timeline or []):
        if tl.event == TimelineEvent.SETTLEMENT_CALCULATION:
            tl.is_completed = True
            tl.event_date   = date.today()

    return settlement


# ─────────────────────────────────────────────────────────────────────────────
# CRUD — Settlement
# ─────────────────────────────────────────────────────────────────────────────

def create_settlement(db: Session, payload: FinalSettlementCreate) -> FinalSettlement:
    # Duplicate guard
    existing = db.execute(
        select(FinalSettlement).where(FinalSettlement.employee_id == payload.employee_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Final settlement already exists for employee_id {payload.employee_id} "
                   f"(code: {existing.settlement_code})",
        )

    code = _generate_settlement_code(db)

    settlement = FinalSettlement(
        settlement_code=code,
        employee_id=payload.employee_id,
        employee_code=payload.employee_code,
        employee_name=payload.employee_name,
        department=payload.department,
        designation=payload.designation,
        date_of_joining=payload.date_of_joining,
        uan_number=payload.uan_number,
        pf_number=payload.pf_number,
        pan_number=payload.pan_number,
        exit_type=payload.exit_type,
        resignation_date=payload.resignation_date,
        last_working_date=payload.last_working_date,
        notice_period_required_days=payload.notice_period_required_days,
        initiated_by_name=payload.initiated_by_name,
        initiated_date=payload.initiated_date or date.today(),
        remarks=payload.remarks,
        status=SettlementStatus.DRAFT,
    )
    db.add(settlement)
    db.flush()  # get settlement.id

    # Sub-blocks
    np_data = payload.notice_period or NoticePeriodCreate(
        required_days=payload.notice_period_required_days
    )
    db.add(SettlementNoticePeriod(settlement_id=settlement.id, **np_data.model_dump()))

    if payload.salary_breakdown:
        sb = payload.salary_breakdown
        db.add(SettlementSalaryBreakdown(settlement_id=settlement.id, **sb.model_dump()))
    else:
        db.add(SettlementSalaryBreakdown(settlement_id=settlement.id))

    if payload.leave_encashment:
        db.add(SettlementLeaveEncashment(settlement_id=settlement.id, **payload.leave_encashment.model_dump()))
    else:
        db.add(SettlementLeaveEncashment(settlement_id=settlement.id))

    if payload.bonus:
        db.add(SettlementBonus(settlement_id=settlement.id, **payload.bonus.model_dump()))
    else:
        db.add(SettlementBonus(settlement_id=settlement.id))

    if payload.gratuity:
        db.add(SettlementGratuity(settlement_id=settlement.id, **payload.gratuity.model_dump()))
    else:
        db.add(SettlementGratuity(settlement_id=settlement.id))

    if payload.deduction:
        db.add(SettlementDeduction(settlement_id=settlement.id, **payload.deduction.model_dump()))
    else:
        db.add(SettlementDeduction(settlement_id=settlement.id))

    if payload.assets:
        for asset_data in payload.assets:
            db.add(SettlementAsset(settlement_id=settlement.id, **asset_data.model_dump()))

    if payload.payment:
        db.add(SettlementPayment(settlement_id=settlement.id, **payload.payment.model_dump()))
    else:
        db.add(SettlementPayment(settlement_id=settlement.id))

    _seed_timeline(db, settlement)
    _seed_documents(db, settlement)

    # Initial approval log
    db.flush()
    _add_log(
        db, settlement,
        action=ApprovalAction.SUBMITTED,
        from_status="",
        to_status=SettlementStatus.DRAFT,
        actioned_by_name=payload.initiated_by_name,
        remarks="Settlement initiated",
    )

    db.commit()
    return _load_full(db, settlement.id)


def get_settlement(db: Session, settlement_id: int) -> FinalSettlement:
    return _load_full(db, settlement_id)


def get_settlement_by_employee(db: Session, employee_id: int) -> FinalSettlement:
    obj = db.execute(
        select(FinalSettlement).where(FinalSettlement.employee_id == employee_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="No final settlement found for this employee")
    return _load_full(db, obj.id)


def list_settlements(
    db: Session,
    status_filter: Optional[str] = None,
    exit_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    stmt = select(FinalSettlement)
    if status_filter:
        stmt = stmt.where(FinalSettlement.status == status_filter)
    if exit_type:
        stmt = stmt.where(FinalSettlement.exit_type == exit_type)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            FinalSettlement.employee_name.ilike(like)
            | FinalSettlement.employee_code.ilike(like)
            | FinalSettlement.settlement_code.ilike(like)
        )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    items = (
        db.execute(
            stmt.order_by(FinalSettlement.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return total, items


def update_settlement(
    db: Session, settlement_id: int, payload: FinalSettlementUpdate
) -> FinalSettlement:
    obj = _get_or_404(db, FinalSettlement, settlement_id, "Final settlement")
    if obj.status not in (SettlementStatus.DRAFT, SettlementStatus.PENDING_APPROVAL):
        raise HTTPException(
            status_code=400,
            detail="Settlement can only be edited in Draft or Pending Approval status",
        )
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    return _load_full(db, settlement_id)


def delete_settlement(db: Session, settlement_id: int) -> None:
    obj = _get_or_404(db, FinalSettlement, settlement_id, "Final settlement")
    if obj.status == SettlementStatus.PAID:
        raise HTTPException(status_code=400, detail="Cannot delete a paid settlement")
    db.delete(obj)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Stats / Dashboard
# ─────────────────────────────────────────────────────────────────────────────

def get_settlement_stats(db: Session, settlement_id: Optional[int] = None):
    """Returns KPI card data for the dashboard."""
    counts = {
        "pending": db.execute(
            select(func.count(FinalSettlement.id)).where(
                FinalSettlement.status == SettlementStatus.PENDING_APPROVAL
            )
        ).scalar() or 0,
        "approved": db.execute(
            select(func.count(FinalSettlement.id)).where(
                FinalSettlement.status == SettlementStatus.APPROVED
            )
        ).scalar() or 0,
        "paid": db.execute(
            select(func.count(FinalSettlement.id)).where(
                FinalSettlement.status == SettlementStatus.PAID
            )
        ).scalar() or 0,
        "cancelled": db.execute(
            select(func.count(FinalSettlement.id)).where(
                FinalSettlement.status == SettlementStatus.CANCELLED
            )
        ).scalar() or 0,
    }

    current = None
    if settlement_id:
        current = db.get(FinalSettlement, settlement_id)

    return {
        "current_settlement": current.net_settlement if current else Decimal("0"),
        "total_additions": current.total_additions if current else Decimal("0"),
        "total_deductions": current.total_deductions if current else Decimal("0"),
        "approval_status": current.status if current else "N/A",
        **{f"total_{k}_count": v for k, v in counts.items()},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Recalculate
# ─────────────────────────────────────────────────────────────────────────────

def recalculate_settlement(db: Session, settlement_id: int) -> FinalSettlement:
    settlement = _load_full(db, settlement_id)
    if settlement.status == SettlementStatus.PAID:
        raise HTTPException(status_code=400, detail="Cannot recalculate a paid settlement")
    recalculate(db, settlement)
    _add_log(
        db, settlement,
        action=ApprovalAction.RECALCULATED,
        from_status=settlement.status,
        to_status=settlement.status,
        remarks="Settlement recalculated",
    )
    db.commit()
    return _load_full(db, settlement_id)


# ─────────────────────────────────────────────────────────────────────────────
# Workflow Transitions
# ─────────────────────────────────────────────────────────────────────────────

def submit_for_approval(db: Session, settlement_id: int, submitted_by_name: Optional[str] = None) -> FinalSettlement:
    settlement = _get_or_404(db, FinalSettlement, settlement_id, "Final settlement")
    if settlement.status != SettlementStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only Draft settlements can be submitted for approval")
    prev = settlement.status
    settlement.status = SettlementStatus.PENDING_APPROVAL
    settlement.updated_at = datetime.utcnow()
    _add_log(db, settlement, ApprovalAction.SUBMITTED, prev, SettlementStatus.PENDING_APPROVAL,
             actioned_by_name=submitted_by_name, remarks="Submitted for approval")
    db.commit()
    return _load_full(db, settlement_id)


def approve_settlement(db: Session, settlement_id: int, payload: ApprovalPayload) -> FinalSettlement:
    settlement = _get_or_404(db, FinalSettlement, settlement_id, "Final settlement")
    if settlement.status != SettlementStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Only Pending Approval settlements can be approved")
    prev = settlement.status
    settlement.status         = SettlementStatus.APPROVED
    settlement.approved_by    = payload.approved_by
    settlement.approved_by_name = payload.approved_by_name
    settlement.approved_date  = date.today()
    settlement.updated_at     = datetime.utcnow()
    _add_log(
        db, settlement, ApprovalAction.APPROVED, prev, SettlementStatus.APPROVED,
        actioned_by=payload.approved_by,
        actioned_by_name=payload.approved_by_name,
        remarks=payload.remarks,
    )
    db.commit()
    return _load_full(db, settlement_id)


def reject_settlement(db: Session, settlement_id: int, payload: RejectionPayload) -> FinalSettlement:
    settlement = _get_or_404(db, FinalSettlement, settlement_id, "Final settlement")
    if settlement.status not in (SettlementStatus.PENDING_APPROVAL, SettlementStatus.APPROVED):
        raise HTTPException(status_code=400, detail="Cannot reject settlement in current status")
    prev = settlement.status
    settlement.status           = SettlementStatus.DRAFT
    settlement.rejection_reason = payload.rejection_reason
    settlement.updated_at       = datetime.utcnow()
    _add_log(
        db, settlement, ApprovalAction.REJECTED, prev, SettlementStatus.DRAFT,
        actioned_by_name=payload.rejected_by_name,
        remarks=payload.rejection_reason,
    )
    db.commit()
    return _load_full(db, settlement_id)


def process_payment(
    db: Session, settlement_id: int, payload: PaymentProcessPayload
) -> FinalSettlement:
    settlement = _get_or_404(db, FinalSettlement, settlement_id, "Final settlement")
    if settlement.status != SettlementStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Settlement must be Approved before marking as Paid")

    # Update payment sub-block
    pay = db.execute(
        select(SettlementPayment).where(SettlementPayment.settlement_id == settlement_id)
    ).scalar_one_or_none()
    if pay:
        pay.status            = "completed"
        pay.reference_number  = payload.reference_number
        pay.utr_number        = payload.utr_number
        pay.payment_date      = payload.payment_date or date.today()
        pay.processed_by_name = payload.processed_by_name
        pay.processed_date    = datetime.utcnow()
        pay.payment_proof_url = payload.payment_proof_url
        if payload.remarks:
            pay.remarks = payload.remarks

    prev = settlement.status
    settlement.status     = SettlementStatus.PAID
    settlement.updated_at = datetime.utcnow()

    # Update timeline — Payment Processing done
    for tl in (db.execute(
        select(SettlementTimeline).where(SettlementTimeline.settlement_id == settlement_id)
    ).scalars().all()):
        if tl.event == TimelineEvent.PAYMENT_PROCESSING:
            tl.is_completed = True
            tl.event_date   = date.today()

    _add_log(
        db, settlement, ApprovalAction.PAID, prev, SettlementStatus.PAID,
        actioned_by_name=payload.processed_by_name,
        remarks=payload.remarks,
    )
    db.commit()
    return _load_full(db, settlement_id)


def cancel_settlement(db: Session, settlement_id: int, reason: str, cancelled_by_name: Optional[str] = None) -> FinalSettlement:
    settlement = _get_or_404(db, FinalSettlement, settlement_id, "Final settlement")
    if settlement.status == SettlementStatus.PAID:
        raise HTTPException(status_code=400, detail="Cannot cancel a paid settlement")
    prev = settlement.status
    settlement.status           = SettlementStatus.CANCELLED
    settlement.rejection_reason = reason
    settlement.updated_at       = datetime.utcnow()
    _add_log(
        db, settlement, ApprovalAction.CANCELLED, prev, SettlementStatus.CANCELLED,
        actioned_by_name=cancelled_by_name,
        remarks=reason,
    )
    db.commit()
    return _load_full(db, settlement_id)


# ─────────────────────────────────────────────────────────────────────────────
# Sub-block Updates
# ─────────────────────────────────────────────────────────────────────────────

def update_notice_period(db: Session, settlement_id: int, payload: NoticePeriodUpdate) -> FinalSettlement:
    settlement = _load_full(db, settlement_id)
    np = settlement.notice_period
    if not np:
        raise HTTPException(status_code=404, detail="Notice period block not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(np, k, v)
    recalculate(db, settlement)
    db.commit()
    return _load_full(db, settlement_id)


def update_salary_breakdown(db: Session, settlement_id: int, payload: SalaryBreakdownUpdate) -> FinalSettlement:
    settlement = _load_full(db, settlement_id)
    sal = settlement.salary_breakdown
    if not sal:
        raise HTTPException(status_code=404, detail="Salary breakdown block not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(sal, k, v)
    recalculate(db, settlement)
    db.commit()
    return _load_full(db, settlement_id)


def update_leave_encashment(db: Session, settlement_id: int, payload: LeaveEncashmentUpdate) -> FinalSettlement:
    settlement = _load_full(db, settlement_id)
    lv = settlement.leave_encashment
    if not lv:
        raise HTTPException(status_code=404, detail="Leave encashment block not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(lv, k, v)
    recalculate(db, settlement)
    db.commit()
    return _load_full(db, settlement_id)


def update_bonus(db: Session, settlement_id: int, payload: BonusUpdate) -> FinalSettlement:
    settlement = _load_full(db, settlement_id)
    bon = settlement.bonus
    if not bon:
        raise HTTPException(status_code=404, detail="Bonus block not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(bon, k, v)
    recalculate(db, settlement)
    db.commit()
    return _load_full(db, settlement_id)


def update_gratuity(db: Session, settlement_id: int, payload: GratuityUpdate) -> FinalSettlement:
    settlement = _load_full(db, settlement_id)
    grat = settlement.gratuity
    if not grat:
        raise HTTPException(status_code=404, detail="Gratuity block not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(grat, k, v)
    recalculate(db, settlement)
    db.commit()
    return _load_full(db, settlement_id)


def update_deductions(db: Session, settlement_id: int, payload: DeductionUpdate) -> FinalSettlement:
    settlement = _load_full(db, settlement_id)
    ded = settlement.deduction
    if not ded:
        raise HTTPException(status_code=404, detail="Deduction block not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(ded, k, v)
    recalculate(db, settlement)
    db.commit()
    return _load_full(db, settlement_id)


# ─────────────────────────────────────────────────────────────────────────────
# Asset Management
# ─────────────────────────────────────────────────────────────────────────────

def add_asset(db: Session, settlement_id: int, payload: AssetCreate) -> FinalSettlement:
    _get_or_404(db, FinalSettlement, settlement_id, "Final settlement")
    db.add(SettlementAsset(settlement_id=settlement_id, **payload.model_dump()))
    db.flush()
    settlement = _load_full(db, settlement_id)
    recalculate(db, settlement)
    db.commit()
    return _load_full(db, settlement_id)


def update_asset(db: Session, settlement_id: int, asset_id: int, payload: AssetUpdate) -> FinalSettlement:
    asset = db.execute(
        select(SettlementAsset).where(
            SettlementAsset.id == asset_id,
            SettlementAsset.settlement_id == settlement_id,
        )
    ).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(asset, k, v)
    settlement = _load_full(db, settlement_id)
    recalculate(db, settlement)
    db.commit()
    return _load_full(db, settlement_id)


def delete_asset(db: Session, settlement_id: int, asset_id: int) -> FinalSettlement:
    asset = db.execute(
        select(SettlementAsset).where(
            SettlementAsset.id == asset_id,
            SettlementAsset.settlement_id == settlement_id,
        )
    ).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.flush()
    settlement = _load_full(db, settlement_id)
    recalculate(db, settlement)
    db.commit()
    return _load_full(db, settlement_id)


# ─────────────────────────────────────────────────────────────────────────────
# Payment
# ─────────────────────────────────────────────────────────────────────────────

def update_payment_info(db: Session, settlement_id: int, payload: PaymentUpdate) -> FinalSettlement:
    pay = db.execute(
        select(SettlementPayment).where(SettlementPayment.settlement_id == settlement_id)
    ).scalar_one_or_none()
    if not pay:
        # create if missing
        pay = SettlementPayment(settlement_id=settlement_id)
        db.add(pay)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(pay, k, v)
    db.commit()
    return _load_full(db, settlement_id)


# ─────────────────────────────────────────────────────────────────────────────
# Documents
# ─────────────────────────────────────────────────────────────────────────────

def generate_document(db: Session, settlement_id: int, doc_type: str, generated_by: Optional[str] = None) -> FinalSettlement:
    doc = db.execute(
        select(SettlementDocument).where(
            SettlementDocument.settlement_id == settlement_id,
            SettlementDocument.document_type == doc_type,
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document type '{doc_type}' not found in checklist")
    doc.generated      = True
    doc.generated_date = datetime.utcnow()
    doc.generated_by   = generated_by
    doc.download_url   = f"/api/v1/final-settlements/{settlement_id}/documents/{doc_type}/download"

    # Update timeline — Document Collection
    settlement = _get_or_404(db, FinalSettlement, settlement_id, "Final settlement")
    all_docs = db.execute(
        select(SettlementDocument).where(SettlementDocument.settlement_id == settlement_id)
    ).scalars().all()
    if all(d.generated for d in all_docs):
        for tl in db.execute(
            select(SettlementTimeline).where(
                SettlementTimeline.settlement_id == settlement_id,
                SettlementTimeline.event == TimelineEvent.DOCUMENT_COLLECTION,
            )
        ).scalars().all():
            tl.is_completed = True
            tl.event_date   = date.today()

    db.commit()
    return _load_full(db, settlement_id)


def issue_document(db: Session, settlement_id: int, doc_type: str) -> FinalSettlement:
    doc = db.execute(
        select(SettlementDocument).where(
            SettlementDocument.settlement_id == settlement_id,
            SettlementDocument.document_type == doc_type,
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document type '{doc_type}' not found")
    if not doc.generated:
        raise HTTPException(status_code=400, detail="Document must be generated before issuing")
    doc.issued      = True
    doc.issued_date = datetime.utcnow()
    db.commit()
    return _load_full(db, settlement_id)


# ─────────────────────────────────────────────────────────────────────────────
# Export  (CSV — minimal; PDF requires WeasyPrint/ReportLab install)
# ─────────────────────────────────────────────────────────────────────────────

def export_settlement_csv(db: Session, settlement_id: int) -> bytes:
    """Return raw CSV bytes for the settlement summary."""
    s = _load_full(db, settlement_id)
    lines = [
        "Field,Value",
        f"Settlement Code,{s.settlement_code}",
        f"Employee Name,{s.employee_name}",
        f"Employee Code,{s.employee_code}",
        f"Department,{s.department or ''}",
        f"Designation,{s.designation or ''}",
        f"Exit Type,{s.exit_type}",
        f"Last Working Date,{s.last_working_date}",
        f"Status,{s.status}",
        "",
        "ADDITIONS",
        f"Salary for Days Worked,{s.salary_breakdown.salary_for_days if s.salary_breakdown else 0}",
        f"Leave Encashment,{s.leave_encashment.total_encashment if s.leave_encashment else 0}",
        f"Pro-Rata Bonus,{s.bonus.pro_rata_bonus if s.bonus else 0}",
        f"Gratuity,{s.gratuity.gratuity_amount if s.gratuity else 0}",
        f"Salary Arrears,{s.salary_breakdown.arrears if s.salary_breakdown else 0}",
        f"Total Additions,{s.total_additions}",
        "",
        "DEDUCTIONS",
        f"Loan Outstanding,{s.deduction.loan_outstanding if s.deduction else 0}",
        f"Advance Amount,{s.deduction.advance_amount if s.deduction else 0}",
        f"Notice Period Recovery,{s.deduction.notice_period_recovery if s.deduction else 0}",
        f"Asset Penalty,{s.deduction.asset_penalty if s.deduction else 0}",
        f"TDS,{s.deduction.tds_deduction if s.deduction else 0}",
        f"Other Deductions,{s.deduction.other_deductions if s.deduction else 0}",
        f"Total Deductions,{s.total_deductions}",
        "",
        f"NET SETTLEMENT,{s.net_settlement}",
    ]
    return "\n".join(lines).encode("utf-8")


def export_settlement_report_csv(db: Session) -> bytes:
    """Export all settlements as a tabular CSV."""
    settlements = db.execute(
        select(FinalSettlement).order_by(FinalSettlement.created_at.desc())
    ).scalars().all()
    header = "Code,Employee,Department,Exit Type,LWD,Net Settlement,Status,Date"
    rows = [header]
    for s in settlements:
        rows.append(
            f"{s.settlement_code},{s.employee_name},{s.department or ''},"
            f"{s.exit_type},{s.last_working_date},{s.net_settlement},"
            f"{s.status},{s.created_at.date()}"
        )
    return "\n".join(rows).encode("utf-8")
