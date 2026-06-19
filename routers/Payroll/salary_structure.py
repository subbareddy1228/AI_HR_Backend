# from fastapi import APIRouter, Depends, Query, status
# from sqlalchemy.orm import Session
# from typing import List, Optional

# from app.database import get_db
# from app.payroll.schemas.salary_structure import (
#     SalaryStructureCreate,
#     SalaryStructureUpdate,
#     SalaryStructureResponse,
#     SalaryStructureListResponse,
#     SalaryComponentCreate,
#     SalaryComponentUpdate,
#     SalaryComponentResponse,
#     EmployeeSalaryStructureCreate,
#     EmployeeSalaryStructureUpdate,
#     EmployeeSalaryStructureResponse,
#     SalaryBreakdownResponse,
# )
# from app.payroll.services.salary_structure_service import (
#     create_salary_structure,
#     get_salary_structure,
#     get_all_salary_structures,
#     update_salary_structure,
#     delete_salary_structure,
#     add_component_to_structure,
#     get_component,
#     update_component,
#     delete_component,
#     get_components_by_structure,
#     assign_structure_to_employee,
#     get_employee_salary_structure,
#     update_employee_salary_structure,
#     get_all_employee_assignments,
#     calculate_salary_breakdown,
# )

# router = APIRouter(
#     prefix="/salary-structure",
#     tags=["Salary Structure"],
# )


# # ─────────────────────────────────────────────
# # Salary Structure Endpoints
# # ─────────────────────────────────────────────

# @router.post("/", response_model=SalaryStructureResponse, status_code=status.HTTP_201_CREATED)
# def create_structure(data: SalaryStructureCreate, db: Session = Depends(get_db)):
#     """Create a new salary structure with optional components."""
#     return create_salary_structure(db, data)


# @router.get("/", response_model=List[SalaryStructureListResponse])
# def list_structures(
#     skip: int = Query(0, ge=0),
#     limit: int = Query(100, ge=1, le=200),
#     is_active: Optional[bool] = Query(None),
#     db: Session = Depends(get_db),
# ):
#     """Get all salary structures. Filter by active status optionally."""
#     return get_all_salary_structures(db, skip=skip, limit=limit, is_active=is_active)


# @router.get("/{structure_id}", response_model=SalaryStructureResponse)
# def get_structure(structure_id: int, db: Session = Depends(get_db)):
#     """Get a specific salary structure with all its components."""
#     return get_salary_structure(db, structure_id)


# @router.put("/{structure_id}", response_model=SalaryStructureResponse)
# def update_structure(
#     structure_id: int, data: SalaryStructureUpdate, db: Session = Depends(get_db)
# ):
#     """Update a salary structure's name, description, or active status."""
#     return update_salary_structure(db, structure_id, data)


# @router.delete("/{structure_id}", status_code=status.HTTP_200_OK)
# def delete_structure(structure_id: int, db: Session = Depends(get_db)):
#     """Delete a salary structure and all its components."""
#     return delete_salary_structure(db, structure_id)


# # ─────────────────────────────────────────────
# # Salary Component Endpoints
# # ─────────────────────────────────────────────

# @router.post("/{structure_id}/components", response_model=SalaryComponentResponse, status_code=status.HTTP_201_CREATED)
# def add_component(
#     structure_id: int, data: SalaryComponentCreate, db: Session = Depends(get_db)
# ):
#     """Add a new salary component to an existing structure."""
#     return add_component_to_structure(db, structure_id, data)


# @router.get("/{structure_id}/components", response_model=List[SalaryComponentResponse])
# def list_components(structure_id: int, db: Session = Depends(get_db)):
#     """List all components for a salary structure, ordered by sequence."""
#     return get_components_by_structure(db, structure_id)


# @router.get("/components/{component_id}", response_model=SalaryComponentResponse)
# def get_single_component(component_id: int, db: Session = Depends(get_db)):
#     """Get details of a specific salary component."""
#     return get_component(db, component_id)


