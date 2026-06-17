"""
Loan & Advance Router — /api/payroll/loans

UI sections mapped to endpoint groups:
  • KPI cards (Total Loans, Active Loans, Total Amount, Pending Amount)
        → GET  /dashboard/stats
  • Filter tabs (All Loans / Pending / Active / Completed)
        → GET  /  (tab query param)
  • Search & filter bar (employee name/ID/loan ID, loan type, status)
        → GET  /  (search, loan_type, status query params)
  • Apply for Loan modal
        → POST /apply
  • Row actions (view / edit / approve / reject / delete icons)
        → GET /{id}, PATCH /{id}, POST /{id}/approve, POST /{id}/reject, DELETE /{id}
  • EMI & repayment tracking
        → POST /{id}/repayments, GET /{id}/repayments
  • Export
        → GET  /export
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.session import get_db
from schema.Payroll.loan_advance import (
    LoanAdvanceDetailResponse,
    LoanAdvanceResponse,
    LoanAdvanceUpdate,
    LoanApplicationCreate,
    LoanApprovalRequest,
    LoanDashboardStats,
    LoanListFilter,
    LoanRejectionRequest,
    LoanRepaymentResponse,
    PaginatedLoanResponse,
    RecordRepaymentRequest,
)
from services.Payroll.loan_advance_service import (
    apply_for_loan,
    approve_loan,
    delete_loan,
    get_dashboard_stats,
    get_loan,
    get_loans_by_employee,
    list_loans,
    mark_overdue_repayments,
    record_repayment,
    reject_loan,
    update_loan,
)

router = APIRouter(prefix="/loans", tags=["Loans & Advances"])


# ─────────────────────────────────────────────────────────────────────────────
# KPI cards
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/dashboard/stats",
    response_model=LoanDashboardStats,
    summary="Get KPI card values: Total Loans, Active Loans, Total Amount, Pending Amount",
)
def dashboard_stats(db: Session = Depends(get_db)):
    return get_dashboard_stats(db)


# ─────────────────────────────────────────────────────────────────────────────
# Apply for Loan
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/apply",
    response_model=LoanAdvanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for Loan — creates a PENDING loan/advance request",
)
def apply(payload: LoanApplicationCreate, db: Session = Depends(get_db)):
    """
    Generates a unique loan_code (LN001, LN002, ...) and stores the
    requested amount, loan type, interest terms, and repayment mode.
    """
    return apply_for_loan(db, payload)


# ─────────────────────────────────────────────────────────────────────────────
# List / search / filter — main table + tabs
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=PaginatedLoanResponse,
    summary="List loans with search, loan type, status, and tab filters",
)
def list_all_loans(
    search:    Optional[str] = Query(default=None, description="Employee name, ID, or loan ID"),
    loan_type: Optional[str] = Query(default=None, description="Filter by loan type"),
    loan_status: Optional[str] = Query(default=None, alias="status"),
    tab:       Optional[str] = Query(
        default="all",
        description="all | pending | active | completed — matches the UI filter tabs",
    ),
    skip:  int = Query(default=0, ge=0),
    limit: int = Query(default=6, ge=1, le=200),
    db: Session = Depends(get_db),
):
    f = LoanListFilter(
        search=search, loan_type=loan_type, status=loan_status,
        tab=tab, skip=skip, limit=limit,
    )
    items, total = list_loans(db, f)
    return PaginatedLoanResponse(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/employee/{employee_id}",
    response_model=List[LoanAdvanceResponse],
    summary="Get all loans/advances for a specific employee",
)
def loans_for_employee(employee_id: int, db: Session = Depends(get_db)):
    return get_loans_by_employee(db, employee_id)


# ─────────────────────────────────────────────────────────────────────────────
# Single record — view / edit / delete
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{loan_id}",
    response_model=LoanAdvanceDetailResponse,
    summary="Get a single loan with its full EMI / repayment schedule (view icon)",
)
def get_one_loan(loan_id: int, db: Session = Depends(get_db)):
    return get_loan(db, loan_id)


@router.patch(
    "/{loan_id}",
    response_model=LoanAdvanceResponse,
    summary="Edit a loan/advance record (edit icon)",
)
def edit_loan(loan_id: int, payload: LoanAdvanceUpdate, db: Session = Depends(get_db)):
    return update_loan(db, loan_id, payload)


@router.delete(
    "/{loan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a loan/advance record (delete icon — disallowed while ACTIVE)",
)
def remove_loan(loan_id: int, db: Session = Depends(get_db)):
    delete_loan(db, loan_id)


# ─────────────────────────────────────────────────────────────────────────────
# Approval workflow
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{loan_id}/approve",
    response_model=LoanAdvanceDetailResponse,
    summary="Approve a pending loan — generates the EMI schedule and activates it",
)
def approve(loan_id: int, payload: LoanApprovalRequest, db: Session = Depends(get_db)):
    """
    Accepts approved_amount, interest terms, tenure (months), and issue_date.
    Builds the complete repayment schedule (Reducing Balance / Flat Rate /
    Interest Free) and transitions the loan PENDING → ACTIVE.
    """
    return approve_loan(db, loan_id, payload)


@router.post(
    "/{loan_id}/reject",
    response_model=LoanAdvanceResponse,
    summary="Reject a pending loan request",
)
def reject(loan_id: int, payload: LoanRejectionRequest, db: Session = Depends(get_db)):
    return reject_loan(db, loan_id, payload)


# ─────────────────────────────────────────────────────────────────────────────
# Repayment / EMI tracking
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{loan_id}/repayments",
    response_model=LoanAdvanceDetailResponse,
    summary="Record an EMI repayment — updates Paid/Pending totals and next due date",
)
def add_repayment(loan_id: int, payload: RecordRepaymentRequest, db: Session = Depends(get_db)):
    """
    If installment_number is omitted, pays off the next outstanding installment
    (PENDING or OVERDUE) in sequence. Auto-closes the loan to COMPLETED once
    every installment is PAID.
    """
    return record_repayment(db, loan_id, payload)


@router.get(
    "/{loan_id}/repayments",
    response_model=List[LoanRepaymentResponse],
    summary="Get the full EMI schedule for a loan",
)
def get_repayments(loan_id: int, db: Session = Depends(get_db)):
    loan = get_loan(db, loan_id)
    return loan.repayments


@router.post(
    "/repayments/sync-overdue",
    summary="Mark past-due PENDING installments as OVERDUE (call from daily scheduler)",
)
def sync_overdue(db: Session = Depends(get_db)):
    count = mark_overdue_repayments(db)
    return {"overdue_count": count}


# ─────────────────────────────────────────────────────────────────────────────
# Export
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/export",
    summary="Export loan records matching current filters (Export button)",
)
def export_loans(
    search:    Optional[str] = None,
    loan_type: Optional[str] = None,
    loan_status: Optional[str] = Query(default=None, alias="status"),
    tab:       Optional[str] = "all",
    db: Session = Depends(get_db),
):
    """
    Returns the full manifest matching the active filters/tab.
    Actual XLSX/CSV file generation is delegated to a reporting / background task.
    """
    f = LoanListFilter(search=search, loan_type=loan_type, status=loan_status,
                       tab=tab, skip=0, limit=10_000)
    items, total = list_loans(db, f)
    return {
        "count": total,
        "items": [
            {
                "loan_code":      i.loan_code,
                "employee_name":  i.employee_name,
                "employee_code":  i.employee_code,
                "designation":    i.designation,
                "department":     i.department,
                "loan_type":      i.loan_type,
                "status":         i.status,
                "amount":         float(i.amount),
                "approved_amount": float(i.approved_amount) if i.approved_amount else None,
                "interest_rate":  float(i.interest_rate),
                "interest_method": i.interest_method,
                "emi_amount":     float(i.emi_amount) if i.emi_amount else None,
                "total_installments": i.total_installments,
                "paid_installments": i.paid_installments,
                "issue_date":     i.issue_date.isoformat() if i.issue_date else None,
                "end_date":       i.end_date.isoformat() if i.end_date else None,
                "total_paid":     float(i.total_paid),
                "total_pending":  float(i.total_pending),
            }
            for i in items
        ],
    }
