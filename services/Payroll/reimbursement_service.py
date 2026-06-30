from __future__ import annotations

from calendar import month_name as _MONTH_NAMES
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Sequence

from fastapi import HTTPException, status as http_status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from model.Payroll.reimbursement import (
    ClaimApprovalLog,
    ReimbursementBalance,
    ReimbursementClaim,
    ReimbursementType,
)
from schema.Payroll.reimbursement import (
    ClaimExportRow,
    ClaimsByTypeRow,
    FinanceApprovalRequest,
    ManagerApprovalRequest,
    MarkPaidRequest,
    MonthlyTrendRow,
    ReimbursementBalanceResponse,
    ReimbursementClaimCreate,
    ReimbursementDashboard,
    ReimbursementReports,
    ReimbursementTypeCreate,
    ReimbursementTypeUpdate,
    TaxAnalysis,
    TopEmployeeRow,
)


_TAX_RATE = Decimal("0.30")   
_TWO_DP   = Decimal("0.01")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _r2(v) -> Decimal:
    return Decimal(str(v)).quantize(_TWO_DP, rounding=ROUND_HALF_UP)


def _period_key(frequency: str) -> str:

    now = _utcnow()
    f = frequency.upper()
    if f == "MONTHLY":
        return now.strftime("%Y-%m")
    if f == "QUARTERLY":
        q = (now.month - 1) // 3 + 1
        return f"{now.year}-Q{q}"
    return str(now.year)   


def _utilisation(balance: ReimbursementBalance) -> tuple[float, str]:

    if not balance.limit_amount or balance.limit_amount == 0:
        return (0.0, "Good")
    pct = float(balance.remaining_amount / balance.limit_amount * 100)
    label = "Low" if pct < 20 else ("Medium" if pct < 50 else "Good")
    return (round(pct, 1), label)


def _enrich_balance(b: ReimbursementBalance) -> ReimbursementBalanceResponse:
    pct, label = _utilisation(b)
    return ReimbursementBalanceResponse(
        id=b.id,
        employee_id=b.employee_id,
        employee_code=b.employee_code,
        employee_name=b.employee_name,
        type_id=b.type_id,
        type_name=b.type_name,
        period=b.period,
        limit_amount=_r2(b.limit_amount),
        used_amount=_r2(b.used_amount),
        remaining_amount=_r2(b.remaining_amount),
        utilisation_pct=pct,
        utilisation_label=label,
    )


def _log(
    db: Session,
    claim: ReimbursementClaim,
    to_status: str,
    role: str,
    by_name: Optional[str] = None,
    remarks: Optional[str] = None,
) -> None:

    db.add(ClaimApprovalLog(
        claim_id=claim.id,
        from_status=claim.status,
        to_status=to_status,
        action_by_role=role,
        action_by_name=by_name,
        remarks=remarks,
    ))


def create_type(db: Session, payload: ReimbursementTypeCreate) -> ReimbursementType:
    existing = db.execute(
        select(ReimbursementType).where(ReimbursementType.name == payload.name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Reimbursement type '{payload.name}' already exists.",
        )
    obj = ReimbursementType(**payload.model_dump())
    db.add(obj)
    try:
        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Duplicate type name — conflict.",
        )
    return obj


def list_types(
    db: Session,
    active_only: bool = True,
    category: Optional[str] = None,
) -> List[ReimbursementType]:
    q = db.query(ReimbursementType)
    if active_only:
        q = q.filter(ReimbursementType.is_active.is_(True))
    if category:
        q = q.filter(ReimbursementType.category == category.upper())
    return q.order_by(ReimbursementType.name).all()


def get_type(db: Session, type_id: int) -> ReimbursementType:
    obj = db.get(ReimbursementType, type_id)
    if not obj:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Reimbursement type {type_id} not found.",
        )
    return obj


def update_type(
    db: Session, type_id: int, payload: ReimbursementTypeUpdate
) -> ReimbursementType:
    obj = get_type(db, type_id)
    if payload.name and payload.name != obj.name:
        clash = db.execute(
            select(ReimbursementType).where(ReimbursementType.name == payload.name)
        ).scalar_one_or_none()
        if clash:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=f"Name '{payload.name}' already taken.",
            )
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = _utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def deactivate_type(db: Session, type_id: int) -> None:

    obj = get_type(db, type_id)
    obj.is_active  = False
    obj.updated_at = _utcnow()
    db.commit()


