# routers/Payroll/salary_structure.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.dependencies import get_current_user
from schema.Payroll.salary_structure import (
    SalaryStructureCreate, SalaryStructureUpdate, SalaryStructureResponse,
    EmployeeSalaryMappingCreate, EmployeeSalaryMappingUpdate, EmployeeSalaryMappingResponse,
)
from services.Payroll.salary_service import (
    create_salary_structure, list_salary_structures, get_salary_structure,
    update_salary_structure, delete_salary_structure,
    assign_employee_to_structure, get_employee_salary_mapping,
)

router = APIRouter(prefix="/api/payroll/salary-structures", tags=["Salary Structure"])


# ── Salary Structures ────────────────────────────────────────────────────────

@router.get("/", response_model=List[SalaryStructureResponse])
def list_structures(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """List all salary structures. Used in SalaryStructure.jsx dropdown."""
    return list_salary_structures(db)


@router.post("/", response_model=SalaryStructureResponse, status_code=status.HTTP_201_CREATED)
def create_structure(
    payload: SalaryStructureCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new salary structure. Raises 409 if name already exists."""
    return create_salary_structure(db, payload)


@router.get("/{structure_id}", response_model=SalaryStructureResponse)
def get_structure(structure_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Fetch a single salary structure by ID."""
    return get_salary_structure(db, structure_id)


@router.put("/{structure_id}", response_model=SalaryStructureResponse)
def update_structure(
    structure_id: int,
    payload: SalaryStructureUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update a salary structure's percentages and settings."""
    return update_salary_structure(db, structure_id, payload)


@router.delete("/{structure_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_structure(structure_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Delete a salary structure."""
    delete_salary_structure(db, structure_id)


# ── Employee Salary Mapping ──────────────────────────────────────────────────

@router.post("/mappings/assign", response_model=EmployeeSalaryMappingResponse, status_code=status.HTTP_201_CREATED)
def assign_employee(
    payload: EmployeeSalaryMappingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Assign or update an employee's salary structure mapping."""
    return assign_employee_to_structure(db, payload)


@router.get("/mappings/employee/{employee_id}", response_model=EmployeeSalaryMappingResponse)
def get_employee_mapping(employee_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get salary mapping for a specific employee."""
    return get_employee_salary_mapping(db, employee_id)