# @router.put("/components/{component_id}", response_model=SalaryComponentResponse)
# def update_single_component(
#     component_id: int, data: SalaryComponentUpdate, db: Session = Depends(get_db)
# ):
#     """Update a salary component's value, formula, or other properties."""
#     return update_component(db, component_id, data)


# @router.delete("/components/{component_id}", status_code=status.HTTP_200_OK)
# def delete_single_component(component_id: int, db: Session = Depends(get_db)):
#     """Delete a salary component from a structure."""
#     return delete_component(db, component_id)


# # ─────────────────────────────────────────────
# # Employee Salary Structure Assignment Endpoints
# # ─────────────────────────────────────────────

# @router.post("/assign", response_model=EmployeeSalaryStructureResponse, status_code=status.HTTP_201_CREATED)
# def assign_to_employee(
#     data: EmployeeSalaryStructureCreate, db: Session = Depends(get_db)
# ):
#     """Assign a salary structure to an employee with CTC and basic salary."""
#     return assign_structure_to_employee(db, data)


# @router.get("/employee/{employee_id}/active", response_model=EmployeeSalaryStructureResponse)
# def get_active_assignment(employee_id: int, db: Session = Depends(get_db)):
#     """Get the current active salary structure assignment for an employee."""
#     return get_employee_salary_structure(db, employee_id)


# @router.get("/employee/{employee_id}/history", response_model=List[EmployeeSalaryStructureResponse])
# def get_assignment_history(employee_id: int, db: Session = Depends(get_db)):
#     """Get full salary structure assignment history for an employee."""
#     return get_all_employee_assignments(db, employee_id)


# @router.put("/assign/{assignment_id}", response_model=EmployeeSalaryStructureResponse)
# def update_assignment(
#     assignment_id: int,
#     data: EmployeeSalaryStructureUpdate,
#     db: Session = Depends(get_db),
# ):
#     """Update an employee's salary structure assignment (CTC, dates, etc.)."""
#     return update_employee_salary_structure(db, assignment_id, data)


# # ─────────────────────────────────────────────
# # Salary Breakdown
# # ─────────────────────────────────────────────

# @router.get("/employee/{employee_id}/breakdown", response_model=SalaryBreakdownResponse)
# def get_salary_breakdown(employee_id: int, db: Session = Depends(get_db)):
#     """
#     Calculate and return a full salary breakdown for an employee:
#     - Gross earnings
#     - Total deductions
#     - Net salary
#     - Component-wise amounts
#     """
#     return calculate_salary_breakdown(db, employee_id)



# from fastapi import APIRouter, Depends, Query, status
# from sqlalchemy.orm import Session
# from typing import List, Optional

# from core.database import get_db
# from schema.Payroll.salary_structure import (
#     SalaryStructureCreate,
#     SalaryStructureUpdate,
#     SalaryStructureResponse,
#     SalaryStructureListResponse,
#     SalaryComponentCreate,
#     SalaryComponentUpdate,
#     SalaryComponentResponse,
#     EmployeeSalaryStructureCreate,
#     EmployeeSalaryStructureUpdate,
#     EmployeeSalaryStructureResponse,
#     SalaryBreakdownResponse,
# )
# from services.Payroll.salary_structure import (
#     create_salary_structure,
#     get_salary_structure,
#     get_all_salary_structures,
#     update_salary_structure,
#     delete_salary_structure,
#     add_component_to_structure,
#     get_component,
#     update_component,
#     delete_component,
#     get_components_by_structure,
#     assign_structure_to_employee,
#     get_employee_salary_structure,
#     update_employee_salary_structure,
#     get_all_employee_assignments,
#     calculate_salary_breakdown,
# )

# router = APIRouter(
#     prefix="/salary-structure",
#     tags=["Salary Structure"],
# )


# # ─────────────────────────────────────────────
# # Salary Structure Endpoints
# # ─────────────────────────────────────────────

