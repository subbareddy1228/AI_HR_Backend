# services/Employee_Management/employee_master_service.py
# Service layer for EmployeeMaster CRUD operations

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
from fastapi import HTTPException, status

from model.Employee_Management.employee_master import EmployeeMaster
from schema.Employee_Management.employee_master import EmployeeMasterCreate, EmployeeMasterUpdate


def create_employee_master(db: Session, payload: EmployeeMasterCreate) -> EmployeeMaster:
    """Create a new employee master record. Raises 409 if already exists."""
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


def get_employee_master(db: Session, employee_id: int) -> EmployeeMaster:
    """Fetch a single master record by employee_id. Raises 404 if not found."""
    obj = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()

    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee master record not found")
    return obj


def list_employee_masters(
    db: Session,
    department: Optional[str] = None,
    employment_status: Optional[str] = None,
) -> List[EmployeeMaster]:
    """List all master records with optional filters."""
    stmt = select(EmployeeMaster)
    if employment_status:
        stmt = stmt.where(EmployeeMaster.employment_status == employment_status)
    if department:
        stmt = stmt.where(EmployeeMaster.work_location == department)
    return db.execute(stmt).scalars().all()


def update_employee_master(db: Session, employee_id: int, payload: EmployeeMasterUpdate) -> EmployeeMaster:
    """Update an existing master record. Raises 404 if not found."""
    obj = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()

    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee master record not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)

    db.commit()
    db.refresh(obj)
    return obj


def delete_employee_master(db: Session, employee_id: int) -> None:
    """Delete a master record. Raises 404 if not found."""
    obj = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()

    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee master record not found")

    db.delete(obj)
    db.commit()
