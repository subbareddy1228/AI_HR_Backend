# FILE 8 of 12 | routers/Employee_Management/all_employees.py
# Router: All Employees — prefix: (empty, mounted at /api/employees)
# Endpoints: GET /  GET /{employee_id}  PATCH /{employee_id}/deactivate  PATCH /{employee_id}/activate

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from typing import Optional

from core.database import get_db
from model.onboarding.employee import Employee

router = APIRouter(prefix="", tags=["Employee Management"])


@router.get("/", response_model=list[dict])
def list_all_employees(
    is_active: Optional[bool] = Query(default=None),
    department: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Search by name or email"),
    db: Session = Depends(get_db),
):
    stmt = select(Employee)

    if is_active is not None:
        stmt = stmt.where(Employee.is_active == is_active)

    if department:
        stmt = stmt.where(Employee.department == department)

    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                Employee.first_name.ilike(search_term),
                Employee.last_name.ilike(search_term),
                Employee.official_email.ilike(search_term),
            )
        )

    employees = db.execute(stmt).scalars().all()
    result = []
    for emp in employees:
        result.append({
            "id": emp.id,
            "employee_code": emp.employee_code,
            "first_name": emp.first_name,
            "middle_name": emp.middle_name,
            "last_name": emp.last_name,
            "official_email": emp.official_email,
            "mobile_number": emp.mobile_number,
            "department": emp.department,
            "designation": emp.designation,
            "business_unit": emp.business_unit,
            "location": emp.location,
            "joining_date": emp.joining_date,
            "is_active": emp.is_active,
        })
    return result


@router.get("/{employee_id}", response_model=dict)
def get_employee_detail(employee_id: int, db: Session = Depends(get_db)):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    return {
        "id": emp.id,
        "onboarding_id": emp.onboarding_id,
        "employee_code": emp.employee_code,
        "biometric_code": emp.biometric_code,
        "first_name": emp.first_name,
        "middle_name": emp.middle_name,
        "last_name": emp.last_name,
        "date_of_birth": emp.date_of_birth,
        "gender": emp.gender,
        "official_email": emp.official_email,
        "mobile_number": emp.mobile_number,
        "joining_date": emp.joining_date,
        "confirmation_date": emp.confirmation_date,
        "business_unit": emp.business_unit,
        "location": emp.location,
        "cost_center": emp.cost_center,
        "department": emp.department,
        "designation": emp.designation,
        "grade": emp.grade,
        "shift_policy": emp.shift_policy,
        "week_off_policy": emp.week_off_policy,
        "overtime_policy": emp.overtime_policy,
        "send_mobile_login": emp.send_mobile_login,
        "send_web_login": emp.send_web_login,
        "is_active": emp.is_active,
    }


@router.patch("/{employee_id}/deactivate", response_model=dict)
def deactivate_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.is_active = False
    db.commit()
    db.refresh(emp)
    return {"id": emp.id, "is_active": emp.is_active, "message": "Employee deactivated successfully"}


@router.patch("/{employee_id}/activate", response_model=dict)
def activate_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.is_active = True
    db.commit()
    db.refresh(emp)
    return {"id": emp.id, "is_active": emp.is_active, "message": "Employee activated successfully"}