# @router.post("/", response_model=SalaryStructureResponse, status_code=status.HTTP_201_CREATED)
# def create_structure(data: SalaryStructureCreate, db: Session = Depends(get_db)):
#     """Create a new salary structure with optional components."""
#     return create_salary_structure(db, data)


# @router.get("/", response_model=List[SalaryStructureListResponse])
# def list_structures(
#     skip: int = Query(0, ge=0),
#     limit: int = Query(100, ge=1, le=200),
#     is_active: Optional[bool] = Query(None),
#     db: Session = Depends(get_db),
# ):
#     """Get all salary structures. Filter by active status optionally."""
#     return get_all_salary_structures(db, skip=skip, limit=limit, is_active=is_active)


# @router.get("/{structure_id}", response_model=SalaryStructureResponse)
# def get_structure(structure_id: int, db: Session = Depends(get_db)):
#     """Get a specific salary structure with all its components."""
#     return get_salary_structure(db, structure_id)


# @router.put("/{structure_id}", response_model=SalaryStructureResponse)
# def update_structure(
#     structure_id: int, data: SalaryStructureUpdate, db: Session = Depends(get_db)
# ):
#     """Update a salary structure's name, description, or active status."""
#     return update_salary_structure(db, structure_id, data)


# @router.delete("/{structure_id}", status_code=status.HTTP_200_OK)
# def delete_structure(structure_id: int, db: Session = Depends(get_db)):
#     """Delete a salary structure and all its components."""
#     return delete_salary_structure(db, structure_id)


# # ─────────────────────────────────────────────
# # Salary Component Endpoints
# # ─────────────────────────────────────────────

# @router.post("/{structure_id}/components", response_model=SalaryComponentResponse, status_code=status.HTTP_201_CREATED)
# def add_component(
#     structure_id: int, data: SalaryComponentCreate, db: Session = Depends(get_db)
# ):
#     """Add a new salary component to an existing structure."""
#     return add_component_to_structure(db, structure_id, data)


# @router.get("/{structure_id}/components", response_model=List[SalaryComponentResponse])
# def list_components(structure_id: int, db: Session = Depends(get_db)):
#     """List all components for a salary structure, ordered by sequence."""
#     return get_components_by_structure(db, structure_id)


# @router.get("/components/{component_id}", response_model=SalaryComponentResponse)
# def get_single_component(component_id: int, db: Session = Depends(get_db)):
#     """Get details of a specific salary component."""
#     return get_component(db, component_id)


# @router.put("/components/{component_id}", response_model=SalaryComponentResponse)
# def update_single_component(
#     component_id: int, data: SalaryComponentUpdate, db: Session = Depends(get_db)
# ):
#     """Update a salary component's value, formula, or other properties."""
#     return update_component(db, component_id, data)


# @router.delete("/components/{component_id}", status_code=status.HTTP_200_OK)
# def delete_single_component(component_id: int, db: Session = Depends(get_db)):
#     """Delete a salary component from a structure."""
#     return delete_component(db, component_id)


# # ─────────────────────────────────────────────
# # Employee Salary Structure Assignment Endpoints
# # ─────────────────────────────────────────────

# @router.post("/assign", response_model=EmployeeSalaryStructureResponse, status_code=status.HTTP_201_CREATED)
# def assign_to_employee(
#     data: EmployeeSalaryStructureCreate, db: Session = Depends(get_db)
# ):
#     """Assign a salary structure to an employee with CTC and basic salary."""
#     return assign_structure_to_employee(db, data)


# @router.get("/employee/{employee_id}/active", response_model=EmployeeSalaryStructureResponse)
# def get_active_assignment(employee_id: int, db: Session = Depends(get_db)):
#     """Get the current active salary structure assignment for an employee."""
#     return get_employee_salary_structure(db, employee_id)


# @router.get("/employee/{employee_id}/history", response_model=List[EmployeeSalaryStructureResponse])
# def get_assignment_history(employee_id: int, db: Session = Depends(get_db)):
#     """Get full salary structure assignment history for an employee."""
#     return get_all_employee_assignments(db, employee_id)


