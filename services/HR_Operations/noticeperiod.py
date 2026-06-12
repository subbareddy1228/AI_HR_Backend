"""
Notice Period Tracking & Management — Service Layer
====================================================
All business logic lives here; routers are kept thin.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from model.HR_Operations.notice_period import (
    ApprovalStatus,
    CounterOfferStatus,
    NoticeBuyoutRequest,
    NoticeCalculation,
    NoticeCounterOffer,
    NoticeExtensionRequest,
    NoticePeriod,
    NoticeResignationWorkflow,
    NoticeStatus,
    NoticeWaiverRequest,
    ResignationWorkflowStep,
)
from schema.HR_Operations.notice_period import (
    BuyoutApprovalUpdate,
    BuyoutRequestCreate,
    BuyoutCalculatorRequest,
    BuyoutCalculatorResponse,
    CounterOfferCreate,
    CounterOfferResponseUpdate,
    CountdownTrackerItem,
    DashboardResponse,
    DashboardStats,
    ExtensionApprovalUpdate,
    ExtensionRequestCreate,
    LWDCalculatorRequest,
    LWDCalculatorResponse,
    NoticePeriodCreate,
    NoticePeriodUpdate,
    ShortfallCalculatorRequest,
    ShortfallCalculatorResponse,
    WaiverApprovalUpdate,
    WaiverCalculatorRequest,
    WaiverCalculatorResponse,
    WaiverRequestCreate,
    WorkflowStepCreate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _not_found(entity: str, id_: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} with id={id_} not found.",
    )


def _compute_lwd(start: date, notice_days: int) -> date:
    """Last Working Day = start + notice_days (calendar days)."""
    return start + timedelta(days=notice_days)


def _compute_days_remaining(end_date: date) -> int:
    delta = (end_date - date.today()).days
    return max(delta, 0)


def _per_day_salary(monthly_salary: Decimal) -> Decimal:
    return (monthly_salary / Decimal("30")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _record_calculation(
    db: Session,
    calc_type: str,
    input_data: dict,
    result_data: dict,
    notice_period_id: Optional[int] = None,
    calculated_by: Optional[int] = None,
) -> None:
    log = NoticeCalculation(
        notice_period_id=notice_period_id,
        calc_type=calc_type,
        input_data=json.dumps(input_data, default=str),
        result_data=json.dumps(result_data, default=str),
        calculated_by=calculated_by,
    )
    db.add(log)
    # intentionally not committing here — caller commits


# ---------------------------------------------------------------------------
# NoticePeriod CRUD
# ---------------------------------------------------------------------------

def create_notice_period(db: Session, payload: NoticePeriodCreate) -> NoticePeriod:
    # Guard: only one SERVING notice per employee
    existing = db.execute(
        select(NoticePeriod).where(
            and_(
                NoticePeriod.employee_id == payload.employee_id,
                NoticePeriod.status.in_([NoticeStatus.SERVING, NoticeStatus.EXTENDED]),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee {payload.employee_id} already has an active notice period (id={existing.id}).",
        )

    notice_end = _compute_lwd(payload.notice_start_date, payload.notice_period_days)
    days_rem   = _compute_days_remaining(notice_end)

    record = NoticePeriod(
        employee_id=payload.employee_id,
        resignation_date=payload.resignation_date,
        resignation_reason=payload.resignation_reason,
        resignation_letter=payload.resignation_letter,
        notice_start_date=payload.notice_start_date,
        notice_end_date=notice_end,
        notice_period_days=payload.notice_period_days,
        days_remaining=days_rem,
        serving_days=0,
        monthly_salary=payload.monthly_salary,
        status=NoticeStatus.SERVING,
        remarks=payload.remarks,
        created_by=payload.created_by,
    )
    db.add(record)
    db.flush()

    # Seed first workflow step
    _add_workflow_step_internal(
        db=db,
        notice_period_id=record.id,
        employee_id=payload.employee_id,
        step=ResignationWorkflowStep.RESIGNATION_SUBMITTED,
        performed_by=payload.created_by,
        comments="Resignation submitted and notice period initiated.",
    )

    db.commit()
    db.refresh(record)
    return record


def list_notice_periods(
    db: Session,
    status_filter: Optional[NoticeStatus] = None,
    employee_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[NoticePeriod]:
    q = select(NoticePeriod)
    if status_filter:
        q = q.where(NoticePeriod.status == status_filter)
    if employee_id:
        q = q.where(NoticePeriod.employee_id == employee_id)
    q = q.order_by(NoticePeriod.created_at.desc()).offset(skip).limit(limit)
    return db.execute(q).scalars().all()


def get_notice_period(db: Session, notice_id: int) -> NoticePeriod:
    record = db.get(NoticePeriod, notice_id)
    if not record:
        raise _not_found("NoticePeriod", notice_id)
    # Refresh computed fields
    record.days_remaining = _compute_days_remaining(record.notice_end_date)
    record.serving_days   = (date.today() - record.notice_start_date).days
    db.commit()
    return record


def update_notice_period(db: Session, notice_id: int, payload: NoticePeriodUpdate) -> NoticePeriod:
    record = db.get(NoticePeriod, notice_id)
    if not record:
        raise _not_found("NoticePeriod", notice_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)

    # Recompute days remaining if status or LWD changed
    if payload.actual_lwd:
        record.days_remaining = _compute_days_remaining(payload.actual_lwd)
    else:
        record.days_remaining = _compute_days_remaining(record.notice_end_date)

    db.commit()
    db.refresh(record)
    return record


def delete_notice_period(db: Session, notice_id: int) -> None:
    record = db.get(NoticePeriod, notice_id)
    if not record:
        raise _not_found("NoticePeriod", notice_id)
    if record.status == NoticeStatus.SERVING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an active SERVING notice period. Change status first.",
        )
    db.delete(record)
    db.commit()


# ---------------------------------------------------------------------------
# Buyout Requests
# ---------------------------------------------------------------------------

def create_buyout_request(db: Session, payload: BuyoutRequestCreate) -> NoticeBuyoutRequest:
    notice = db.get(NoticePeriod, payload.notice_period_id)
    if not notice:
        raise _not_found("NoticePeriod", payload.notice_period_id)
    if notice.status not in (NoticeStatus.SERVING, NoticeStatus.EXTENDED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buyout can only be requested for SERVING or EXTENDED notices.",
        )

    per_day = _per_day_salary(payload.monthly_salary)
    buyout_amt = (per_day * payload.days_to_buyout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    record = NoticeBuyoutRequest(
        notice_period_id=payload.notice_period_id,
        employee_id=payload.employee_id,
        requested_date=payload.requested_date,
        days_to_buyout=payload.days_to_buyout,
        monthly_salary=payload.monthly_salary,
        buyout_amount=buyout_amt,
        requested_lwd=payload.requested_lwd,
        remarks=payload.remarks,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def process_buyout_approval(
    db: Session, buyout_id: int, payload: BuyoutApprovalUpdate
) -> NoticeBuyoutRequest:
    record = db.get(NoticeBuyoutRequest, buyout_id)
    if not record:
        raise _not_found("NoticeBuyoutRequest", buyout_id)

    role_field_map = {
        "MANAGER": "manager_status",
        "HR":      "hr_status",
        "FINANCE": "finance_status",
    }
    field = role_field_map[payload.approver_role]
    setattr(record, field, payload.approval_status)

    if payload.rejection_reason:
        record.rejection_reason = payload.rejection_reason
    if payload.remarks:
        record.remarks = payload.remarks

    # Compute aggregate approval status
    all_statuses = [record.manager_status, record.hr_status, record.finance_status]
    if any(s == ApprovalStatus.REJECTED for s in all_statuses):
        record.approval_status = ApprovalStatus.REJECTED
    elif all(s == ApprovalStatus.APPROVED for s in all_statuses):
        record.approval_status = ApprovalStatus.APPROVED
        record.approved_at     = datetime.utcnow()
        # Update master record
        notice = db.get(NoticePeriod, record.notice_period_id)
        if notice:
            notice.status        = NoticeStatus.BUYOUT
            notice.buyout_amount = record.buyout_amount
            notice.actual_lwd    = record.requested_lwd
    else:
        record.approval_status = ApprovalStatus.PENDING

    db.commit()
    db.refresh(record)
    return record


def list_buyout_requests(db: Session, notice_period_id: Optional[int] = None) -> List[NoticeBuyoutRequest]:
    q = select(NoticeBuyoutRequest)
    if notice_period_id:
        q = q.where(NoticeBuyoutRequest.notice_period_id == notice_period_id)
    return db.execute(q.order_by(NoticeBuyoutRequest.created_at.desc())).scalars().all()


# ---------------------------------------------------------------------------
# Waiver Requests
# ---------------------------------------------------------------------------

def create_waiver_request(db: Session, payload: WaiverRequestCreate) -> NoticeWaiverRequest:
    notice = db.get(NoticePeriod, payload.notice_period_id)
    if not notice:
        raise _not_found("NoticePeriod", payload.notice_period_id)

    doc_json = json.dumps(payload.document_urls) if payload.document_urls else None

    record = NoticeWaiverRequest(
        notice_period_id=payload.notice_period_id,
        employee_id=payload.employee_id,
        requested_date=payload.requested_date,
        waiver_days=payload.waiver_days,
        reason=payload.reason,
        document_urls=doc_json,
        remarks=payload.remarks,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def process_waiver_approval(
    db: Session, waiver_id: int, payload: WaiverApprovalUpdate
) -> NoticeWaiverRequest:
    record = db.get(NoticeWaiverRequest, waiver_id)
    if not record:
        raise _not_found("NoticeWaiverRequest", waiver_id)

    role_field_map = {
        "MANAGER":  "manager_status",
        "HR":       "hr_status",
        "DIRECTOR": "director_status",
    }
    setattr(record, role_field_map[payload.approver_role], payload.approval_status)

    if payload.rejection_reason:
        record.rejection_reason = payload.rejection_reason
    if payload.remarks:
        record.remarks = payload.remarks

    all_statuses = [record.manager_status, record.hr_status, record.director_status]
    if any(s == ApprovalStatus.REJECTED for s in all_statuses):
        record.approval_status = ApprovalStatus.REJECTED
    elif all(s == ApprovalStatus.APPROVED for s in all_statuses):
        record.approval_status = ApprovalStatus.APPROVED
        record.approved_at     = datetime.utcnow()
        # Shorten notice end date
        notice = db.get(NoticePeriod, record.notice_period_id)
        if notice:
            notice.notice_end_date  = notice.notice_end_date - timedelta(days=record.waiver_days)
            notice.notice_period_days -= record.waiver_days
            notice.days_remaining   = _compute_days_remaining(notice.notice_end_date)
            notice.status           = NoticeStatus.WAIVED
    else:
        record.approval_status = ApprovalStatus.PENDING

    db.commit()
    db.refresh(record)
    return record


def list_waiver_requests(db: Session, notice_period_id: Optional[int] = None) -> List[NoticeWaiverRequest]:
    q = select(NoticeWaiverRequest)
    if notice_period_id:
        q = q.where(NoticeWaiverRequest.notice_period_id == notice_period_id)
    return db.execute(q.order_by(NoticeWaiverRequest.created_at.desc())).scalars().all()


# ---------------------------------------------------------------------------
# Counter Offers
# ---------------------------------------------------------------------------

def create_counter_offer(db: Session, payload: CounterOfferCreate) -> NoticeCounterOffer:
    notice = db.get(NoticePeriod, payload.notice_period_id)
    if not notice:
        raise _not_found("NoticePeriod", payload.notice_period_id)

    hike = None
    if payload.current_salary and payload.offered_salary:
        hike = (
            ((payload.offered_salary - payload.current_salary) / payload.current_salary) * 100
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    record = NoticeCounterOffer(
        notice_period_id=payload.notice_period_id,
        employee_id=payload.employee_id,
        current_salary=payload.current_salary,
        offered_salary=payload.offered_salary,
        hike_percentage=hike,
        additional_benefits=payload.additional_benefits,
        role_change=payload.role_change,
        retention_probability=payload.retention_probability,
        offer_date=payload.offer_date,
        expiry_date=payload.expiry_date,
        created_by=payload.created_by,
    )
    db.add(record)

    # Advance workflow
    _add_workflow_step_internal(
        db=db,
        notice_period_id=notice.id,
        employee_id=notice.employee_id,
        step=ResignationWorkflowStep.COUNTER_OFFER_SENT,
        performed_by=payload.created_by,
        comments=f"Counter offer sent: ₹{payload.offered_salary} (+{hike}%)",
    )

    db.commit()
    db.refresh(record)
    return record


def respond_to_counter_offer(
    db: Session, offer_id: int, payload: CounterOfferResponseUpdate
) -> NoticeCounterOffer:
    record = db.get(NoticeCounterOffer, offer_id)
    if not record:
        raise _not_found("NoticeCounterOffer", offer_id)

    record.status            = payload.status
    record.employee_response = payload.employee_response
    record.responded_at      = datetime.utcnow()

    notice = db.get(NoticePeriod, record.notice_period_id)
    if notice:
        _add_workflow_step_internal(
            db=db,
            notice_period_id=notice.id,
            employee_id=notice.employee_id,
            step=ResignationWorkflowStep.COUNTER_OFFER_RESPONDED,
            performed_by=notice.employee_id,
            comments=f"Employee {payload.status.value.lower()} the counter offer.",
        )
        if payload.status == CounterOfferStatus.ACCEPTED:
            notice.status = NoticeStatus.CANCELLED  # resignation withdrawn

    db.commit()
    db.refresh(record)
    return record


def list_counter_offers(db: Session, notice_period_id: Optional[int] = None) -> List[NoticeCounterOffer]:
    q = select(NoticeCounterOffer)
    if notice_period_id:
        q = q.where(NoticeCounterOffer.notice_period_id == notice_period_id)
    return db.execute(q.order_by(NoticeCounterOffer.created_at.desc())).scalars().all()


# ---------------------------------------------------------------------------
# Extension Requests
# ---------------------------------------------------------------------------

def create_extension_request(db: Session, payload: ExtensionRequestCreate) -> NoticeExtensionRequest:
    notice = db.get(NoticePeriod, payload.notice_period_id)
    if not notice:
        raise _not_found("NoticePeriod", payload.notice_period_id)

    new_end = notice.notice_end_date + timedelta(days=payload.extension_days)

    record = NoticeExtensionRequest(
        notice_period_id=payload.notice_period_id,
        employee_id=payload.employee_id,
        requested_by=payload.requested_by,
        requested_date=payload.requested_date,
        extension_days=payload.extension_days,
        new_end_date=new_end,
        reason=payload.reason,
        remarks=payload.remarks,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def process_extension_approval(
    db: Session, extension_id: int, payload: ExtensionApprovalUpdate
) -> NoticeExtensionRequest:
    record = db.get(NoticeExtensionRequest, extension_id)
    if not record:
        raise _not_found("NoticeExtensionRequest", extension_id)

    record.approval_status  = payload.approval_status
    record.rejection_reason = payload.rejection_reason
    record.remarks          = payload.remarks

    if payload.approval_status == ApprovalStatus.APPROVED:
        record.approved_by = payload.approved_by
        record.approved_at = datetime.utcnow()
        notice = db.get(NoticePeriod, record.notice_period_id)
        if notice:
            notice.notice_end_date  = record.new_end_date
            notice.notice_period_days += record.extension_days
            notice.days_remaining   = _compute_days_remaining(record.new_end_date)
            notice.status           = NoticeStatus.EXTENDED

    db.commit()
    db.refresh(record)
    return record


def list_extension_requests(db: Session, notice_period_id: Optional[int] = None) -> List[NoticeExtensionRequest]:
    q = select(NoticeExtensionRequest)
    if notice_period_id:
        q = q.where(NoticeExtensionRequest.notice_period_id == notice_period_id)
    return db.execute(q.order_by(NoticeExtensionRequest.created_at.desc())).scalars().all()


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

def _add_workflow_step_internal(
    db: Session,
    notice_period_id: int,
    employee_id: int,
    step: ResignationWorkflowStep,
    performed_by: Optional[int],
    comments: Optional[str],
) -> NoticeResignationWorkflow:
    # Mark previous current step as done
    db.execute(
        select(NoticeResignationWorkflow)
        .where(
            and_(
                NoticeResignationWorkflow.notice_period_id == notice_period_id,
                NoticeResignationWorkflow.is_current_step == True,
            )
        )
    )
    db.query(NoticeResignationWorkflow).filter(
        NoticeResignationWorkflow.notice_period_id == notice_period_id,
        NoticeResignationWorkflow.is_current_step == True,
    ).update({"is_current_step": False})

    step_record = NoticeResignationWorkflow(
        notice_period_id=notice_period_id,
        employee_id=employee_id,
        step=step,
        performed_by=performed_by,
        comments=comments,
        is_current_step=True,
    )
    db.add(step_record)
    return step_record


def add_workflow_step(db: Session, payload: WorkflowStepCreate) -> NoticeResignationWorkflow:
    notice = db.get(NoticePeriod, payload.notice_period_id)
    if not notice:
        raise _not_found("NoticePeriod", payload.notice_period_id)

    step_record = _add_workflow_step_internal(
        db=db,
        notice_period_id=payload.notice_period_id,
        employee_id=payload.employee_id,
        step=payload.step,
        performed_by=payload.performed_by,
        comments=payload.comments,
    )
    db.commit()
    db.refresh(step_record)
    return step_record


def get_workflow(db: Session, notice_period_id: int) -> List[NoticeResignationWorkflow]:
    return (
        db.execute(
            select(NoticeResignationWorkflow)
            .where(NoticeResignationWorkflow.notice_period_id == notice_period_id)
            .order_by(NoticeResignationWorkflow.step_date)
        )
        .scalars()
        .all()
    )


# ---------------------------------------------------------------------------
# Calculators
# ---------------------------------------------------------------------------

def calc_lwd(db: Session, payload: LWDCalculatorRequest, calculated_by: Optional[int] = None) -> LWDCalculatorResponse:
    lwd = _compute_lwd(payload.resignation_date, payload.notice_period_days)
    result = LWDCalculatorResponse(
        resignation_date=payload.resignation_date,
        notice_period_days=payload.notice_period_days,
        last_working_date=lwd,
        calendar_days=payload.notice_period_days,
    )
    _record_calculation(
        db, "LWD",
        {"resignation_date": str(payload.resignation_date), "notice_period_days": payload.notice_period_days},
        {"last_working_date": str(lwd)},
        calculated_by=calculated_by,
    )
    db.commit()
    return result


def calc_buyout(db: Session, payload: BuyoutCalculatorRequest, calculated_by: Optional[int] = None) -> BuyoutCalculatorResponse:
    per_day  = _per_day_salary(payload.monthly_salary)
    buyout   = (per_day * payload.days_to_buyout).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    result   = BuyoutCalculatorResponse(
        monthly_salary=payload.monthly_salary,
        days_to_buyout=payload.days_to_buyout,
        per_day_salary=per_day,
        buyout_amount=buyout,
    )
    _record_calculation(
        db, "BUYOUT",
        {"monthly_salary": str(payload.monthly_salary), "days_to_buyout": payload.days_to_buyout},
        {"per_day_salary": str(per_day), "buyout_amount": str(buyout)},
        calculated_by=calculated_by,
    )
    db.commit()
    return result


def calc_waiver(db: Session, payload: WaiverCalculatorRequest, calculated_by: Optional[int] = None) -> WaiverCalculatorResponse:
    effective    = payload.actual_service_days
    shortfall    = max(payload.current_notice_period_days - payload.actual_service_days, 0)
    eligible     = payload.waiver_days_requested <= shortfall
    result = WaiverCalculatorResponse(
        original_notice_days=payload.current_notice_period_days,
        waiver_days_requested=payload.waiver_days_requested,
        actual_service_days=payload.actual_service_days,
        effective_notice_days=effective,
        shortfall_days=shortfall,
        is_eligible_for_waiver=eligible,
    )
    _record_calculation(
        db, "WAIVER",
        payload.model_dump(),
        result.model_dump(),
        calculated_by=calculated_by,
    )
    db.commit()
    return result


def calc_shortfall(db: Session, payload: ShortfallCalculatorRequest, calculated_by: Optional[int] = None) -> ShortfallCalculatorResponse:
    shortfall_days = max(payload.required_notice_days - payload.actual_service_days, 0)
    per_day        = _per_day_salary(payload.monthly_salary)
    shortfall_amt  = (per_day * shortfall_days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    result = ShortfallCalculatorResponse(
        required_notice_days=payload.required_notice_days,
        actual_service_days=payload.actual_service_days,
        shortfall_days=shortfall_days,
        shortfall_amount=shortfall_amt,
    )
    _record_calculation(
        db, "SHORTFALL",
        payload.model_dump(),
        result.model_dump(),
        calculated_by=calculated_by,
    )
    db.commit()
    return result


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def get_dashboard(db: Session) -> DashboardResponse:
    today     = date.today()
    week_ago  = today - timedelta(days=7)

    active_cases = db.execute(
        select(func.count()).where(
            NoticePeriod.status.in_([NoticeStatus.SERVING, NoticeStatus.EXTENDED])
        )
    ).scalar_one()

    cases_this_week = db.execute(
        select(func.count()).where(
            NoticePeriod.resignation_date >= week_ago
        )
    ).scalar_one()

    pending_approvals = (
        db.execute(select(func.count()).where(NoticeBuyoutRequest.approval_status == ApprovalStatus.PENDING)).scalar_one()
        + db.execute(select(func.count()).where(NoticeWaiverRequest.approval_status == ApprovalStatus.PENDING)).scalar_one()
        + db.execute(select(func.count()).where(NoticeExtensionRequest.approval_status == ApprovalStatus.PENDING)).scalar_one()
    )

    retention_successes = db.execute(
        select(func.count()).where(
            NoticePeriod.status == NoticeStatus.CANCELLED
        )
    ).scalar_one()

    # Countdown tracker — active cases ordered by days remaining
    active_notices: List[NoticePeriod] = (
        db.execute(
            select(NoticePeriod)
            .where(NoticePeriod.status.in_([NoticeStatus.SERVING, NoticeStatus.EXTENDED]))
            .order_by(NoticePeriod.notice_end_date)
            .limit(20)
        )
        .scalars()
        .all()
    )

    countdown_items = []
    for n in active_notices:
        days_left     = _compute_days_remaining(n.notice_end_date)
        pending_acts  = _get_pending_actions(db, n)
        countdown_items.append(
            CountdownTrackerItem(
                notice_period_id=n.id,
                employee_id=n.employee_id,
                employee_name=f"Employee {n.employee_id}",   # enriched by join in production
                employee_code=None,
                department=None,
                days_left=days_left,
                notice_start_date=n.notice_start_date,
                notice_end_date=n.notice_end_date,
                status=n.status,
                pending_actions=pending_acts,
            )
        )

    stats = DashboardStats(
        active_cases=active_cases,
        pending_approvals=pending_approvals,
        retention_successes=retention_successes,
        cases_this_week=cases_this_week,
        ai_time_saved_hours=42,       # configurable KPI
        prediction_accuracy=0.95,
    )

    return DashboardResponse(stats=stats, countdown_tracker=countdown_items)


def _get_pending_actions(db: Session, notice: NoticePeriod) -> List[str]:
    actions: List[str] = []
    if not notice.manager_acknowledged:
        actions.append("Manager Ack Pending")
    if not notice.hr_reviewed:
        actions.append("HR Review Pending")

    pending_buyout = db.execute(
        select(func.count()).where(
            and_(
                NoticeBuyoutRequest.notice_period_id == notice.id,
                NoticeBuyoutRequest.approval_status == ApprovalStatus.PENDING,
            )
        )
    ).scalar_one()
    if pending_buyout:
        actions.append("Buyout Approval Pending")

    pending_waiver = db.execute(
        select(func.count()).where(
            and_(
                NoticeWaiverRequest.notice_period_id == notice.id,
                NoticeWaiverRequest.approval_status == ApprovalStatus.PENDING,
            )
        )
    ).scalar_one()
    if pending_waiver:
        actions.append("Waiver Requested")

    pending_offer = db.execute(
        select(func.count()).where(
            and_(
                NoticeCounterOffer.notice_period_id == notice.id,
                NoticeCounterOffer.status == CounterOfferStatus.PENDING,
            )
        )
    ).scalar_one()
    if pending_offer:
        actions.append("Counter Offer")

    return actions
