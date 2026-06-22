from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from typing import Optional, List
from datetime import date, datetime, timezone

from model.Payroll.loan_advance import LoanAdvance, LoanEMISchedule
from schema.Payroll.loan_advance import (
    LoanAdvanceCreate,
    LoanAdvanceUpdate,
    EMIPaymentRequest,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_loan_id(db: Session) -> str:
    count = db.query(LoanAdvance).count()
    return f"LN{str(count + 1).zfill(3)}"


def _get_by_id(db: Session, loan_id: int) -> Optional[LoanAdvance]:
    return db.query(LoanAdvance).filter(LoanAdvance.id == loan_id).first()


def _build_emi_schedule(db: Session, loan: LoanAdvance) -> None:
    """Generate month-by-month EMI rows after loan is approved."""
    if not (loan.emi_amount and loan.tenure_months and loan.start_date):
        return

    # Clear old schedule if any
    db.query(LoanEMISchedule).filter(
        LoanEMISchedule.loan_id == loan.id
    ).delete()

    balance      = loan.principal_amount
    r            = (loan.interest_rate or 0.0) / (12 * 100)
    due_date     = loan.start_date

    for i in range(1, loan.tenure_months + 1):
        if loan.interest_method == "Reducing Balance" and r > 0:
            interest_part  = round(balance * r, 2)
            principal_part = round(loan.emi_amount - interest_part, 2)
        elif loan.interest_method == "Flat" and r > 0:
            interest_part  = round(loan.principal_amount * r, 2)
            principal_part = round(loan.emi_amount - interest_part, 2)
        else:
            interest_part  = 0.0
            principal_part = round(loan.emi_amount, 2)

        balance = round(max(balance - principal_part, 0.0), 2)

        db.add(LoanEMISchedule(
            loan_id        = loan.id,
            installment_no = i,
            due_date       = due_date,
            emi_amount     = loan.emi_amount,
            principal_part = principal_part,
            interest_part  = interest_part,
            balance        = balance,
            status         = "PENDING",
        ))

        # Advance 1 month
        m = due_date.month % 12 + 1
        y = due_date.year + (1 if due_date.month == 12 else 0)
        try:
            due_date = due_date.replace(year=y, month=m)
        except ValueError:
            import calendar
            last_day = calendar.monthrange(y, m)[1]
            due_date = due_date.replace(year=y, month=m, day=last_day)

    db.flush()


# ── CRUD ──────────────────────────────────────────────────────────────────────

def get_all(
    db: Session,
    status: Optional[str]      = None,
    loan_type: Optional[str]   = None,
    employee_id: Optional[int] = None,
    search: Optional[str]      = None,
) -> List[LoanAdvance]:
    q = db.query(LoanAdvance)

    if status:
        q = q.filter(LoanAdvance.status == status.upper())
    if loan_type:
        q = q.filter(LoanAdvance.loan_type.ilike(f"%{loan_type}%"))
    if employee_id:
        q = q.filter(LoanAdvance.employee_id == employee_id)
    if search:
        q = q.filter(
            or_(
                LoanAdvance.loan_id.ilike(f"%{search}%"),
                LoanAdvance.loan_type.ilike(f"%{search}%"),
                LoanAdvance.status.ilike(f"%{search}%"),
                cast(LoanAdvance.employee_id, String).ilike(f"%{search}%"),
                cast(LoanAdvance.principal_amount, String).ilike(f"%{search}%"),
            )
        )
    return q.order_by(LoanAdvance.id.desc()).all()


def get_by_id(db: Session, loan_id: int) -> Optional[LoanAdvance]:
    return _get_by_id(db, loan_id)


def get_by_employee(db: Session, employee_id: int) -> List[LoanAdvance]:
    return (
        db.query(LoanAdvance)
        .filter(LoanAdvance.employee_id == employee_id)
        .order_by(LoanAdvance.id.desc())
        .all()
    )


def create(db: Session, payload: LoanAdvanceCreate):
    data = payload.model_dump()
    data["loan_id"]        = _generate_loan_id(db)
    data["amount_pending"] = data["principal_amount"]
    data["amount_paid"]    = 0.0
    data["status"]         = "PENDING"

    loan = LoanAdvance(**data)
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def update(db: Session, loan_id: int, payload: LoanAdvanceUpdate):
    loan = _get_by_id(db, loan_id)
    if not loan:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(loan, key, value)
    db.commit()
    db.refresh(loan)
    return loan


def delete(db: Session, loan_id: int) -> bool:
    loan = _get_by_id(db, loan_id)
    if not loan:
        return False
    if loan.status == "ACTIVE":
        return None  # signal: cannot delete active
    db.delete(loan)
    db.commit()
    return True


# ── Workflow actions ──────────────────────────────────────────────────────────

def approve(
    db: Session,
    loan_id: int,
    approved_by: Optional[str],
    remarks: Optional[str],
):
    loan = _get_by_id(db, loan_id)
    if not loan:
        return None, "Loan not found"
    if loan.status != "PENDING":
        return None, f"Only PENDING loans can be approved. Current: {loan.status}"

    loan.status        = "ACTIVE"
    loan.approved_by   = approved_by
    loan.approved_date = date.today()
    loan.remarks       = remarks

    # Auto-generate EMI schedule
    _build_emi_schedule(db, loan)

    # Set next due date from first EMI
    first = (
        db.query(LoanEMISchedule)
        .filter(
            LoanEMISchedule.loan_id        == loan.id,
            LoanEMISchedule.installment_no == 1,
        )
        .first()
    )
    if first:
        loan.next_due_date = first.due_date

    db.commit()
    db.refresh(loan)
    return loan, None


def reject(
    db: Session,
    loan_id: int,
    approved_by: Optional[str],
    remarks: Optional[str],
):
    loan = _get_by_id(db, loan_id)
    if not loan:
        return None, "Loan not found"
    if loan.status not in ("PENDING", "ACTIVE"):
        return None, "Only PENDING or ACTIVE loans can be rejected."

    loan.status      = "REJECTED"
    loan.approved_by = approved_by
    loan.remarks     = remarks

    db.commit()
    db.refresh(loan)
    return loan, None


# ── EMI payment ───────────────────────────────────────────────────────────────

def pay_emi(db: Session, loan_id: int, payload: EMIPaymentRequest):
    loan = _get_by_id(db, loan_id)
    if not loan:
        return None, "Loan not found"
    if loan.status != "ACTIVE":
        return None, "EMI can only be paid for ACTIVE loans."

    emi = (
        db.query(LoanEMISchedule)
        .filter(
            LoanEMISchedule.loan_id        == loan.id,
            LoanEMISchedule.installment_no == payload.installment_no,
        )
        .first()
    )
    if not emi:
        return None, "Installment not found"
    if emi.status == "PAID":
        return None, "Installment already paid"

    emi.paid_amount = round(emi.paid_amount + payload.paid_amount, 2)
    emi.paid_date   = payload.paid_date
    emi.status      = "PAID" if emi.paid_amount >= emi.emi_amount else "PARTIAL"

    # Update loan totals
    loan.amount_paid    = round(loan.amount_paid + payload.paid_amount, 2)
    loan.amount_pending = round(max(loan.principal_amount - loan.amount_paid, 0.0), 2)

    # Advance next due date
    next_pending = (
        db.query(LoanEMISchedule)
        .filter(
            LoanEMISchedule.loan_id == loan.id,
            LoanEMISchedule.status.in_(["PENDING", "PARTIAL"]),
        )
        .order_by(LoanEMISchedule.due_date.asc())
        .first()
    )
    loan.next_due_date = next_pending.due_date if next_pending else None

    # Mark completed if fully paid
    if loan.amount_pending <= 0:
        loan.status        = "COMPLETED"
        loan.next_due_date = None

    db.commit()
    db.refresh(loan)
    return loan, None


# ── EMI schedule ──────────────────────────────────────────────────────────────

def get_emi_schedule(db: Session, loan_id: int) -> List[LoanEMISchedule]:
    loan = _get_by_id(db, loan_id)
    if not loan:
        return []
    return (
        db.query(LoanEMISchedule)
        .filter(LoanEMISchedule.loan_id == loan.id)
        .order_by(LoanEMISchedule.installment_no.asc())
        .all()
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_dashboard(db: Session) -> dict:
    loans = db.query(LoanAdvance).all()
    return {
        "total_loans"   : len(loans),
        "active_loans"  : len([l for l in loans if l.status == "ACTIVE"]),
        "pending_loans" : len([l for l in loans if l.status == "PENDING"]),
        "completed"     : len([l for l in loans if l.status == "COMPLETED"]),
        "total_amount"  : round(sum(l.principal_amount for l in loans), 2),
        "pending_amount": round(sum(l.amount_pending for l in loans if l.status == "ACTIVE"), 2),
    }


# ── Reports ───────────────────────────────────────────────────────────────────

def get_reports(db: Session) -> dict:
    loans = db.query(LoanAdvance).all()

    # By loan type
    type_breakdown = {}
    for l in loans:
        type_breakdown.setdefault(l.loan_type, {"count": 0, "total_amount": 0.0, "active": 0})
        type_breakdown[l.loan_type]["count"]        += 1
        type_breakdown[l.loan_type]["total_amount"]  = round(
            type_breakdown[l.loan_type]["total_amount"] + l.principal_amount, 2
        )
        if l.status == "ACTIVE":
            type_breakdown[l.loan_type]["active"] += 1

    # By interest method
    method_breakdown = {}
    for l in loans:
        m = l.interest_method or "No Interest"
        method_breakdown.setdefault(m, {"count": 0, "total_amount": 0.0})
        method_breakdown[m]["count"]       += 1
        method_breakdown[m]["total_amount"] = round(
            method_breakdown[m]["total_amount"] + l.principal_amount, 2
        )

    return {
        "summary"          : get_dashboard(db),
        "by_loan_type"     : type_breakdown,
        "by_interest_method": method_breakdown,
    }