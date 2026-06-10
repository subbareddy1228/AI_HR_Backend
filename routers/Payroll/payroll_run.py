# routers/Payroll/payroll_run.py

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from core.dependencies import get_current_user
from schema.Payroll.payroll_run import (
    PayrollRunCreate, PayrollRunUpdate, PayrollRunResponse,
    PayrollRunDetailCreate, PayrollRunDetailResponse,
)
from services.Payroll.payroll_service import (
    create_payroll_run, list_payroll_runs, get_payroll_run,
    approve_payroll_run, mark_payroll_run_paid,
    add_employee_to_run, list_run_details,
)

router = APIRouter(prefix="/api/payroll/runs", tags=["Payroll Run"])


# ── Payroll Runs ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[PayrollRunResponse])
def list_runs(
    year: Optional[int] = Query(default=None, description="Filter by year"),
    run_status: Optional[str] = Query(default=None, description="Draft | Processing | Approved | Paid"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List payroll runs. Used in PayrollProcessingEngine.jsx run history table."""
    return list_payroll_runs(db, year=year, run_status=run_status)


@router.post("/", response_model=PayrollRunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    payload: PayrollRunCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new payroll run in Draft status."""
    return create_payroll_run(db, payload)


@router.get("/{run_id}", response_model=PayrollRunResponse)
def get_run(run_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get a single payroll run by ID."""
    return get_payroll_run(db, run_id)


@router.patch("/{run_id}/approve", response_model=PayrollRunResponse)
def approve_run(
    run_id: int,
    approved_by: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Approve a payroll run. Sets status to Approved."""
    return approve_payroll_run(db, run_id, approved_by=approved_by or current_user.username)


@router.patch("/{run_id}/mark-paid", response_model=PayrollRunResponse)
def mark_paid(run_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Mark a payroll run as Paid after bank transfer is complete."""
    return mark_payroll_run_paid(db, run_id)


# ── Payroll Run Details ───────────────────────────────────────────────────────

@router.get("/{run_id}/details", response_model=List[PayrollRunDetailResponse])
def get_run_details(run_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get all employee salary details for a specific payroll run."""
    return list_run_details(db, run_id)


@router.post("/{run_id}/details", response_model=PayrollRunDetailResponse, status_code=status.HTTP_201_CREATED)
def add_employee_detail(
    run_id: int,
    payload: PayrollRunDetailCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add an employee's salary detail to a payroll run. Updates run totals automatically."""
    return add_employee_to_run(db, run_id, payload)