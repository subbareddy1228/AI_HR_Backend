
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException
from decimal import Decimal
from typing import Optional
from datetime import datetime

from model.Employee_Management.employee_master import EmployeeMaster
from model.onboarding.employee import Employee
from schema.Employee_Management.employee_master import (
    EmployeeMasterCreate,
    EmployeeMasterUpdate,
)


def get_stats(db: Session) -> dict:
 
    total = db.execute(
        select(func.count(Employee.id))
    ).scalar_one() or 0

    active = db.execute(
        select(func.count(Employee.id)).where(Employee.is_active == True)
    ).scalar_one() or 0

    departments = db.execute(
        select(func.count(func.distinct(Employee.department))).where(
            Employee.department != None
        )
    ).scalar_one() or 0

    avg_salary_raw = db.execute(
        select(func.avg(EmployeeMaster.salary)).where(
            EmployeeMaster.salary != None
        )
    ).scalar_one()

    avg_salary = float(round(avg_salary_raw, 2)) if avg_salary_raw else 0.0

    return {
        "total_employees": total,
        "active_employees": active,
        "departments": departments,
        "avg_salary": avg_salary,
    }


def list_employees(
    db: Session,
    search: Optional[str] = None,
    department: Optional[str] = None,
    employment_status: Optional[str] = None,
    employment_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 6,
) -> dict:

    stmt = (
        select(Employee, EmployeeMaster)
        .outerjoin(EmployeeMaster, EmployeeMaster.employee_id == Employee.id)
    )

    if search:
        s = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Employee.first_name).like(s) |
            func.lower(Employee.last_name).like(s) |
            func.lower(Employee.official_email).like(s) |
            func.lower(Employee.employee_code).like(s)
        )

 
    if department and department not in ("All Departments", "All", ""):
        stmt = stmt.where(Employee.department == department)

  
    if employment_status and employment_status not in ("All", ""):
        stmt = stmt.where(EmployeeMaster.employment_status == employment_status)

 
    if employment_type and employment_type not in ("All", ""):
        stmt = stmt.where(EmployeeMaster.employment_type == employment_type)

 
    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one() or 0

 
    offset = (page - 1) * page_size
    rows = db.execute(
        stmt.order_by(Employee.first_name).offset(offset).limit(page_size)
    ).all()

    employees = []
    for emp, master in rows:
        full_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip()
        employees.append({
          
            "id": emp.id,
            "employee_code": emp.employee_code,
            "name": full_name,
            "designation": emp.designation or "",
            
            "department": emp.department or "",
            "location": emp.location or "",
        
            "email": emp.official_email or "",
            "phone": emp.mobile_number or "",
          
            "salary": float(master.salary) if master and master.salary else None,
            "currency": master.currency if master else "USD",
            "employment_type": master.employment_type if master else "Full-Time",
          
            "employment_status": master.employment_status if master else "Active",
         
            "joining_date": str(emp.joining_date) if emp.joining_date else None,
            "grade": emp.grade or "",
            "work_location": master.work_location if master else "",
            "is_active": emp.is_active,
        })

    total_pages = (total + page_size - 1) // page_size
    showing_from = offset + 1 if total > 0 else 0
    showing_to = min(offset + page_size, total)

    return {
        "employees": employees,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "showing_from": showing_from,
        "showing_to": showing_to,
    }


def get_departments(db: Session) -> list:
    """
    Returns distinct department names for the 'All Departments' dropdown.
    """
    rows = db.execute(
        select(func.distinct(Employee.department))
        .where(Employee.department != None)
        .order_by(Employee.department)
    ).scalars().all()
    return rows