# @router.put("/assign/{assignment_id}", response_model=EmployeeSalaryStructureResponse)
# def update_assignment(
#     assignment_id: int,
#     data: EmployeeSalaryStructureUpdate,
#     db: Session = Depends(get_db),
# ):
#     """Update an employee's salary structure assignment (CTC, dates, etc.)."""
#     return update_employee_salary_structure(db, assignment_id, data)


# # ─────────────────────────────────────────────
# # Salary Breakdown
# # ─────────────────────────────────────────────

# @router.get("/employee/{employee_id}/breakdown", response_model=SalaryBreakdownResponse)
# def get_salary_breakdown(employee_id: int, db: Session = Depends(get_db)):
#     """
#     Calculate and return a full salary breakdown for an employee:
#     - Gross earnings
#     - Total deductions
#     - Net salary
#     - Component-wise amounts
#     """
#     return calculate_salary_breakdown(db, employee_id)



# routers/Payroll/salary_structure.py
# REPLACE your entire existing file with this. Clean — no commented duplicates.
# NEW endpoints added:
#   GET /api/payroll/salary-structure/kpi
#   GET /api/payroll/salary-structure/components/export

import io
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from schema.Payroll.salary_structure import (
    SalaryStructureCreate,
    SalaryStructureUpdate,
    SalaryStructureResponse,
    SalaryStructureListResponse,
    SalaryComponentCreate,
    SalaryComponentUpdate,
    SalaryComponentResponse,
    EmployeeSalaryStructureCreate,
    EmployeeSalaryStructureUpdate,
    EmployeeSalaryStructureResponse,
    SalaryBreakdownResponse,
    SalaryStructureKPIResponse,
)
from services.Payroll.salary_structure import (
    get_salary_structure_kpi,
    export_components_csv,
    create_salary_structure,
    get_salary_structure,
    get_all_salary_structures,
    update_salary_structure,
    delete_salary_structure,
    add_component_to_structure,
    get_component,
    update_component,
    delete_component,
    get_components_by_structure,
    assign_structure_to_employee,
    get_employee_salary_structure,
    update_employee_salary_structure,
    get_all_employee_assignments,
    calculate_salary_breakdown,
)

router = APIRouter(
    prefix="/salary-structure",
    tags=["Salary Structure"],
)


# ─────────────────────────────────────────────
# KPI  ← NEW
# GET /api/payroll/salary-structure/kpi
# ─────────────────────────────────────────────

@router.get(
    "/kpi",
    response_model=SalaryStructureKPIResponse,
    summary="Dashboard KPIs — Total Structures, Active Assignments, Total Components",
)
def salary_structure_kpi(db: Session = Depends(get_db)):
    return get_salary_structure_kpi(db)


# ─────────────────────────────────────────────
# Export Components CSV  ← NEW
# GET /api/payroll/salary-structure/components/export
# ─────────────────────────────────────────────

@router.get(
    "/components/export",
    summary="Export salary components as CSV (optionally filter by structure or type)",
)
def export_components(
    structure_id: Optional[int] = Query(None),
    component_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    csv_bytes = export_components_csv(db, structure_id=structure_id, component_type=component_type)
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="salary_components.csv"'},
    )


# ─────────────────────────────────────────────
# Salary Structure Endpoints
# ─────────────────────────────────────────────

@router.post("/", response_model=SalaryStructureResponse, status_code=status.HTTP_201_CREATED)
def create_structure(data: SalaryStructureCreate, db: Session = Depends(get_db)):
    """Create a new salary structure with optional components."""
    return create_salary_structure(db, data)


