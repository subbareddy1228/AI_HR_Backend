

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


@router.get("/stats")
def employee_stats(db: Session = Depends(get_db)):

    return get_stats(db)



@router.get("/departments")
def departments_list(db: Session = Depends(get_db)):

    depts = get_departments(db)
    return {"departments": depts, "total": len(depts)}


@router.get("/export/csv")
def export_csv(
    department: Optional[str] = Query(None),
    employment_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):

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

    return list_employees(
        db,
        search=search,
        department=department,
        employment_status=employment_status,
        employment_type=employment_type,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=EmployeeMasterResponse, status_code=201)
def add_employee(payload: EmployeeMasterCreate, db: Session = Depends(get_db)):

    return create_master(db, payload)

@router.get("/{employee_id}")
def view_employee(employee_id: int, db: Session = Depends(get_db)):

    return get_employee_detail(db, employee_id)


@router.put("/{employee_id}", response_model=EmployeeMasterResponse)
def edit_employee(
    employee_id: int,
    payload: EmployeeMasterUpdate,
    db: Session = Depends(get_db),
):
   
    return update_master(db, employee_id, payload)


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    hard: bool = Query(False,
        description="hard=false (default) → soft delete (sets Terminated + inactive). "
                    "hard=true → permanently removes master record."),
    db: Session = Depends(get_db),
):

    if hard:
        hard_delete_master(db, employee_id)
        return {"message": f"Employee master record {employee_id} permanently deleted."}
    else:
        return soft_delete_master(db, employee_id)
