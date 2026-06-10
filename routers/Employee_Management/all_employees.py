

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException
from typing import Optional

from core.database import get_db
from model.onboarding.employee import Employee
from schema.Employee_Management.all_employees_schema import (
    EmployeeCreateRequest,
    EmployeeUpdateRequest,
    EmployeeFullResponse,
    DeleteResponse,
    ActivationResponse,
)
from services.Employee_Management.all_employees_service import (
    list_all_employees,
    get_employee,
    create_employee,
    update_employee,
    delete_employee,
)

router = APIRouter(prefix="", tags=["Employee Management"])


@router.get("/", response_model=list[EmployeeFullResponse])
def list_employees_endpoint(
    is_active: Optional[bool] = Query(default=None),
    department: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    return list_all_employees(db, is_active=is_active, department=department, search=search)


@router.post("/", response_model=EmployeeFullResponse, status_code=201)
def create_employee_endpoint(
    payload: EmployeeCreateRequest,
    db: Session = Depends(get_db),
):
    return create_employee(db, payload.model_dump())


@router.get("/{employee_id}", response_model=EmployeeFullResponse)
def get_employee_endpoint(employee_id: int, db: Session = Depends(get_db)):
    return get_employee(db, employee_id)


@router.put("/{employee_id}", response_model=EmployeeFullResponse)
def update_employee_endpoint(
    employee_id: int,
    payload: EmployeeUpdateRequest,
    db: Session = Depends(get_db),
):
    return update_employee(db, employee_id, payload.model_dump(exclude_none=True))


@router.delete("/{employee_id}", response_model=DeleteResponse)
def delete_employee_endpoint(
    employee_id: int,
    hard: bool = Query(False),
    db: Session = Depends(get_db),
):
    return delete_employee(db, employee_id, hard=hard)


@router.patch("/{employee_id}/deactivate", response_model=ActivationResponse)
def deactivate_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.is_active = False
    db.commit()
    return {"id": emp.id, "is_active": False, "message": "Employee deactivated"}


@router.patch("/{employee_id}/activate", response_model=ActivationResponse)
def activate_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.is_active = True
    db.commit()
    return {"id": emp.id, "is_active": True, "message": "Employee activated"}