def _get_balance_locked(
    db: Session,
    employee_id: int,
    employee_code: str,
    employee_name: str,
    rtype: ReimbursementType,
) -> ReimbursementBalance:

    period = _period_key(rtype.frequency)
    balance = db.execute(
        select(ReimbursementBalance)
        .where(
            ReimbursementBalance.employee_id == employee_id,
            ReimbursementBalance.type_id     == rtype.id,
            ReimbursementBalance.period      == period,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if not balance:
        balance = ReimbursementBalance(
            employee_id=employee_id,
            employee_code=employee_code,
            employee_name=employee_name,
            type_id=rtype.id,
            type_name=rtype.name,
            period=period,
            limit_amount=rtype.limit_amount,
            used_amount=Decimal("0.00"),
            remaining_amount=rtype.limit_amount,
        )
        db.add(balance)
        db.flush()

    return balance


def _debit_balance(
    db: Session, balance: ReimbursementBalance, amount: Decimal
) -> None:
    if amount > balance.remaining_amount:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Claim ₹{amount} exceeds remaining balance "
                f"₹{balance.remaining_amount} for period '{balance.period}'."
            ),
        )
    balance.used_amount      = _r2(balance.used_amount + amount)
    balance.remaining_amount = _r2(balance.remaining_amount - amount)
    balance.updated_at       = _utcnow()


def list_balances(
    db: Session,
    employee_id: Optional[int] = None,
    type_id:     Optional[int] = None,
    period:      Optional[str] = None,
) -> List[ReimbursementBalanceResponse]:
    q = db.query(ReimbursementBalance)
    if employee_id:
        q = q.filter(ReimbursementBalance.employee_id == employee_id)
    if type_id:
        q = q.filter(ReimbursementBalance.type_id == type_id)
    if period:
        q = q.filter(ReimbursementBalance.period == period)
    rows = q.order_by(
        ReimbursementBalance.employee_name,
        ReimbursementBalance.type_name,
    ).all()
    return [_enrich_balance(r) for r in rows]


def submit_claim(
    db: Session, payload: ReimbursementClaimCreate
) -> ReimbursementClaim:

    rtype = get_type(db, payload.type_id)
    if not rtype.is_active:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Type '{rtype.name}' is no longer active.",
        )

    if payload.claimed_amount > rtype.limit_amount:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Claim ₹{payload.claimed_amount} exceeds type limit "
                f"₹{rtype.limit_amount} for '{rtype.name}'."
            ),
        )

    balance = _get_balance_locked(
        db, payload.employee_id, payload.employee_code,
        payload.employee_name, rtype,
    )
    if payload.claimed_amount > balance.remaining_amount:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Claim ₹{payload.claimed_amount} exceeds period balance "
                f"₹{balance.remaining_amount} for '{rtype.name}' "
                f"(period {balance.period})."
            ),
        )

    tax_amount = (
        _r2(payload.claimed_amount * _TAX_RATE)
        if rtype.is_taxable else Decimal("0.00")
    )
    net_amount = _r2(payload.claimed_amount - tax_amount)

    claim = ReimbursementClaim(
        employee_id=payload.employee_id,
        employee_code=payload.employee_code,
        employee_name=payload.employee_name,
        type_id=rtype.id,
        type_name=rtype.name,
        frequency=rtype.frequency,
        claimed_amount=payload.claimed_amount,
        tax_amount=tax_amount,
        net_amount=net_amount,
        description=payload.description,
        receipt_path=payload.receipt_path,
        receipt_filename=payload.receipt_filename,
        status="PENDING",
        manager_approval_status="PENDING",
        finance_approval_status="PENDING",
        payroll_processed=False,
       
        balance_used=balance.used_amount,
        balance_remaining=balance.remaining_amount,
    )
    db.add(claim)
    db.flush()

    _log(db, claim, "PENDING", "SYSTEM",
         remarks="Claim submitted — awaiting manager approval")

    try:
        db.commit()
        db.refresh(claim)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save claim.",
        ) from exc

    return claim


