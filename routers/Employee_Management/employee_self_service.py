
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from core.database import get_db
from model.onboarding.employee import Employee
from model.Employee_Management.employee_master import EmployeeMaster
from model.Employee_Management.employee_document import EmployeeDocument
from model.Employee_Management.employee_lifecycle import EmployeeLifecycleEvent

router = APIRouter(prefix="/self-service", tags=["Employee Management"])


@router.get("/{employee_id}/profile", response_model=dict)
def get_self_profile(employee_id: int, db: Session = Depends(get_db)):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    master = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()

    profile = {
        "id": emp.id,
        "employee_code": emp.employee_code,
        "first_name": emp.first_name,
        "middle_name": emp.middle_name,
        "last_name": emp.last_name,
        "date_of_birth": emp.date_of_birth,
        "gender": emp.gender,
        "official_email": emp.official_email,
        "mobile_number": emp.mobile_number,
        "joining_date": emp.joining_date,
        "confirmation_date": emp.confirmation_date,
        "department": emp.department,
        "designation": emp.designation,
        "business_unit": emp.business_unit,
        "location": emp.location,
        "grade": emp.grade,
        "is_active": emp.is_active,
    }

    if master:
        profile["employment_type"] = master.employment_type
        profile["employment_status"] = master.employment_status
        profile["work_location"] = master.work_location
        profile["probation_end_date"] = master.probation_end_date
        profile["confirmed_date"] = master.confirmed_date
        profile["notice_period_days"] = master.notice_period_days
        profile["reporting_manager_id"] = master.reporting_manager_id

    return profile


@router.get("/{employee_id}/documents", response_model=list[dict])
def get_self_documents(employee_id: int, db: Session = Depends(get_db)):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    docs = db.execute(
        select(EmployeeDocument).where(EmployeeDocument.employee_id == employee_id)
    ).scalars().all()

    return [
        {
            "id": doc.id,
            "document_type": doc.document_type,
            "document_name": doc.document_name,
            "file_path": doc.file_path,
            "uploaded_at": doc.uploaded_at,
            "is_verified": doc.is_verified,
            "notes": doc.notes,
        }
        for doc in docs
    ]


@router.get("/{employee_id}/lifecycle", response_model=list[dict])
def get_self_lifecycle(employee_id: int, db: Session = Depends(get_db)):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    events = db.execute(
        select(EmployeeLifecycleEvent).where(
            EmployeeLifecycleEvent.employee_id == employee_id
        )
    ).scalars().all()

    return [
        {
            "id": evt.id,
            "event_type": evt.event_type,
            "event_date": evt.event_date,
            "from_value": evt.from_value,
            "to_value": evt.to_value,
            "remarks": evt.remarks,
            "created_at": evt.created_at,
        }
        for evt in events
    ]
