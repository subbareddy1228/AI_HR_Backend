# services/Employee_Management/employee_master_service.py

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


# ════════════════════════════════════════════════════════════════════
# STAT CARDS
# ════════════════════════════════════════════════════════════════════

def get_stats(db: Session) -> dict:
    """
    Powers the 4 stat cards at the top of the screenshot.
      Total Employees  → count all employees
      Active Employees → count where is_active=True
      Departments      → count distinct department values
      Avg. Salary      → average salary from employee_master
    """
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


# ════════════════════════════════════════════════════════════════════
# EMPLOYEE TABLE — search + filter + paginate
# ════════════════════════════════════════════════════════════════════

def list_employees(
    db: Session,
    search: Optional[str] = None,
    department: Optional[str] = None,
    employment_status: Optional[str] = None,
    employment_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 6,
) -> dict:
    """
    Powers the Employee Records table.

    Screenshot columns mapped:
      EMPLOYEE   → name, employee_code, designation
      DEPARTMENT → department, location
      CONTACT    → official_email, mobile_number
      SALARY     → salary, currency, employment_type badge
      STATUS     → employment_status badge
      ACTIONS    → id returned for View/Delete buttons

    Pagination → "Showing 1 to 6 of 8 employees" + page buttons
    """
    stmt = (
        select(Employee, EmployeeMaster)
        .outerjoin(EmployeeMaster, EmployeeMaster.employee_id == Employee.id)
    )

    # Search: name, email, employee_code
    if search:
        s = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Employee.first_name).like(s) |
            func.lower(Employee.last_name).like(s) |
            func.lower(Employee.official_email).like(s) |
            func.lower(Employee.employee_code).like(s)
        )

    # Department filter (dropdown in screenshot)
    if department and department not in ("All Departments", "All", ""):
        stmt = stmt.where(Employee.department == department)

    # Status filter (All dropdown in screenshot)
    if employment_status and employment_status not in ("All", ""):
        stmt = stmt.where(EmployeeMaster.employment_status == employment_status)

    # Employment type filter
    if employment_type and employment_type not in ("All", ""):
        stmt = stmt.where(EmployeeMaster.employment_type == employment_type)

    # Total count before pagination
    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one() or 0

    # Pagination
    offset = (page - 1) * page_size
    rows = db.execute(
        stmt.order_by(Employee.first_name).offset(offset).limit(page_size)
    ).all()

    employees = []
    for emp, master in rows:
        full_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip()
        employees.append({
            # EMPLOYEE column
            "id": emp.id,
            "employee_code": emp.employee_code,
            "name": full_name,
            "designation": emp.designation or "",
            # DEPARTMENT column
            "department": emp.department or "",
            "location": emp.location or "",
            # CONTACT column
            "email": emp.official_email or "",
            "phone": emp.mobile_number or "",
            # SALARY column
            "salary": float(master.salary) if master and master.salary else None,
            "currency": master.currency if master else "USD",
            "employment_type": master.employment_type if master else "Full-Time",
            # STATUS column
            "employment_status": master.employment_status if master else "Active",
            # For detail modal
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


# ════════════════════════════════════════════════════════════════════
# DEPARTMENT DROPDOWN
# ════════════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════════════
# CREATE — Add Employee button
# ════════════════════════════════════════════════════════════════════

def create_master(db: Session, payload: EmployeeMasterCreate) -> EmployeeMaster:
    """
    Creates EmployeeMaster record for an existing employee.
    Called when HR clicks 'Add Employee' and fills the form.

    Validates:
    - Employee must exist in employees table
    - No duplicate master record for same employee_id
    """
    # Check employee exists
    emp = db.execute(
        select(Employee).where(Employee.id == payload.employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(
            status_code=404,
            detail=f"Employee with id {payload.employee_id} not found. "
                   "The base employee record must exist first (created during onboarding)."
        )

    # Check no duplicate
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


# ════════════════════════════════════════════════════════════════════
# GET — single master record
# ════════════════════════════════════════════════════════════════════

def get_master_by_employee_id(db: Session, employee_id: int) -> EmployeeMaster:
    """Returns raw EmployeeMaster record by employee_id. 404 if not found."""
    obj = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Employee master record not found.")
    return obj


def get_employee_detail(db: Session, employee_id: int) -> dict:
    """
    Returns combined Employee + EmployeeMaster data for the View button detail modal.
    All fields shown in the screenshot's detail view.
    """
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
        # Employee table fields
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


# ════════════════════════════════════════════════════════════════════
# UPDATE — edit salary, status, employment type
# ════════════════════════════════════════════════════════════════════

def update_master(
    db: Session, employee_id: int, payload: EmployeeMasterUpdate
) -> EmployeeMaster:
    """
    Partial update of EmployeeMaster record.
    Only fields sent in the request body are changed.

    Common use cases:
    - Change employment_status: Active → On Leave (STATUS badge in screenshot)
    - Update salary (SALARY column in screenshot)
    - Change employment_type: Full-Time → Contract (badge under salary)
    """
    obj = get_master_by_employee_id(db, employee_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


# ════════════════════════════════════════════════════════════════════
# DELETE
# ════════════════════════════════════════════════════════════════════

def soft_delete_master(db: Session, employee_id: int) -> dict:
    """
    Soft delete — sets employment_status='Terminated' and Employee.is_active=False.
    Triggered by trash icon in ACTIONS column.
    Recommended over hard delete to preserve history.
    """
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
    """
    Hard delete — permanently removes the EmployeeMaster record.
    The base Employee record in employees table is NOT deleted.
    """
    obj = get_master_by_employee_id(db, employee_id)
    db.delete(obj)
    db.commit()


# ════════════════════════════════════════════════════════════════════
# EXPORT CSV DATA
# ════════════════════════════════════════════════════════════════════

def export_csv_data(
    db: Session,
    department: Optional[str] = None,
    employment_status: Optional[str] = None,
) -> list:
    """
    Returns all employee rows for CSV export.
    Applies the same filters as the table.
    Triggered by 'Export CSV' button in screenshot.
    """
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