def list_claims(
    db: Session,
    employee_id:  Optional[int]      = None,
    type_id:      Optional[int]      = None,
    claim_status: Optional[str]      = None,
    date_from:    Optional[datetime] = None,
    date_to:      Optional[datetime] = None,
    search:       Optional[str]      = None,   
    skip:         int                = 0,
    limit:        int                = 100,
) -> List[ReimbursementClaim]:
    q = db.query(ReimbursementClaim)
    if employee_id:
        q = q.filter(ReimbursementClaim.employee_id == employee_id)
    if type_id:
        q = q.filter(ReimbursementClaim.type_id == type_id)
    if claim_status:

        status_map = {
            "Finance Review": "FINANCE_REVIEW",
            "finance_review": "FINANCE_REVIEW",
        }
        db_status = status_map.get(claim_status, claim_status.upper())
        q = q.filter(ReimbursementClaim.status == db_status)
    if date_from:
        q = q.filter(ReimbursementClaim.claim_date >= date_from)
    if date_to:
        q = q.filter(ReimbursementClaim.claim_date <= date_to)
    if search:
        ilike = f"%{search}%"
        q = q.filter(
            ReimbursementClaim.employee_name.ilike(ilike)
            | ReimbursementClaim.employee_code.ilike(ilike)
            | ReimbursementClaim.type_name.ilike(ilike)
        )
    return (
        q.order_by(ReimbursementClaim.created_at.desc())
        .offset(skip).limit(limit).all()
    )


def get_claim(db: Session, claim_id: int) -> ReimbursementClaim:

    claim = (
        db.query(ReimbursementClaim)
        .options(joinedload(ReimbursementClaim.logs))
        .filter(ReimbursementClaim.id == claim_id)
        .first()
    )
    if not claim:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found.",
        )
    return claim


def _fetch_claim(db: Session, claim_id: int) -> ReimbursementClaim:

    claim = db.get(ReimbursementClaim, claim_id)
    if not claim:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found.",
        )
    return claim


def manager_approve(
    db: Session, claim_id: int, payload: ManagerApprovalRequest
) -> ReimbursementClaim:

    claim = _fetch_claim(db, claim_id)
    if claim.status != "PENDING":
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot manager-approve a '{claim.status}' claim.",
        )
    if claim.manager_approval_status != "PENDING":
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            detail="Manager approval already recorded.",
        )
    _log(db, claim, "FINANCE_REVIEW", "MANAGER",
         payload.approved_by, payload.remarks)
    claim.manager_approval_status = "APPROVED"
    claim.manager_approved_by     = payload.approved_by
    claim.manager_approved_at     = _utcnow()
    claim.manager_remarks         = payload.remarks
    claim.status                  = "FINANCE_REVIEW"
    claim.updated_at              = _utcnow()
    db.commit()
    db.refresh(claim)
    return claim


def manager_reject(
    db: Session, claim_id: int, payload: ManagerApprovalRequest
) -> ReimbursementClaim:

    claim = _fetch_claim(db, claim_id)
    if claim.status != "PENDING":
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject a '{claim.status}' claim.",
        )
    _log(db, claim, "REJECTED", "MANAGER",
         payload.approved_by, payload.remarks)
    claim.manager_approval_status = "REJECTED"
    claim.manager_approved_by     = payload.approved_by
    claim.manager_approved_at     = _utcnow()
    claim.manager_remarks         = payload.remarks
    claim.status                  = "REJECTED"
    claim.updated_at              = _utcnow()
    db.commit()
    db.refresh(claim)
    return claim


def finance_approve(
    db: Session, claim_id: int, payload: FinanceApprovalRequest
) -> ReimbursementClaim:

    claim = _fetch_claim(db, claim_id)
    if claim.status != "FINANCE_REVIEW":
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finance-approve a '{claim.status}' claim.",
        )
    if claim.finance_approval_status != "PENDING":
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            detail="Finance approval already recorded.",
        )


    rtype   = db.get(ReimbursementType, claim.type_id)
    balance = db.execute(
        select(ReimbursementBalance)
        .where(
            ReimbursementBalance.employee_id == claim.employee_id,
            ReimbursementBalance.type_id     == claim.type_id,
            ReimbursementBalance.period      == _period_key(rtype.frequency),
        )
        .with_for_update()
    ).scalar_one_or_none()

    if balance:
        _debit_balance(db, balance, claim.claimed_amount)
        claim.balance_used      = balance.used_amount
        claim.balance_remaining = balance.remaining_amount

    _log(db, claim, "APPROVED", "FINANCE",
         payload.approved_by, payload.remarks)
    claim.finance_approval_status = "APPROVED"
    claim.finance_approved_by     = payload.approved_by
    claim.finance_approved_at     = _utcnow()
    claim.finance_remarks         = payload.remarks
    claim.status                  = "APPROVED"
    claim.updated_at              = _utcnow()

    db.commit()
    db.refresh(claim)
    return claim


