

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Tuple

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from model.onboarding.employee import Employee
from model.Payroll.loan_advance import LoanAdvance, LoanRepayment
from schema.Payroll.loan_advance import (
    LoanApplicationCreate,
    LoanApprovalRequest,
    LoanAdvanceUpdate,
    LoanDashboardStats,
    LoanListFilter,
    LoanRejectionRequest,
    RecordRepaymentRequest,
)

TWO_PLACES = Decimal("0.01")

def _get_employee_or_404(db: Session, employee_id: int) -> Employee:
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Employee {employee_id} not found.")
    return emp


def _next_loan_code(db: Session) -> str:

    count = db.query(func.count(LoanAdvance.id)).scalar() or 0
    return f"LN{count + 1:03d}"


def _get_loan_or_404(db: Session, loan_id: int) -> LoanAdvance:
    loan = db.get(LoanAdvance, loan_id)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Loan / advance record not found.")
    return loan


@dataclass
class _EmiPlan:
    emi_amount: Decimal
    schedule: List[Tuple[int, date, Decimal]]   # (installment_number, due_date, emi_amount)


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _build_emi_plan(
    principal: Decimal,
    annual_rate_pct: Decimal,
    tenure_months: int,
    method: str,
    issue_date: date,
) -> _EmiPlan:

    n = tenure_months
    monthly_rate = annual_rate_pct / Decimal("100") / Decimal("12")

    if method == "Interest Free" or annual_rate_pct == 0:
        emi = _round(principal / n)

    elif method == "Flat Rate":
        total_interest = _round(principal * annual_rate_pct / 100 * n / 12)
        emi = _round((principal + total_interest) / n)

    elif method == "Reducing Balance":
        if monthly_rate == 0:
            emi = _round(principal / n)
        else:
            factor = (1 + monthly_rate) ** n
            emi = _round(principal * monthly_rate * factor / (factor - 1))

    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported interest method: {method}",
        )

    schedule: List[Tuple[int, date, Decimal]] = []
    running_total = Decimal("0")
    for i in range(1, n + 1):
        due = issue_date + relativedelta(months=i)

        if i == n:
            installment_amount = _round(principal - running_total) if method != "Reducing Balance" else emi
        else:
            installment_amount = emi
        running_total += installment_amount
        schedule.append((i, due, installment_amount))

    return _EmiPlan(emi_amount=emi, schedule=schedule)


def _recalculate_totals(loan: LoanAdvance) -> None:

    paid = sum((r.paid_amount or Decimal("0")) for r in loan.repayments if r.status == "PAID")
    pending = sum(r.emi_amount for r in loan.repayments if r.status in ("PENDING", "OVERDUE"))
    loan.total_paid = _round(Decimal(str(paid)))
    loan.total_pending = _round(Decimal(str(pending)))
    loan.paid_installments = sum(1 for r in loan.repayments if r.status == "PAID")

    next_due = (
        min((r.due_date for r in loan.repayments if r.status in ("PENDING", "OVERDUE")), default=None)
    )
    loan.next_due_date = next_due

    if loan.paid_installments >= (loan.total_installments or 0) and loan.total_installments:
        loan.status = "COMPLETED"
        loan.closed_date = max((r.paid_date for r in loan.repayments if r.paid_date), default=date.today())


def apply_for_loan(db: Session, payload: LoanApplicationCreate) -> LoanAdvance:
    emp = _get_employee_or_404(db, payload.employee_id)

    loan = LoanAdvance(
        loan_code        = _next_loan_code(db),
        employee_id      = emp.id,
        employee_code    = emp.employee_code,
        employee_name    = f"{emp.first_name} {emp.last_name or ''}".strip(),
        designation      = emp.designation,
        department       = emp.department,
        loan_type        = payload.loan_type,
        amount           = payload.amount,
        reason           = payload.reason,
        interest_rate    = payload.interest_rate,
        interest_method  = payload.interest_method,
        repayment_mode   = payload.repayment_mode,
        total_installments = payload.requested_tenure_months,
        status           = "PENDING",
        total_pending    = payload.amount,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def approve_loan(db: Session, loan_id: int, payload: LoanApprovalRequest) -> LoanAdvance:
    loan = _get_loan_or_404(db, loan_id)

    if loan.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only PENDING loans can be approved (current status: {loan.status}).",
        )

    if payload.approved_amount > loan.amount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Approved amount cannot exceed the requested amount.",
        )

    interest_rate   = payload.interest_rate if payload.interest_rate is not None else loan.interest_rate
    interest_method = payload.interest_method or loan.interest_method

    plan = _build_emi_plan(
        principal=payload.approved_amount,
        annual_rate_pct=interest_rate,
        tenure_months=payload.total_installments,
        method=interest_method,
        issue_date=payload.issue_date,
    )

    loan.approved_amount     = payload.approved_amount
    loan.approved_by         = payload.approved_by
    loan.approved_at         = datetime.utcnow()
    loan.interest_rate       = interest_rate
    loan.interest_method     = interest_method
    loan.emi_amount          = plan.emi_amount
    loan.total_installments  = payload.total_installments
    loan.issue_date          = payload.issue_date
    loan.end_date            = plan.schedule[-1][1] if plan.schedule else None
    loan.next_due_date       = plan.schedule[0][1] if plan.schedule else None
    loan.total_pending       = payload.approved_amount
    loan.total_paid          = Decimal("0")
    loan.paid_installments   = 0
    loan.status              = "ACTIVE"

    for installment_number, due_date, emi_amount in plan.schedule:
        db.add(LoanRepayment(
            loan_id=loan.id,
            installment_number=installment_number,
            due_date=due_date,
            emi_amount=emi_amount,
            status="PENDING",
        ))

    db.commit()
    db.refresh(loan)
    return loan


