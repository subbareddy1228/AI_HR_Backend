"""
routers/Payroll/salary_structure.py
REST API for the full Salary Structure Management module.

Tabs covered:
  GET  /api/payroll/salary-structures/dashboard              → page stats
  ── Components Master ──────────────────────────────────────
  GET  /api/payroll/salary-structures/components             → grouped master view
  POST /api/payroll/salary-structures/components             → add component
  GET  /api/payroll/salary-structures/components/{id}
  PUT  /api/payroll/salary-structures/components/{id}
  DELETE /api/payroll/salary-structures/components/{id}      → soft-delete
  ── Structure Templates ────────────────────────────────────
  GET  /api/payroll/salary-structures/templates              → filterable list
  POST /api/payroll/salary-structures/templates              → create template
  GET  /api/payroll/salary-structures/templates/{id}
  PUT  /api/payroll/salary-structures/templates/{id}
  POST /api/payroll/salary-structures/templates/{id}/activate
  POST /api/payroll/salary-structures/templates/{id}/deactivate
  DELETE /api/payroll/salary-structures/templates/{id}
  ── Structure Assignment ───────────────────────────────────
  GET  /api/payroll/salary-structures/assignments            → assignment table
  POST /api/payroll/salary-structures/assignments            → assign / re-assign
  GET  /api/payroll/salary-structures/assignments/employee/{employee_id}
  PUT  /api/payroll/salary-structures/assignments/{id}
  DELETE /api/payroll/salary-structures/assignments/{id}
  ── Legacy (backward-compat) ───────────────────────────────
  POST   /api/payroll/salary-structures/
  GET    /api/payroll/salary-structures/
  GET    /api/payroll/salary-structures/{id}
  PUT    /api/payroll/salary-structures/{id}
  DELETE /api/payroll/salary-structures/{id}
  GET    /api/payroll/salary-structures/employee/{employee_id}
  POST   /api/payroll/salary-structures/assign
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from core.database import get_db
import services.Payroll.salary_service as svc
from schema.Payroll.salary_structure import (
    # Components
    SalaryComponentCreate, SalaryComponentUpdate, SalaryComponentResponse,
    ComponentsMasterResponse,
    # Templates
    SalaryStructureTemplateCreate, SalaryStructureTemplateUpdate,
    SalaryStructureTemplateResponse, StructureTemplatesOverview,
    # Assignments
    StructureAssignmentCreate, StructureAssignmentUpdate,
    StructureAssignmentResponse,
    # Dashboard
    SalaryStructureDashboard,
    # Legacy
    SalaryStructureCreate, SalaryStructureUpdate, SalaryStructureResponse,
    EmployeeSalaryMappingCreate, EmployeeSalaryMappingResponse,
)

router = APIRouter(prefix="/salary-structures", tags=["Payroll - Salary Structure"])


# ─── Dashboard ───────────────────────────────

@router.get("/dashboard", response_model=SalaryStructureDashboard)
def get_dashboard(db: Session = Depends(get_db)):
    """Aggregate stats displayed at the top of the Salary Structure Management page."""
    return svc.get_salary_structure_dashboard(db)


# ─── Components Master ───────────────────────

@router.get("/components", response_model=ComponentsMasterResponse)
def get_components_master(db: Session = Depends(get_db)):
    """All components grouped by category for the Components Master tab."""
    return svc.get_components_master(db)


@router.post(
    "/components",
    response_model=SalaryComponentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_component(payload: SalaryComponentCreate, db: Session = Depends(get_db)):
    return svc.create_component(db, payload)


@router.get("/components/list", response_model=List[SalaryComponentResponse])
def list_components(
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.list_components(db, category=category, is_active=is_active)


@router.get("/components/{component_id}", response_model=SalaryComponentResponse)
def get_component(component_id: int, db: Session = Depends(get_db)):
    return svc.get_component(db, component_id)


@router.put("/components/{component_id}", response_model=SalaryComponentResponse)
def update_component(
    component_id: int,
    payload: SalaryComponentUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_component(db, component_id, payload)


@router.delete(
    "/components/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_component(component_id: int, db: Session = Depends(get_db)):
    svc.delete_component(db, component_id)


# ─── Structure Templates ─────────────────────

@router.get("/templates", response_model=StructureTemplatesOverview)
def list_templates(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Returns template cards grouped by status (Total / Active / Draft)."""
    return svc.get_templates_overview(db, status=status, category=category,
                                      grade=grade, department=department)


