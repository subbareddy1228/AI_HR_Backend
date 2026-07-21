from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException
from typing import Optional

from core.database import get_db
from core.dependencies import get_current_tenant_id
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
    tenant_id: Optional[int] = Depends(get_current_tenant_id),
):
    return list_all_employees(
        db,
        tenant_id=tenant_id,
        is_active=is_active,
        department=department,
        search=search,
    )


@router.post("/", response_model=EmployeeFullResponse, status_code=201)
def create_employee_endpoint(
    payload: EmployeeCreateRequest,
    db: Session = Depends(get_db),
    tenant_id: Optional[int] = Depends(get_current_tenant_id),
):
    if tenant_id is None:

        raise HTTPException(
            status_code=400,
            detail="Employees must be created from a company (recruiter) account, not a super_admin account.",
        )
    return create_employee(db, payload.model_dump(), tenant_id=tenant_id)


@router.get("/{employee_id}", response_model=EmployeeFullResponse)
def get_employee_endpoint(
    employee_id: int,
    db: Session = Depends(get_db),
    tenant_id: Optional[int] = Depends(get_current_tenant_id),
):
    return get_employee(db, employee_id, tenant_id=tenant_id)


@router.put("/{employee_id}", response_model=EmployeeFullResponse)
def update_employee_endpoint(
    employee_id: int,
    payload: EmployeeUpdateRequest,
    db: Session = Depends(get_db),
    tenant_id: Optional[int] = Depends(get_current_tenant_id),
):
    return update_employee(
        db,
        employee_id,
        payload.model_dump(exclude_none=True),
        tenant_id=tenant_id,
    )


@router.delete("/{employee_id}", response_model=DeleteResponse)
def delete_employee_endpoint(
    employee_id: int,
    hard: bool = Query(False),
    db: Session = Depends(get_db),
    tenant_id: Optional[int] = Depends(get_current_tenant_id),
):
    return delete_employee(db, employee_id, tenant_id=tenant_id, hard=hard)


@router.patch("/{employee_id}/deactivate", response_model=ActivationResponse)
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    tenant_id: Optional[int] = Depends(get_current_tenant_id),
):
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if tenant_id is not None and emp.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.is_active = False
    db.commit()
    return {"id": emp.id, "is_active": False, "message": "Employee deactivated"}


@router.patch("/{employee_id}/activate", response_model=ActivationResponse)
def activate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    tenant_id: Optional[int] = Depends(get_current_tenant_id),
):
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if tenant_id is not None and emp.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.is_active = True
    db.commit()
    return {"id": emp.id, "is_active": True, "message": "Employee activated"}