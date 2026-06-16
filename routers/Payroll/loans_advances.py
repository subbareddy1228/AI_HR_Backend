from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from schema.Payroll.loan_advance import (
    LoanAdvanceCreate,
    LoanAdvanceUpdate,
    LoanAdvanceResponse,
    LoanAdvanceDetailResponse,
    LoanEMIScheduleResponse,
    EMIPaymentRequest,
    LoanDashboard,
)
#import services.Payroll.loan_advance as svc

router = APIRouter(
    prefix="/loans",
    tags=["Payroll - Loans & Advances"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  STATIC ROUTES — defined BEFORE /{loan_id} to avoid FastAPI int-cast errors
# ══════════════════════════════════════════════════════════════════════════════

# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=LoanDashboard)
def get_dashboard(db: Session = Depends(get_db)):
    return svc.get_dashboard(db)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports")
def get_reports(db: Session = Depends(get_db)):
    return svc.get_reports(db)


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/export")
def export_loans():
    return {"message": "Export feature coming soon"}


# ── Filter / search ───────────────────────────────────────────────────────────

@router.get("/filter", response_model=List[LoanAdvanceResponse])
def filter_loans(
    status: Optional[str]      = None,
    loan_type: Optional[str]   = None,
    employee_id: Optional[int] = None,
    search: Optional[str]      = None,
    db: Session = Depends(get_db),
):
    return svc.get_all(db, status=status, loan_type=loan_type,
                       employee_id=employee_id, search=search)


# ── Employee loan history ─────────────────────────────────────────────────────

@router.get("/employee/{employee_id}", response_model=List[LoanAdvanceResponse])
def get_employee_loans(
    employee_id: int,
    db: Session = Depends(get_db),
):
    return svc.get_by_employee(db, employee_id)


# ══════════════════════════════════════════════════════════════════════════════
#  CORE CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=List[LoanAdvanceResponse])
def get_all_loans(db: Session = Depends(get_db)):
    return svc.get_all(db)


@router.post(
    "/",
    response_model=LoanAdvanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_loan(
    payload: LoanAdvanceCreate,
    db: Session = Depends(get_db),
):
    return svc.create(db, payload)


@router.get("/{loan_id}", response_model=LoanAdvanceDetailResponse)
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    loan = svc.get_by_id(db, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


@router.put("/{loan_id}", response_model=LoanAdvanceResponse)
def update_loan(
    loan_id: int,
    payload: LoanAdvanceUpdate,
    db: Session = Depends(get_db),
):
    loan = svc.update(db, loan_id, payload)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


@router.delete("/{loan_id}")
def delete_loan(loan_id: int, db: Session = Depends(get_db)):
    result = svc.delete(db, loan_id)
    if result is None:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an ACTIVE loan. Reject it first."
        )
    if result is False:
        raise HTTPException(status_code=404, detail="Loan not found")
    return {"message": "Loan deleted successfully"}


# ══════════════════════════════════════════════════════════════════════════════
#  WORKFLOW ACTIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.put("/{loan_id}/approve")
def approve_loan(
    loan_id: int,
    approved_by: Optional[str] = None,
    remarks: Optional[str]     = None,
    db: Session = Depends(get_db),
):
    loan, error = svc.approve(db, loan_id, approved_by, remarks)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Loan approved successfully"}


@router.put("/{loan_id}/reject")
def reject_loan(
    loan_id: int,
    approved_by: Optional[str] = None,
    remarks: Optional[str]     = None,
    db: Session = Depends(get_db),
):
    loan, error = svc.reject(db, loan_id, approved_by, remarks)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Loan rejected successfully"}


# ══════════════════════════════════════════════════════════════════════════════
#  EMI
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{loan_id}/emi-schedule",
    response_model=List[LoanEMIScheduleResponse],
)
def get_emi_schedule(loan_id: int, db: Session = Depends(get_db)):
    schedule = svc.get_emi_schedule(db, loan_id)
    if schedule == [] and not svc.get_by_id(db, loan_id):
        raise HTTPException(status_code=404, detail="Loan not found")
    return schedule


@router.put("/{loan_id}/pay-emi")
def pay_emi(
    loan_id: int,
    payload: EMIPaymentRequest,
    db: Session = Depends(get_db),
):
    loan, error = svc.pay_emi(db, loan_id, payload)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "EMI payment recorded successfully"}