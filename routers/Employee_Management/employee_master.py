# routers/Employee_Management/employee_master.py

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import csv
import io

from core.database import get_db
from schema.Employee_Management.employee_master import (
    EmployeeMasterCreate,
    EmployeeMasterUpdate,
    EmployeeMasterResponse,
)
from services.Employee_Management.employee_master_service import (
    get_stats,
    list_employees,
    get_departments,
    create_master,
    get_master_by_employee_id,
    get_employee_detail,
    update_master,
    soft_delete_master,
    hard_delete_master,
    export_csv_data,
)

router = APIRouter(prefix="/master", tags=["Employee Management"])


# ════════════════════════════════════════════════════════════════════
# STAT CARDS
# ════════════════════════════════════════════════════════════════════

@router.get("/stats")
def employee_stats(db: Session = Depends(get_db)):
    """
    Powers the 4 stat cards at the top of the Employee Master Data page.

    Returns:
      total_employees   → "Total Employees — 8"
      active_employees  → "Active Employees — 6"
      departments       → "Departments — 7"
      avg_salary        → "Avg. Salary — $70,750"
    """
    return get_stats(db)


# ════════════════════════════════════════════════════════════════════
# DEPARTMENT DROPDOWN
# ════════════════════════════════════════════════════════════════════

@router.get("/departments")
def departments_list(db: Session = Depends(get_db)):
    """
    Returns all distinct department names.
    Populates the 'All Departments' dropdown filter in the screenshot.
    """
    depts = get_departments(db)
    return {"departments": depts, "total": len(depts)}


# ════════════════════════════════════════════════════════════════════
# EXPORT CSV
# ════════════════════════════════════════════════════════════════════

@router.get("/export/csv")
def export_csv(
    department: Optional[str] = Query(None),
    employment_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Downloads the employee list as a CSV file.
    Triggered by the 'Export CSV' button in the screenshot.

    Same filters as the table:
      ?department=HR&employment_status=Active

    CSV columns match the screenshot table:
    Employee Code, Name, Designation, Department, Location,
    Email, Phone, Salary, Employment Type, Status, Joining Date, Grade
    """
    data = export_csv_data(db, department=department, employment_status=employment_status)

    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    else:
        output.write("No records found.\n")

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employee_master_data.csv"},
    )


# ════════════════════════════════════════════════════════════════════
# EMPLOYEE TABLE — main list with search + filter + pagination
# ════════════════════════════════════════════════════════════════════

@router.get("/")
def list_employees_endpoint(
    search: Optional[str] = Query(None,
        description="Search bar — matches name, email, employee code"),
    department: Optional[str] = Query(None,
        description="All Departments dropdown — e.g. HR, Engineering, Sales"),
    employment_status: Optional[str] = Query(None,
        description="All dropdown — Active | Inactive | On Leave | Resigned | Terminated"),
    employment_type: Optional[str] = Query(None,
        description="Full-Time | Part-Time | Contract | Intern"),
    page: int = Query(1, ge=1,
        description="Page number — used by Previous/1/2/Next buttons"),
    page_size: int = Query(6, ge=1, le=100,
        description="Rows per page — default 6 as shown in screenshot"),
    db: Session = Depends(get_db),
):
    """
    Powers the Employee Records table.

    Each row in screenshot:
      EMPLOYEE   → name + employee_code + designation
      DEPARTMENT → department + location
      CONTACT    → email + phone
      SALARY     → salary amount + employment_type badge (Full-time/Contract)
      STATUS     → employment_status badge (Active/On Leave)
      ACTIONS    → id for View/Delete buttons

    Pagination footer: "Showing 1 to 6 of 8 employees"
    """
    return list_employees(
        db,
        search=search,
        department=department,
        employment_status=employment_status,
        employment_type=employment_type,
        page=page,
        page_size=page_size,
    )


# ════════════════════════════════════════════════════════════════════
# ADD EMPLOYEE
# ════════════════════════════════════════════════════════════════════

@router.post("/", response_model=EmployeeMasterResponse, status_code=201)
def add_employee(payload: EmployeeMasterCreate, db: Session = Depends(get_db)):
    """
    Creates an EmployeeMaster record.
    Triggered by the green 'Add Employee' button in the screenshot.

    The base Employee record must already exist (created during onboarding by D11).
    This adds the HR employment data on top of it.

    Required:
      employee_id      → must exist in employees table
      employment_type  → Full-Time | Part-Time | Contract | Intern

    Optional:
      salary, currency, employment_status, work_location,
      probation_end_date, reporting_manager_id, notice_period_days
    """
    return create_master(db, payload)


# ════════════════════════════════════════════════════════════════════
# VIEW EMPLOYEE DETAIL (View button)
# ════════════════════════════════════════════════════════════════════

@router.get("/{employee_id}")
def view_employee(employee_id: int, db: Session = Depends(get_db)):
    """
    Returns full detail for one employee.
    Triggered by the 'View' (eye) button in the ACTIONS column.

    Returns combined data from:
      - employees table (name, email, phone, dept, joining_date etc.)
      - employee_master table (salary, employment_type, status, probation etc.)
    """
    return get_employee_detail(db, employee_id)


# ════════════════════════════════════════════════════════════════════
# UPDATE EMPLOYEE
# ════════════════════════════════════════════════════════════════════

@router.put("/{employee_id}", response_model=EmployeeMasterResponse)
def edit_employee(
    employee_id: int,
    payload: EmployeeMasterUpdate,
    db: Session = Depends(get_db),
):
    """
    Updates employee master data. Only fields you send are changed.

    Common uses (from screenshot):
      Change STATUS badge:
        { "employment_status": "On Leave" }

      Update SALARY column:
        { "salary": 75000, "currency": "USD" }

      Change employment_type badge:
        { "employment_type": "Contract" }

      Update multiple fields:
        { "salary": 80000, "employment_status": "Active", "work_location": "New York" }
    """
    return update_master(db, employee_id, payload)


# ════════════════════════════════════════════════════════════════════
# DELETE EMPLOYEE (trash icon)
# ════════════════════════════════════════════════════════════════════

@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    hard: bool = Query(False,
        description="hard=false (default) → soft delete (sets Terminated + inactive). "
                    "hard=true → permanently removes master record."),
    db: Session = Depends(get_db),
):
    """
    Triggered by the trash/delete icon in the ACTIONS column.

    Default (hard=false) → SOFT DELETE:
      Sets employment_status='Terminated' and Employee.is_active=False.
      Employee disappears from the active list but data is preserved.
      RECOMMENDED — preserves audit history.

    hard=true → HARD DELETE:
      Permanently removes the EmployeeMaster record.
      Base Employee record in employees table remains.
      Use only if you need to fully wipe the record.
    """
    if hard:
        hard_delete_master(db, employee_id)
        return {"message": f"Employee master record {employee_id} permanently deleted."}
    else:
        return soft_delete_master(db, employee_id)
