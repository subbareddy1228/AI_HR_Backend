from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, distinct
from core.database import get_db
from typing import Optional
from datetime import date

try:
    from model.onboarding.employee import Employee
except ImportError:
    Employee = None

try:
    from model.HR_Operations.exit_management import ExitManagement
except ImportError:
    ExitManagement = None

router = APIRouter(prefix="/employees", tags=["Reports"])


@router.get("/headcount")
def headcount(
    department: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if Employee is None:
        return {"error": "Employee model not available", "data": {}}

    query = select(Employee)
    if department:
        query = query.where(Employee.department == department)
    if location:
        query = query.where(Employee.location == location)

    employees = db.execute(query).scalars().all()

    total = len(employees)
    active = sum(1 for e in employees if e.is_active)
    inactive = total - active

    dept_breakdown: dict = {}
    gender_breakdown: dict = {}

    for e in employees:
        dept = e.department or "Unknown"
        dept_breakdown[dept] = dept_breakdown.get(dept, 0) + 1

        gender = e.gender or "Unknown"
        gender_breakdown[gender] = gender_breakdown.get(gender, 0) + 1

    return {
        "total_employees": total,
        "active_count": active,
        "inactive_count": inactive,
        "by_department": dept_breakdown,
        "by_gender": gender_breakdown,
    }


@router.get("/new-joiners")
def new_joiners(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    if Employee is None:
        return {"data": [], "count": 0}

    query = select(Employee)
    if start_date:
        query = query.where(Employee.joining_date >= start_date)
    if end_date:
        query = query.where(Employee.joining_date <= end_date)

    employees = db.execute(query).scalars().all()
    data = [
        {
            "id": e.id,
            "employee_code": e.employee_code,
            "first_name": e.first_name,
            "last_name": e.last_name,
            "department": e.department,
            "designation": e.designation,
            "joining_date": str(e.joining_date) if e.joining_date else None,
        }
        for e in employees
    ]
    return {"data": data, "count": len(data)}


@router.get("/attrition")
def attrition(
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if ExitManagement is None or Employee is None:
        return {
            "attrition_count": 0,
            "attrition_rate": 0.0,
            "by_exit_type": {},
            "message": "Exit management model not available",
        }

    exit_query = select(ExitManagement)
    if year:
        exit_query = exit_query.where(
            func.extract("year", ExitManagement.last_working_date) == year
        )

    exits = db.execute(exit_query).scalars().all()
    total_employees_result = db.execute(
        select(func.count()).select_from(Employee).where(Employee.is_active == True)
    ).scalar()
    total_employees = total_employees_result or 1  # avoid division by zero

    exit_type_breakdown: dict = {}
    for ex in exits:
        et = ex.exit_type or "Unknown"
        exit_type_breakdown[et] = exit_type_breakdown.get(et, 0) + 1

    attrition_count = len(exits)
    attrition_rate = round((attrition_count / total_employees) * 100, 2)

    return {
        "attrition_count": attrition_count,
        "attrition_rate": attrition_rate,
        "total_active_employees": total_employees,
        "by_exit_type": exit_type_breakdown,
    }


@router.get("/department-distribution")
def department_distribution(db: Session = Depends(get_db)):
    if Employee is None:
        return {"data": []}

    rows = db.execute(
        select(Employee.department, func.count(Employee.id).label("count"))
        .group_by(Employee.department)
    ).all()

    data = [{"department": row.department or "Unknown", "count": row.count} for row in rows]
    return {"data": data}
