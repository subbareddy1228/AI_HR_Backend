from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional

from core.database import get_db
from model.Payroll.payroll_run import PayrollRun, PayrollRunDetail
from schema.Payroll.payroll_run import (
    PayrollRunCreate, PayrollRunUpdate, PayrollRunResponse,
    PayrollRunDetailCreate, PayrollRunDetailResponse,
)

router = APIRouter(prefix="/runs", tags=["Payroll"])


@router.post("/", response_model=PayrollRunResponse, status_code=status.HTTP_201_CREATED)
def create_payroll_run(payload: PayrollRunCreate, db: Session = Depends(get_db)):
    obj = PayrollRun(**payload.model_dump())
    obj.status = "Draft"
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/", response_model=list[PayrollRunResponse])
def list_payroll_runs(
    year: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(PayrollRun)
    if year:
        stmt = stmt.where(PayrollRun.run_year == year)
    if status:
        stmt = stmt.where(PayrollRun.status == status)
    return db.execute(stmt).scalars().all()


@router.get("/{run_id}", response_model=dict)
def get_payroll_run(run_id: int, db: Session = Depends(get_db)):
    run = db.execute(select(PayrollRun).where(PayrollRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    details = db.execute(
        select(PayrollRunDetail).where(PayrollRunDetail.payroll_run_id == run_id)
    ).scalars().all()
    run_data = PayrollRunResponse.model_validate(run).model_dump()
    run_data["details"] = [PayrollRunDetailResponse.model_validate(d).model_dump() for d in details]
    return run_data


@router.patch("/{run_id}/approve", response_model=PayrollRunResponse)
def approve_payroll_run(run_id: int, approved_by: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    run = db.execute(select(PayrollRun).where(PayrollRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    run.status = "Approved"
    if approved_by:
        run.approved_by = approved_by
    db.commit()
    db.refresh(run)
    return run


@router.patch("/{run_id}/mark-paid", response_model=PayrollRunResponse)
def mark_payroll_run_paid(run_id: int, db: Session = Depends(get_db)):
    run = db.execute(select(PayrollRun).where(PayrollRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    run.status = "Paid"
    db.commit()
    db.refresh(run)
    return run


@router.post("/{run_id}/add-employee", response_model=PayrollRunDetailResponse, status_code=status.HTTP_201_CREATED)
def add_employee_to_run(run_id: int, payload: PayrollRunDetailCreate, db: Session = Depends(get_db)):
    run = db.execute(select(PayrollRun).where(PayrollRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    data = payload.model_dump()
    data["payroll_run_id"] = run_id
    obj = PayrollRunDetail(**data)
    db.add(obj)
    # Update run totals
    run.total_employees = (run.total_employees or 0) + 1
    run.total_gross = (run.total_gross or 0) + float(payload.gross_salary)
    run.total_deductions = (run.total_deductions or 0) + float(payload.total_deductions)
    run.total_net_pay = (run.total_net_pay or 0) + float(payload.net_pay)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{run_id}/details", response_model=list[PayrollRunDetailResponse])
def list_run_details(run_id: int, db: Session = Depends(get_db)):
    run = db.execute(select(PayrollRun).where(PayrollRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    return db.execute(
        select(PayrollRunDetail).where(PayrollRunDetail.payroll_run_id == run_id)
    ).scalars().all()