def reject_loan(db: Session, loan_id: int, payload: LoanRejectionRequest) -> LoanAdvance:
    loan = _get_loan_or_404(db, loan_id)
    if loan.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only PENDING loans can be rejected (current status: {loan.status}).",
        )
    loan.status            = "REJECTED"
    loan.approved_by        = payload.approved_by
    loan.rejection_reason   = payload.rejection_reason
    loan.approved_at        = datetime.utcnow()
    db.commit()
    db.refresh(loan)
    return loan


def update_loan(db: Session, loan_id: int, payload: LoanAdvanceUpdate) -> LoanAdvance:
    loan = _get_loan_or_404(db, loan_id)

    if loan.status in ("COMPLETED", "REJECTED") and payload.model_dump(exclude_unset=True):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit a loan with status '{loan.status}'.",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(loan, field, value)

    db.commit()
    db.refresh(loan)
    return loan


def delete_loan(db: Session, loan_id: int) -> None:
    loan = _get_loan_or_404(db, loan_id)
    if loan.status == "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete an ACTIVE loan with an ongoing EMI schedule. Close it first.",
        )
    db.delete(loan)
    db.commit()


def record_repayment(
    db: Session, loan_id: int, payload: RecordRepaymentRequest
) -> LoanAdvance:
    loan = _get_loan_or_404(db, loan_id)

    if loan.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repayments can only be recorded for ACTIVE loans (current status: {loan.status}).",
        )

    if payload.installment_number is not None:
        installment = next(
            (r for r in loan.repayments if r.installment_number == payload.installment_number), None
        )
        if not installment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Installment #{payload.installment_number} not found.")
    else:
        installment = next(
            (r for r in sorted(loan.repayments, key=lambda r: r.installment_number)
             if r.status in ("PENDING", "OVERDUE")),
            None,
        )
        if not installment:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="No outstanding installments remain for this loan.")

    if installment.status == "PAID":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Installment #{installment.installment_number} is already PAID.")

    installment.status            = "PAID"
    installment.paid_amount        = payload.paid_amount
    installment.paid_date          = payload.paid_date
    installment.payment_reference  = payload.payment_reference

    _recalculate_totals(loan)
    db.commit()
    db.refresh(loan)
    return loan


def mark_overdue_repayments(db: Session) -> int:

    today = date.today()
    overdue_rows = (
        db.query(LoanRepayment)
        .filter(LoanRepayment.status == "PENDING", LoanRepayment.due_date < today)
        .all()
    )
    for row in overdue_rows:
        row.status = "OVERDUE"
    db.commit()
    return len(overdue_rows)


_TAB_STATUS_MAP = {
    "pending":   ["PENDING"],
    "active":    ["ACTIVE"],
    "completed": ["COMPLETED"],
}


def list_loans(db: Session, f: LoanListFilter) -> Tuple[List[LoanAdvance], int]:
    q = db.query(LoanAdvance)

    if f.search:
        pattern = f"%{f.search}%"
        q = q.filter(
            or_(
                LoanAdvance.employee_name.ilike(pattern),
                LoanAdvance.employee_code.ilike(pattern),
                LoanAdvance.loan_code.ilike(pattern),
            )
        )
    if f.loan_type:
        q = q.filter(LoanAdvance.loan_type == f.loan_type)
    if f.status:
        q = q.filter(LoanAdvance.status == f.status)
    elif f.tab and f.tab != "all":
        q = q.filter(LoanAdvance.status.in_(_TAB_STATUS_MAP[f.tab]))

    total = q.count()
    loans = (
        q.order_by(LoanAdvance.created_at.desc())
        .offset(f.skip)
        .limit(f.limit)
        .all()
    )
    return loans, total


def get_loan(db: Session, loan_id: int) -> LoanAdvance:
    return _get_loan_or_404(db, loan_id)


def get_loans_by_employee(db: Session, employee_id: int) -> List[LoanAdvance]:
    return (
        db.query(LoanAdvance)
        .filter(LoanAdvance.employee_id == employee_id)
        .order_by(LoanAdvance.created_at.desc())
        .all()
    )

def get_dashboard_stats(db: Session) -> LoanDashboardStats:
    total_loans = db.query(func.count(LoanAdvance.id)).scalar() or 0

    status_counts = dict(
        db.query(LoanAdvance.status, func.count(LoanAdvance.id))
        .group_by(LoanAdvance.status)
        .all()
    )
    pending_count   = status_counts.get("PENDING", 0)
    active_count    = status_counts.get("ACTIVE", 0)
    completed_count = status_counts.get("COMPLETED", 0)

    
    total_amount = (
        db.query(
            func.coalesce(
                func.sum(func.coalesce(LoanAdvance.approved_amount, LoanAdvance.amount)), 0
            )
        )
        .filter(LoanAdvance.status != "REJECTED")
        .scalar()
    )

    pending_amount = (
        db.query(func.coalesce(func.sum(LoanAdvance.total_pending), 0))
        .filter(LoanAdvance.status == "ACTIVE")
        .scalar()
    )

    return LoanDashboardStats(
        total_loans=total_loans,
        pending_count=pending_count,
        active_count=active_count,
        completed_count=completed_count,
        total_amount=_round(Decimal(str(total_amount))),
        pending_amount=_round(Decimal(str(pending_amount))),
    )
