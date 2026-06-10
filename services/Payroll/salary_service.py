# services/Payroll/salary_service.py
# Service layer for SalaryStructure and EmployeeSalaryMapping
# (No changes from original — included here for completeness)
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
from fastapi import HTTPException, status

from model.Payroll.salary_structure import SalaryStructure, EmployeeSalaryMapping
from schema.Payroll.salary_structure import (
    SalaryStructureCreate, SalaryStructureUpdate,
    EmployeeSalaryMappingCreate,
)


# ── Salary Structure ─────────────────────────────────────────────────────────

def create_salary_structure(db: Session, payload: SalaryStructureCreate) -> SalaryStructure:
    """Create a new salary structure. Raises 409 if name already exists."""
    existing = db.execute(
        select(SalaryStructure).where(SalaryStructure.structure_name == payload.structure_name)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Salary structure '{payload.structure_name}' already exists",
        )

    obj = SalaryStructure(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_salary_structures(db: Session) -> List[SalaryStructure]:
    """Return all salary structures."""
    return db.execute(select(SalaryStructure)).scalars().all()


def get_salary_structure(db: Session, structure_id: int) -> SalaryStructure:
    """Fetch a single salary structure by ID. Raises 404 if not found."""
    obj = db.execute(
        select(SalaryStructure).where(SalaryStructure.id == structure_id)
    ).scalar_one_or_none()

    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary structure not found",
        )
    return obj


def update_salary_structure(
    db: Session, structure_id: int, payload: SalaryStructureUpdate
) -> SalaryStructure:
    """Update a salary structure. Raises 404 if not found."""
    obj = get_salary_structure(db, structure_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_salary_structure(db: Session, structure_id: int) -> None:
    """Delete a salary structure. Raises 404 if not found."""
    obj = get_salary_structure(db, structure_id)
    db.delete(obj)
    db.commit()


# ── Employee Salary Mapping ───────────────────────────────────────────────────

def assign_employee_to_structure(
    db: Session, payload: EmployeeSalaryMappingCreate
) -> EmployeeSalaryMapping:
    """Assign an employee to a salary structure. Updates if mapping already exists."""
    existing = db.execute(
        select(EmployeeSalaryMapping).where(
            EmployeeSalaryMapping.employee_id == payload.employee_id
        )
    ).scalar_one_or_none()

    if existing:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    obj = EmployeeSalaryMapping(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_employee_salary_mapping(db: Session, employee_id: int) -> EmployeeSalaryMapping:
    """Get the salary mapping for a specific employee. Raises 404 if not found."""
    obj = db.execute(
        select(EmployeeSalaryMapping).where(
            EmployeeSalaryMapping.employee_id == employee_id
        )
    ).scalar_one_or_none()

    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No salary mapping found for this employee",
        )
    return obj
