# FILE 10 of 18 | routers/Payroll/salary_structure.py
# Router: Salary Structures — prefix: /salary-structures  (mounted under /api/payroll in main.py)
# Endpoints:
#   POST   /salary-structures/                         — create structure
#   GET    /salary-structures/                         — list all
#   GET    /salary-structures/{id}                     — get one
#   PUT    /salary-structures/{id}                     — update
#   DELETE /salary-structures/{id}                     — delete
#   POST   /salary-structures/assign                   — assign employee to structure
#   GET    /salary-structures/employee/{employee_id}   — get mapping for employee

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from core.database import get_db
from model.Payroll.salary_structure import SalaryStructure, EmployeeSalaryMapping
from schema.Payroll.salary_structure import (
    SalaryStructureCreate, SalaryStructureUpdate, SalaryStructureResponse,
    EmployeeSalaryMappingCreate, EmployeeSalaryMappingResponse,
)

router = APIRouter(prefix="/salary-structures", tags=["Payroll"])


@router.post("/", response_model=SalaryStructureResponse, status_code=status.HTTP_201_CREATED)
def create_salary_structure(payload: SalaryStructureCreate, db: Session = Depends(get_db)):
    obj = SalaryStructure(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/", response_model=list[SalaryStructureResponse])
def list_salary_structures(db: Session = Depends(get_db)):
    return db.execute(select(SalaryStructure)).scalars().all()


@router.get("/employee/{employee_id}", response_model=EmployeeSalaryMappingResponse)
def get_employee_salary_mapping(employee_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(EmployeeSalaryMapping).where(EmployeeSalaryMapping.employee_id == employee_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="No salary mapping found for this employee")
    return obj


@router.post("/assign", response_model=EmployeeSalaryMappingResponse, status_code=status.HTTP_201_CREATED)
def assign_employee_to_structure(payload: EmployeeSalaryMappingCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(EmployeeSalaryMapping).where(EmployeeSalaryMapping.employee_id == payload.employee_id)
    ).scalar_one_or_none()
    if existing:
        # Update in place instead of duplicating
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    obj = EmployeeSalaryMapping(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{structure_id}", response_model=SalaryStructureResponse)
def get_salary_structure(structure_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(SalaryStructure).where(SalaryStructure.id == structure_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Salary structure not found")
    return obj


@router.put("/{structure_id}", response_model=SalaryStructureResponse)
def update_salary_structure(
    structure_id: int, payload: SalaryStructureUpdate, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(SalaryStructure).where(SalaryStructure.id == structure_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Salary structure not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{structure_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salary_structure(structure_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(SalaryStructure).where(SalaryStructure.id == structure_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Salary structure not found")
    db.delete(obj)
    db.commit()
