from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from typing import List, Optional
from datetime import date, timedelta, datetime, timezone

from core.database import get_db
from model.Payroll.loan_advance import LoanAdvance, LoanEMISchedule
from schema.Payroll.loan_advance import (
    LoanAdvanceCreate,
    LoanAdvanceUpdate,
    LoanAdvanceResponse,
    LoanAdvanceDetailResponse,
    EMIPaymentRequest,
    LoanEMIScheduleResponse,
)

router = APIRouter(
    prefix="/loans",
    tags=["Loans & Advances"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_loan_or_404(loan_id: int, db: Session) -> LoanAdvance:
    loan = (
        db.query(LoanAdvance)
        .filter(LoanAdvance.id == loan_id)
        .first()
    )
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


def _generate_loan_id(db: Session) -> str:
    count = db.query(LoanAdvance).count()
    return f"LN{str(count + 1).zfill(4)}"


def _build_emi_schedule(loan: LoanAdvance, db: Session) -> None:
    """Generate EMI schedule rows for a loan after approval."""
    if not loan.emi_amount or not loan.tenure_months or not loan.start_date:
        return

    # Clear any existing schedule
    db.query(LoanEMISchedule).filter(
        LoanEMISchedule.loan_id == loan.id
    ).delete()

    balance       = loan.principal_amount
    rate_monthly  = (loan.interest_rate or 0.0) / (12 * 100)
    due_date      = loan.start_date

    for i in range(1, loan.tenure_months + 1):
        if loan.interest_method == "Reducing Balance" and rate_monthly > 0:
            interest_part  = round(balance * rate_monthly, 2)
            principal_part = round(loan.emi_amount - interest_part, 2)
        elif loan.interest_method == "Flat" and rate_monthly > 0:
            interest_part  = round(loan.principal_amount * rate_monthly, 2)
            principal_part = round(loan.emi_amount - interest_part, 2)
        else:
            interest_part  = 0.0
            principal_part = round(loan.emi_amount, 2)

        balance = round(max(balance - principal_part, 0), 2)

        schedule = LoanEMISchedule(
            loan_id        = loan.id,
            installment_no = i,
            due_date       = due_date,
            emi_amount     = loan.emi_amount,
            principal_part = principal_part,
            interest_part  = interest_part,
            balance        = balance,
            status         = "PENDING",
        )
        db.add(schedule)

        # Advance due date by 1 month
        month = due_date.month + 1
        year  = due_date.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        due_date = due_date.replace(year=year, month=month)

    db.flush()


# ── NOTE: All static routes (/filter, /reports, /export, /employee/{id})
#    are defined BEFORE /{loan_id} to avoid FastAPI casting "filter" as int


# ── Filter / search ───────────────────────────────────────────────────────────

@router.get("/filter")
def filter_loans(
    status: Optional[str]     = None,
    loan_type: Optional[str]  = None,
    employee_id: Optional[int] = None,
    search: Optional[str]     = None,
    db: Session = Depends(get_db),
):
    query = db.query(LoanAdvance)

    if status:
        query = query.filter(
            LoanAdvance.status == status.upper()
        )

    if loan_type:
        query = query.filter(
            LoanAdvance.loan_type.ilike(f"%{loan_type}%")
        )

    if employee_id:
        query = query.filter(
            LoanAdvance.employee_id == employee_id
        )

    if search:
        query = query.filter(
            or_(
                LoanAdvance.loan_id.ilike(f"%{search}%"),
                LoanAdvance.loan_type.ilike(f"%{search}%"),
                LoanAdvance.status.ilike(f"%{search}%"),
                cast(LoanAdvance.employee_id, String).ilike(f"%{search}%"),
                cast(LoanAdvance.principal_amount, String).ilike(f"%{search}%"),
            )
        )

    return query.order_by(LoanAdvance.id.desc()).all()


# ── Dashboard reports ─────────────────────────────────────────────────────────

@router.get("/reports")
def loan_reports(
    db: Session = Depends(get_db),
):
    loans = db.query(LoanAdvance).all()

    total_loans   = len(loans)
    active_loans  = len([l for l in loans if l.status == "ACTIVE"])
    pending_loans = len([l for l in loans if l.status == "PENDING"])
    completed     = len([l for l in loans if l.status == "COMPLETED"])
    rejected      = len([l for l in loans if l.status == "REJECTED"])

    total_amount   = round(sum(l.principal_amount for l in loans), 2)
    active_amount  = round(sum(l.principal_amount for l in loans if l.status == "ACTIVE"), 2)
    pending_amount = round(sum(l.amount_pending for l in loans if l.status == "ACTIVE"), 2)
    paid_amount    = round(sum(l.amount_paid for l in loans), 2)

    # Breakdown by loan type
    type_breakdown = {}
    for l in loans:
        type_breakdown.setdefault(l.loan_type, {"count": 0, "total_amount": 0.0})
        type_breakdown[l.loan_type]["count"] += 1
        type_breakdown[l.loan_type]["total_amount"] = round(
            type_breakdown[l.loan_type]["total_amount"] + l.principal_amount, 2
        )

    return {
        "total_loans"   : total_loans,
        "active_loans"  : active_loans,
        "pending_loans" : pending_loans,
        "completed"     : completed,
        "rejected"      : rejected,
        "total_amount"  : total_amount,
        "active_amount" : active_amount,
        "pending_amount": pending_amount,
        "paid_amount"   : paid_amount,
        "by_loan_type"  : type_breakdown,
    }


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/export")
def export_loans():
    return {"message": "Export feature coming soon"}


# ── Employee loan history ─────────────────────────────────────────────────────

@router.get(
    "/employee/{employee_id}",
    response_model=List[LoanAdvanceResponse],
)
def employee_loans(
    employee_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(LoanAdvance)
        .filter(LoanAdvance.employee_id == employee_id)
        .order_by(LoanAdvance.id.desc())
        .all()
    )


# ── Create loan ───────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=LoanAdvanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_loan(
    payload: LoanAdvanceCreate,
    db: Session = Depends(get_db),
):
    data               = payload.model_dump()
    data["loan_id"]    = _generate_loan_id(db)
    data["amount_pending"] = data["principal_amount"]
    data["amount_paid"]    = 0.0
    data["status"]         = "PENDING"

    loan = LoanAdvance(**data)
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


# ── Get all loans ─────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[LoanAdvanceResponse],
)
def get_all_loans(
    db: Session = Depends(get_db),
):
    return (
        db.query(LoanAdvance)
        .order_by(LoanAdvance.id.desc())
        .all()
    )