def finance_reject(
    db: Session, claim_id: int, payload: FinanceApprovalRequest
) -> ReimbursementClaim:

    claim = _fetch_claim(db, claim_id)
    if claim.status != "FINANCE_REVIEW":
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finance-reject a '{claim.status}' claim.",
        )
    _log(db, claim, "REJECTED", "FINANCE",
         payload.approved_by, payload.remarks)
    claim.finance_approval_status = "REJECTED"
    claim.finance_approved_by     = payload.approved_by
    claim.finance_approved_at     = _utcnow()
    claim.finance_remarks         = payload.remarks
    claim.status                  = "REJECTED"
    claim.updated_at              = _utcnow()
    db.commit()
    db.refresh(claim)
    return claim

def mark_paid(
    db: Session, claim_id: int, payload: MarkPaidRequest
) -> ReimbursementClaim:

    claim = _fetch_claim(db, claim_id)
    if claim.status != "APPROVED":
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            detail=f"Only APPROVED claims can be marked PAID (current: '{claim.status}').",
        )
    _log(db, claim, "PAID", "PAYROLL",
         payload.processed_by,
         f"Payroll run #{payload.payroll_run_id}")
    claim.payroll_processed      = True
    claim.payroll_run_id         = payload.payroll_run_id
    claim.payroll_processed_date = payload.payroll_processed_date or _utcnow()
    claim.status                 = "PAID"
    claim.updated_at             = _utcnow()
    db.commit()
    db.refresh(claim)
    return claim


def get_dashboard(db: Session) -> ReimbursementDashboard:

    rows = db.execute(
        select(
            func.count(ReimbursementClaim.id).label("total"),
            func.coalesce(func.sum(ReimbursementClaim.claimed_amount), 0)
                .label("total_amt"),
            func.count(ReimbursementClaim.id)
                .filter(ReimbursementClaim.status == "APPROVED")
                .label("approved"),
            func.coalesce(
                func.sum(ReimbursementClaim.claimed_amount)
                .filter(ReimbursementClaim.status == "APPROVED"), 0
            ).label("approved_amt"),
            func.count(ReimbursementClaim.id)
                .filter(ReimbursementClaim.status.in_(["PENDING", "FINANCE_REVIEW"]))
                .label("pending"),
            func.coalesce(
                func.sum(ReimbursementClaim.claimed_amount)
                .filter(ReimbursementClaim.status.in_(["PENDING", "FINANCE_REVIEW"])), 0
            ).label("pending_amt"),
            func.count(ReimbursementClaim.id)
                .filter(ReimbursementClaim.status == "REJECTED")
                .label("rejected"),
            func.coalesce(
                func.sum(ReimbursementClaim.claimed_amount)
                .filter(ReimbursementClaim.status == "REJECTED"), 0
            ).label("rejected_amt"),
            func.coalesce(func.sum(ReimbursementClaim.tax_amount), 0)
                .label("total_tax"),
        )
    ).one()

    return ReimbursementDashboard(
        total_claims=rows.total,
        total_amount=_r2(rows.total_amt),
        approved_claims=rows.approved,
        approved_amount=_r2(rows.approved_amt),
        pending_claims=rows.pending,
        pending_amount=_r2(rows.pending_amt),
        rejected_claims=rows.rejected,
        rejected_amount=_r2(rows.rejected_amt),
        total_tax_amount=_r2(rows.total_tax),
    )


