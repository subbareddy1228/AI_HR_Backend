# FILE 7 of 12 | routers/Employee_Management/employee_master.py
# Router: EmployeeMaster CRUD — prefix: /master
# Endpoints: POST /  GET /  GET /{employee_id}  PUT /{employee_id}  DELETE /{employee_id}

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional

from core.database import get_db
from model.Employee_Management.employee_master import EmployeeMaster
from schema.Employee_Management.employee_master import (
    EmployeeMasterCreate,
    EmployeeMasterUpdate,
    EmployeeMasterResponse,
)

router = APIRouter(prefix="/master", tags=["Employee Management"])


@router.post("/", response_model=EmployeeMasterResponse, status_code=status.HTTP_201_CREATED)
def create_employee_master(payload: EmployeeMasterCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == payload.employee_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Master record for employee_id {payload.employee_id} already exists",
        )
    obj = EmployeeMaster(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/", response_model=list[EmployeeMasterResponse])
def list_employee_masters(
    department: Optional[str] = Query(default=None),
    employment_status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(EmployeeMaster)
    if employment_status:
        stmt = stmt.where(EmployeeMaster.employment_status == employment_status)
    # department filter would require a join to Employee; filter by work_location as proxy if needed
    if department:
        stmt = stmt.where(EmployeeMaster.work_location == department)
    return db.execute(stmt).scalars().all()


@router.get("/{employee_id}", response_model=EmployeeMasterResponse)
def get_employee_master(employee_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Employee master record not found")
    return obj


@router.put("/{employee_id}", response_model=EmployeeMasterResponse)
def update_employee_master(
    employee_id: int, payload: EmployeeMasterUpdate, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Employee master record not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee_master(employee_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Employee master record not found")
    db.delete(obj)
    db.commit()