# ── Get loan by ID (with EMI schedule) ───────────────────────────────────────

@router.get(
    "/{loan_id}",
    response_model=LoanAdvanceDetailResponse,
)
def get_loan_by_id(
    loan_id: int,
    db: Session = Depends(get_db),
):
    loan = _get_loan_or_404(loan_id, db)
    return loan


# ── Update loan ───────────────────────────────────────────────────────────────

@router.put(
    "/{loan_id}",
    response_model=LoanAdvanceResponse,
)
def update_loan(
    loan_id: int,
    payload: LoanAdvanceUpdate,
    db: Session = Depends(get_db),
):
    loan = _get_loan_or_404(loan_id, db)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(loan, key, value)

    db.commit()
    db.refresh(loan)
    return loan


# ── Delete loan ───────────────────────────────────────────────────────────────

@router.delete("/{loan_id}")
def delete_loan(
    loan_id: int,
    db: Session = Depends(get_db),
):
    loan = _get_loan_or_404(loan_id, db)

    if loan.status == "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an active loan. Reject or cancel it first."
        )

    db.delete(loan)
    db.commit()
    return {"message": "Loan deleted successfully"}


# ── Approve loan ──────────────────────────────────────────────────────────────

@router.put("/{loan_id}/approve")
def approve_loan(
    loan_id: int,
    approved_by: Optional[str] = None,
    remarks: Optional[str]     = None,
    db: Session = Depends(get_db),
):
    loan = _get_loan_or_404(loan_id, db)

    if loan.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Only PENDING loans can be approved. Current status: {loan.status}"
        )

    loan.status      = "ACTIVE"
    loan.approved_by = approved_by
    loan.remarks     = remarks

    # Auto-generate EMI schedule on approval
    _build_emi_schedule(loan, db)

    # Set next due date from first EMI
    first_emi = (
        db.query(LoanEMISchedule)
        .filter(
            LoanEMISchedule.loan_id        == loan.id,
            LoanEMISchedule.installment_no == 1,
        )
        .first()
    )
    if first_emi:
        loan.next_due_date = first_emi.due_date

    db.commit()
    db.refresh(loan)
    return {"message": "Loan approved successfully"}


