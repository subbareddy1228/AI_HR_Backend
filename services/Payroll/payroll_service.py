# services/Payroll/payroll_service.py
# Service layer for PayrollRun and PayrollRunDetail

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
from fastapi import HTTPException, status

from model.Payroll.payroll_run import PayrollRun, PayrollRunDetail
from schema.Payroll.payroll_run import (
    PayrollRunCreate, PayrollRunUpdate,
    PayrollRunDetailCreate,
)


# ── Payroll Run ───────────────────────────────────────────────────────────────

def create_payroll_run(db: Session, payload: PayrollRunCreate) -> PayrollRun:
    """Create a new payroll run with Draft status."""
    obj = PayrollRun(**payload.model_dump())
    obj.status = "Draft"
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_payroll_runs(
    db: Session,
    year: Optional[int] = None,
    run_status: Optional[str] = None,
) -> List[PayrollRun]:
    """List payroll runs with optional year and status filters."""
    stmt = select(PayrollRun)
    if year:
        stmt = stmt.where(PayrollRun.run_year == year)
    if run_status:
        stmt = stmt.where(PayrollRun.status == run_status)
    return db.execute(stmt).scalars().all()


def get_payroll_run(db: Session, run_id: int) -> PayrollRun:
    """Fetch a single payroll run. Raises 404 if not found."""
    obj = db.execute(
        select(PayrollRun).where(PayrollRun.id == run_id)
    ).scalar_one_or_none()

    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll run not found")
    return obj


def approve_payroll_run(db: Session, run_id: int, approved_by: Optional[str] = None) -> PayrollRun:
    """Set payroll run status to Approved."""
    obj = get_payroll_run(db, run_id)
    obj.status = "Approved"
    if approved_by:
        obj.approved_by = approved_by
    db.commit()
    db.refresh(obj)
    return obj


def mark_payroll_run_paid(db: Session, run_id: int) -> PayrollRun:
    """Set payroll run status to Paid."""
    obj = get_payroll_run(db, run_id)
    obj.status = "Paid"
    db.commit()
    db.refresh(obj)
    return obj


# ── Payroll Run Detail ────────────────────────────────────────────────────────

def add_employee_to_run(db: Session, run_id: int, payload: PayrollRunDetailCreate) -> PayrollRunDetail:
    """Add an employee entry to a payroll run and update run totals."""
    run = get_payroll_run(db, run_id)

    data = payload.model_dump()
    data["payroll_run_id"] = run_id
    detail = PayrollRunDetail(**data)
    db.add(detail)

    # Update aggregate totals on the run
    run.total_employees = (run.total_employees or 0) + 1
    run.total_gross = (run.total_gross or 0) + float(payload.gross_salary)
    run.total_deductions = (run.total_deductions or 0) + float(payload.total_deductions)
    run.total_net_pay = (run.total_net_pay or 0) + float(payload.net_pay)

    db.commit()
    db.refresh(detail)
    return detail


def list_run_details(db: Session, run_id: int) -> List[PayrollRunDetail]:
    """List all employee details for a given payroll run."""
    get_payroll_run(db, run_id)  # validates run exists
    return db.execute(
        select(PayrollRunDetail).where(PayrollRunDetail.payroll_run_id == run_id)
    ).scalars().all()