@router.post(
    "/templates",
    response_model=SalaryStructureTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    payload: SalaryStructureTemplateCreate, db: Session = Depends(get_db)
):
    return svc.create_template(db, payload)


@router.get("/templates/{template_id}", response_model=SalaryStructureTemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db)):
    return svc.get_template(db, template_id)


@router.put("/templates/{template_id}", response_model=SalaryStructureTemplateResponse)
def update_template(
    template_id: int,
    payload: SalaryStructureTemplateUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_template(db, template_id, payload)


@router.post("/templates/{template_id}/activate", response_model=SalaryStructureTemplateResponse)
def activate_template(template_id: int, db: Session = Depends(get_db)):
    return svc.activate_template(db, template_id)


@router.post("/templates/{template_id}/deactivate", response_model=SalaryStructureTemplateResponse)
def deactivate_template(template_id: int, db: Session = Depends(get_db)):
    return svc.deactivate_template(db, template_id)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    svc.delete_template(db, template_id)


# ─── Structure Assignment ────────────────────

@router.get("/assignments", response_model=List[StructureAssignmentResponse])
def list_assignments(
    department: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    template_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Returns the assignment table rows."""
    return svc.list_assignments(db, department=department,
                                grade=grade, template_id=template_id)


@router.post(
    "/assignments",
    response_model=StructureAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_employee(
    payload: StructureAssignmentCreate, db: Session = Depends(get_db)
):
    """Create or update (upsert) a structure assignment for an employee."""
    return svc.create_or_update_assignment(db, payload)


@router.get(
    "/assignments/employee/{employee_id}",
    response_model=StructureAssignmentResponse,
)
def get_employee_assignment(employee_id: int, db: Session = Depends(get_db)):
    return svc.get_employee_assignment(db, employee_id)


@router.put("/assignments/{assignment_id}", response_model=StructureAssignmentResponse)
def update_assignment(
    assignment_id: int,
    payload: StructureAssignmentUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_assignment(db, assignment_id, payload)


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    svc.delete_assignment(db, assignment_id)


# ─── Legacy endpoints (backward-compat) ──────

@router.post("/", response_model=SalaryStructureResponse, status_code=status.HTTP_201_CREATED)
def create_salary_structure(payload: SalaryStructureCreate, db: Session = Depends(get_db)):
    return svc.create_salary_structure(db, payload)


@router.get("/", response_model=List[SalaryStructureResponse])
def list_salary_structures(db: Session = Depends(get_db)):
    return svc.list_salary_structures(db)


@router.get("/{structure_id}", response_model=SalaryStructureResponse)
def get_salary_structure(structure_id: int, db: Session = Depends(get_db)):
    return svc.get_salary_structure(db, structure_id)


@router.put("/{structure_id}", response_model=SalaryStructureResponse)
def update_salary_structure(
    structure_id: int, payload: SalaryStructureUpdate, db: Session = Depends(get_db)
):
    return svc.update_salary_structure(db, structure_id, payload)


@router.delete("/{structure_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salary_structure(structure_id: int, db: Session = Depends(get_db)):
    svc.delete_salary_structure(db, structure_id)


@router.get("/employee/{employee_id}", response_model=EmployeeSalaryMappingResponse)
def get_employee_salary_mapping(employee_id: int, db: Session = Depends(get_db)):
    return svc.get_employee_salary_mapping(db, employee_id)


@router.post(
    "/assign",
    response_model=EmployeeSalaryMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_employee_to_structure(
    payload: EmployeeSalaryMappingCreate, db: Session = Depends(get_db)
):
    return svc.assign_employee_to_structure(db, payload)