# ── Reject loan ───────────────────────────────────────────────────────────────

@router.put("/{loan_id}/reject")
def reject_loan(
    loan_id: int,
    approved_by: Optional[str] = None,
    remarks: Optional[str]     = None,
    db: Session = Depends(get_db),
):
    loan = _get_loan_or_404(loan_id, db)

    if loan.status not in ("PENDING", "ACTIVE"):
        raise HTTPException(
            status_code=400,
            detail="Only PENDING or ACTIVE loans can be rejected."
        )

    loan.status      = "REJECTED"
    loan.approved_by = approved_by
    loan.remarks     = remarks

    db.commit()
    db.refresh(loan)
    return {"message": "Loan rejected successfully"}


# ── Record EMI payment ────────────────────────────────────────────────────────

@router.put("/{loan_id}/pay-emi")
def pay_emi(
    loan_id: int,
    payload: EMIPaymentRequest,
    db: Session = Depends(get_db),
):
    loan = _get_loan_or_404(loan_id, db)

    if loan.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="EMI payments can only be recorded for ACTIVE loans."
        )

    emi = (
        db.query(LoanEMISchedule)
        .filter(
            LoanEMISchedule.loan_id        == loan.id,
            LoanEMISchedule.installment_no == payload.installment_no,
        )
        .first()
    )

    if not emi:
        raise HTTPException(status_code=404, detail="EMI installment not found")

    if emi.status == "PAID":
        raise HTTPException(status_code=400, detail="This installment is already paid")

    emi.paid_amount = round(emi.paid_amount + payload.paid_amount, 2)
    emi.paid_date   = payload.paid_date
    emi.status      = "PAID" if emi.paid_amount >= emi.emi_amount else "PARTIAL"

    # Update loan totals
    loan.amount_paid    = round(loan.amount_paid + payload.paid_amount, 2)
    loan.amount_pending = round(max(loan.principal_amount - loan.amount_paid, 0), 2)

    # Update next due date to the next PENDING installment
    next_pending = (
        db.query(LoanEMISchedule)
        .filter(
            LoanEMISchedule.loan_id == loan.id,
            LoanEMISchedule.status  == "PENDING",
        )
        .order_by(LoanEMISchedule.due_date.asc())
        .first()
    )
    loan.next_due_date = next_pending.due_date if next_pending else None

    # Mark loan completed if fully paid
    if loan.amount_pending <= 0:
        loan.status        = "COMPLETED"
        loan.next_due_date = None

    db.commit()
    db.refresh(loan)
    return {"message": "EMI payment recorded successfully"}


# ── EMI schedule for a loan ───────────────────────────────────────────────────

@router.get(
    "/{loan_id}/emi-schedule",
    response_model=List[LoanEMIScheduleResponse],
)
def get_emi_schedule(
    loan_id: int,
    db: Session = Depends(get_db),
):
    loan = _get_loan_or_404(loan_id, db)

    return (
        db.query(LoanEMISchedule)
        .filter(LoanEMISchedule.loan_id == loan.id)
        .order_by(LoanEMISchedule.installment_no.asc())
        .all()
    )