@router.get("/", response_model=List[SalaryStructureListResponse])
def list_structures(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """Get all salary structures. Filter by active status optionally."""
    return get_all_salary_structures(db, skip=skip, limit=limit, is_active=is_active)


@router.get("/{structure_id}", response_model=SalaryStructureResponse)
def get_structure(structure_id: int, db: Session = Depends(get_db)):
    """Get a specific salary structure with all its components."""
    return get_salary_structure(db, structure_id)


@router.put("/{structure_id}", response_model=SalaryStructureResponse)
def update_structure(
    structure_id: int, data: SalaryStructureUpdate, db: Session = Depends(get_db)
):
    """Update a salary structure's name, description, or active status."""
    return update_salary_structure(db, structure_id, data)


@router.delete("/{structure_id}", status_code=status.HTTP_200_OK)
def delete_structure(structure_id: int, db: Session = Depends(get_db)):
    """Delete a salary structure and all its components."""
    return delete_salary_structure(db, structure_id)


# ─────────────────────────────────────────────
# Salary Component Endpoints
# ─────────────────────────────────────────────

@router.post("/{structure_id}/components", response_model=SalaryComponentResponse, status_code=status.HTTP_201_CREATED)
def add_component(
    structure_id: int, data: SalaryComponentCreate, db: Session = Depends(get_db)
):
    """Add a new salary component to an existing structure."""
    return add_component_to_structure(db, structure_id, data)


@router.get("/{structure_id}/components", response_model=List[SalaryComponentResponse])
def list_components(structure_id: int, db: Session = Depends(get_db)):
    """List all components for a salary structure, ordered by sequence."""
    return get_components_by_structure(db, structure_id)


@router.get("/components/{component_id}", response_model=SalaryComponentResponse)
def get_single_component(component_id: int, db: Session = Depends(get_db)):
    """Get details of a specific salary component."""
    return get_component(db, component_id)


@router.put("/components/{component_id}", response_model=SalaryComponentResponse)
def update_single_component(
    component_id: int, data: SalaryComponentUpdate, db: Session = Depends(get_db)
):
    """Update a salary component's value, formula, or other properties."""
    return update_component(db, component_id, data)


@router.delete("/components/{component_id}", status_code=status.HTTP_200_OK)
def delete_single_component(component_id: int, db: Session = Depends(get_db)):
    """Delete a salary component from a structure."""
    return delete_component(db, component_id)


# ─────────────────────────────────────────────
# Employee Salary Structure Assignment Endpoints
# ─────────────────────────────────────────────

@router.post("/assign", response_model=EmployeeSalaryStructureResponse, status_code=status.HTTP_201_CREATED)
def assign_to_employee(
    data: EmployeeSalaryStructureCreate, db: Session = Depends(get_db)
):
    """Assign a salary structure to an employee with CTC and basic salary."""
    return assign_structure_to_employee(db, data)


@router.get("/employee/{employee_id}/active", response_model=EmployeeSalaryStructureResponse)
def get_active_assignment(employee_id: int, db: Session = Depends(get_db)):
    """Get the current active salary structure assignment for an employee."""
    return get_employee_salary_structure(db, employee_id)


@router.get("/employee/{employee_id}/history", response_model=List[EmployeeSalaryStructureResponse])
def get_assignment_history(employee_id: int, db: Session = Depends(get_db)):
    """Get full salary structure assignment history for an employee."""
    return get_all_employee_assignments(db, employee_id)


@router.put("/assign/{assignment_id}", response_model=EmployeeSalaryStructureResponse)
def update_assignment(
    assignment_id: int,
    data: EmployeeSalaryStructureUpdate,
    db: Session = Depends(get_db),
):
    """Update an employee's salary structure assignment (CTC, dates, etc.)."""
    return update_employee_salary_structure(db, assignment_id, data)


# ─────────────────────────────────────────────
# Salary Breakdown
# ─────────────────────────────────────────────

@router.get("/employee/{employee_id}/breakdown", response_model=SalaryBreakdownResponse)
def get_salary_breakdown(employee_id: int, db: Session = Depends(get_db)):
    """
    Calculate and return a full salary breakdown for an employee:
    - Gross earnings
    - Total deductions
    - Net salary
    - Component-wise amounts
    """
    return calculate_salary_breakdown(db, employee_id)




