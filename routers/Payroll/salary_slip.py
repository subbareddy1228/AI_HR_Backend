# FILE 12 of 18 | routers/Payroll/salary_slip.py
# Router: Salary Slips — prefix: /salary-slips  (mounted under /api/payroll in main.py)
# Endpoints:
#   POST   /salary-slips/                          — create slip
#   GET    /salary-slips/                          — list all (filter: employee_id, slip_month, slip_year)
#   GET    /salary-slips/employee/{employee_id}    — all slips for employee
#   GET    /salary-slips/{slip_id}                 — get one
#   PATCH  /salary-slips/{slip_id}/publish         — set is_published=True
#   DELETE /salary-slips/{slip_id}                 — delete

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional

from core.database import get_db
from model.Payroll.salary_slip import SalarySlip
from schema.Payroll.salary_slip import SalarySlipCreate, SalarySlipUpdate, SalarySlipResponse

router = APIRouter(prefix="/salary-slips", tags=["Payroll"])


@router.post("/", response_model=SalarySlipResponse, status_code=status.HTTP_201_CREATED)
def create_salary_slip(payload: SalarySlipCreate, db: Session = Depends(get_db)):
    obj = SalarySlip(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/", response_model=list[SalarySlipResponse])
def list_salary_slips(
    employee_id: Optional[int] = Query(default=None),
    slip_month: Optional[int] = Query(default=None),
    slip_year: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(SalarySlip)
    if employee_id:
        stmt = stmt.where(SalarySlip.employee_id == employee_id)
    if slip_month:
        stmt = stmt.where(SalarySlip.slip_month == slip_month)
    if slip_year:
        stmt = stmt.where(SalarySlip.slip_year == slip_year)
    return db.execute(stmt).scalars().all()


@router.get("/employee/{employee_id}", response_model=list[SalarySlipResponse])
def get_slips_by_employee(employee_id: int, db: Session = Depends(get_db)):
    return db.execute(
        select(SalarySlip)
        .where(SalarySlip.employee_id == employee_id)
        .order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())
    ).scalars().all()


@router.get("/{slip_id}", response_model=SalarySlipResponse)
def get_salary_slip(slip_id: int, db: Session = Depends(get_db)):
    obj = db.execute(select(SalarySlip).where(SalarySlip.id == slip_id)).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Salary slip not found")
    return obj


@router.patch("/{slip_id}/publish", response_model=SalarySlipResponse)
def publish_salary_slip(slip_id: int, db: Session = Depends(get_db)):
    obj = db.execute(select(SalarySlip).where(SalarySlip.id == slip_id)).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Salary slip not found")
    obj.is_published = True
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{slip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salary_slip(slip_id: int, db: Session = Depends(get_db)):
    obj = db.execute(select(SalarySlip).where(SalarySlip.id == slip_id)).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Salary slip not found")
    db.delete(obj)
    db.commit()