def get_reports(db: Session) -> ReimbursementReports:

    all_types: Sequence[ReimbursementType]  = list_types(db, active_only=False)
    all_claims: Sequence[ReimbursementClaim] = db.query(ReimbursementClaim).all()


    type_index = {t.id: t for t in all_types}
    type_map: dict = {}
    for c in all_claims:
        key = c.type_name
        if key not in type_map:
            t = type_index.get(c.type_id)
            type_map[key] = {
                "category":    t.category if t else "OTHER",
                "count":       0,
                "total":       Decimal("0"),
            }
        type_map[key]["count"] += 1
        type_map[key]["total"] += c.claimed_amount

 
    for t in all_types:
        if t.name not in type_map:
            type_map[t.name] = {"category": t.category, "count": 0,
                                "total": Decimal("0")}

    by_type = [
        ClaimsByTypeRow(
            type_name=name,
            category=v["category"],
            claim_count=v["count"],
            total_amount=_r2(v["total"]),
            avg_amount=_r2(v["total"] / v["count"]) if v["count"] else Decimal("0"),
        )
        for name, v in sorted(
            type_map.items(),
            key=lambda x: x[1]["total"], reverse=True
        )
    ]

 
    taxable_ids   = {t.id for t in all_types if t.is_taxable}
    taxable_amt   = Decimal("0")
    non_taxable   = Decimal("0")
    tax_deducted  = Decimal("0")
    for c in all_claims:
        if c.type_id in taxable_ids:
            taxable_amt  += c.claimed_amount
            tax_deducted += c.tax_amount
        else:
            non_taxable  += c.claimed_amount

    tax_analysis = TaxAnalysis(
        total_taxable_amount=_r2(taxable_amt),
        total_tax_amount=_r2(tax_deducted),
        total_non_taxable=_r2(non_taxable),
    )


    month_map: dict = {}
    for c in all_claims:
        key   = c.claim_date.strftime("%Y-%m")
        label = f"{_MONTH_NAMES[c.claim_date.month]} {c.claim_date.year}"
        if key not in month_map:
            month_map[key] = {
                "label":    label,
                "count":    0,
                "total":    Decimal("0"),
                "approved": 0,
                "pending":  0,
                "rejected": 0,
            }
        m = month_map[key]
        m["count"] += 1
        m["total"] += c.claimed_amount
        if c.status == "APPROVED":
            m["approved"] += 1
        elif c.status == "REJECTED":
            m["rejected"] += 1
        else:
            m["pending"] += 1

    monthly_trend = [
        MonthlyTrendRow(
            month=v["label"],
            claim_count=v["count"],
            total_amount=_r2(v["total"]),
            approved=v["approved"],
            pending=v["pending"],
            rejected=v["rejected"],
        )
        for _, v in sorted(month_map.items())
    ]

    emp_map: dict = {}
    for c in all_claims:
        k = c.employee_id
        if k not in emp_map:
            emp_map[k] = {
                "employee_id":   c.employee_id,
                "employee_name": c.employee_name,
                "count":         0,
                "total":         Decimal("0"),
            }
        emp_map[k]["count"] += 1
        emp_map[k]["total"] += c.claimed_amount

    top_employees = [
        TopEmployeeRow(
            employee_id=v["employee_id"],
            employee_name=v["employee_name"],
            claim_count=v["count"],
            total_amount=_r2(v["total"]),
        )
        for v in sorted(emp_map.values(),
                        key=lambda x: x["total"], reverse=True)[:10]
    ]

    return ReimbursementReports(
        by_type=by_type,
        tax_analysis=tax_analysis,
        monthly_trend=monthly_trend,
        top_employees=top_employees,
    )

def export_claims(
    db: Session,
    employee_id:  Optional[int]      = None,
    type_id:      Optional[int]      = None,
    claim_status: Optional[str]      = None,
    date_from:    Optional[datetime] = None,
    date_to:      Optional[datetime] = None,
    search:       Optional[str]      = None,
) -> List[ClaimExportRow]:
   
    claims = list_claims(
        db, employee_id=employee_id, type_id=type_id,
        claim_status=claim_status, date_from=date_from,
        date_to=date_to, search=search, skip=0, limit=10000,
    )
    return [
        ClaimExportRow(
            id=c.id,
            employee=c.employee_name,
            employee_id=c.employee_code,
            type=c.type_name,
            amount=c.claimed_amount,
            tax_amount=c.tax_amount,
            net_amount=c.net_amount,
            date=c.claim_date.strftime("%Y-%m-%d"),
            status=c.status,
            manager_status=c.manager_approval_status,
            finance_status=c.finance_approval_status,
            payroll_status="Processed" if c.payroll_processed else "Pending",
            description=c.description,
        )
        for c in claims
    ]