def create_master(db: Session, payload: EmployeeMasterCreate) -> EmployeeMaster:

    emp = db.execute(
        select(Employee).where(Employee.id == payload.employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(
            status_code=404,
            detail=f"Employee with id {payload.employee_id} not found. "
                   "The base employee record must exist first (created during onboarding)."
        )

    
    existing = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == payload.employee_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Master record already exists for employee_id {payload.employee_id}."
        )

    obj = EmployeeMaster(
        employee_id=payload.employee_id,
        salary=payload.salary,
        currency=payload.currency or "USD",
        employment_type=payload.employment_type,
        employment_status=payload.employment_status or "Active",
        probation_end_date=payload.probation_end_date,
        confirmed_date=payload.confirmed_date,
        reporting_manager_id=payload.reporting_manager_id,
        work_location=payload.work_location,
        notice_period_days=payload.notice_period_days or 30,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj



def get_master_by_employee_id(db: Session, employee_id: int) -> EmployeeMaster:
    """Returns raw EmployeeMaster record by employee_id. 404 if not found."""
    obj = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Employee master record not found.")
    return obj


def get_employee_detail(db: Session, employee_id: int) -> dict:

    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    master = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()

    full_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip()

    return {
        "id": emp.id,
        "employee_code": emp.employee_code,
        "name": full_name,
        "first_name": emp.first_name,
        "last_name": emp.last_name or "",
        "date_of_birth": str(emp.date_of_birth) if emp.date_of_birth else None,
        "gender": emp.gender.value if emp.gender else None,
        "official_email": emp.official_email or "",
        "mobile_number": emp.mobile_number or "",
        "designation": emp.designation or "",
        "department": emp.department or "",
        "grade": emp.grade or "",
        "location": emp.location or "",
        "business_unit": emp.business_unit or "",
        "cost_center": emp.cost_center or "",
        "joining_date": str(emp.joining_date) if emp.joining_date else None,
        "confirmation_date": str(emp.confirmation_date) if emp.confirmation_date else None,
        "is_active": emp.is_active,
        # EmployeeMaster fields
        "salary": float(master.salary) if master and master.salary else None,
        "currency": master.currency if master else "USD",
        "employment_type": master.employment_type if master else None,
        "employment_status": master.employment_status if master else None,
        "work_location": master.work_location if master else None,
        "probation_end_date": str(master.probation_end_date) if master and master.probation_end_date else None,
        "confirmed_date": str(master.confirmed_date) if master and master.confirmed_date else None,
        "reporting_manager_id": master.reporting_manager_id if master else None,
        "notice_period_days": master.notice_period_days if master else 30,
    }


def update_master(
    db: Session, employee_id: int, payload: EmployeeMasterUpdate
) -> EmployeeMaster:
 
    obj = get_master_by_employee_id(db, employee_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj

def soft_delete_master(db: Session, employee_id: int) -> dict:
  
    obj = get_master_by_employee_id(db, employee_id)
    obj.employment_status = "Terminated"
    obj.updated_at = datetime.utcnow()

    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if emp:
        emp.is_active = False

    db.commit()
    return {"message": f"Employee {employee_id} has been terminated and deactivated."}


def hard_delete_master(db: Session, employee_id: int) -> None:
   
    obj = get_master_by_employee_id(db, employee_id)
    db.delete(obj)
    db.commit()

def export_csv_data(
    db: Session,
    department: Optional[str] = None,
    employment_status: Optional[str] = None,
) -> list:

    stmt = (
        select(Employee, EmployeeMaster)
        .outerjoin(EmployeeMaster, EmployeeMaster.employee_id == Employee.id)
    )
    if department and department not in ("All Departments", "All", ""):
        stmt = stmt.where(Employee.department == department)
    if employment_status and employment_status not in ("All", ""):
        stmt = stmt.where(EmployeeMaster.employment_status == employment_status)

    rows = db.execute(stmt.order_by(Employee.first_name)).all()

    result = []
    for emp, master in rows:
        full_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip()
        result.append({
            "Employee Code": emp.employee_code,
            "Name": full_name,
            "Designation": emp.designation or "",
            "Department": emp.department or "",
            "Location": emp.location or "",
            "Email": emp.official_email or "",
            "Phone": emp.mobile_number or "",
            "Salary": str(master.salary) if master and master.salary else "",
            "Currency": master.currency if master else "USD",
            "Employment Type": master.employment_type if master else "",
            "Status": master.employment_status if master else "",
            "Joining Date": str(emp.joining_date) if emp.joining_date else "",
            "Grade": emp.grade or "",
        })
    return result
