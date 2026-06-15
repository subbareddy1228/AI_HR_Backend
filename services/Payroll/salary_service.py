"""
services/Payroll/salary_service.py
Business logic for all three Salary Structure Management tabs.
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func
from typing import List, Optional
from fastapi import HTTPException, status

from model.Payroll.salary_structure import (
    SalaryComponent, SalaryStructureTemplate, StructureComponentLine,
    StructureAssignment, SalaryStructure, EmployeeSalaryMapping,
    ComponentCategory, StructureStatus,
)
from schema.Payroll.salary_structure import (
    SalaryComponentCreate, SalaryComponentUpdate,
    SalaryStructureTemplateCreate, SalaryStructureTemplateUpdate,
    StructureAssignmentCreate, StructureAssignmentUpdate,
    ComponentsMasterResponse, StructureTemplatesOverview,
    SalaryStructureDashboard, StructureAssignmentDetail,
    SalaryStructureCreate, SalaryStructureUpdate,
    EmployeeSalaryMappingCreate,
)


# ═══════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════

def get_salary_structure_dashboard(db: Session) -> SalaryStructureDashboard:
    """Returns the aggregate stats shown at the top of the page."""

    def _count(model, **filters):
        q = select(func.count()).select_from(model)
        for col, val in filters.items():
            q = q.where(getattr(model, col) == val)
        return db.execute(q).scalar_one()

    return SalaryStructureDashboard(
        total_structures=_count(SalaryStructureTemplate),
        active_structures=_count(SalaryStructureTemplate, status=StructureStatus.ACTIVE),
        draft_structures=_count(SalaryStructureTemplate, status=StructureStatus.DRAFT),
        active_assignments=_count(StructureAssignment, effective_to=None),
        total_assignments=_count(StructureAssignment),
        pending_assignments=0,   # extend with an approval workflow if needed
        total_components=_count(SalaryComponent),
        active_components=_count(SalaryComponent, is_active=True),
        inactive_components=_count(SalaryComponent, is_active=False),
    )


# ═══════════════════════════════════════════════
# 1. Components Master
# ═══════════════════════════════════════════════

def get_components_master(db: Session) -> ComponentsMasterResponse:
    """Returns all components grouped for the Components Master tab."""
    all_comps = db.execute(
        select(SalaryComponent).where(SalaryComponent.is_active == True)
        .order_by(SalaryComponent.category, SalaryComponent.component_name)
    ).scalars().all()

    by_cat = {cat: [] for cat in ComponentCategory}
    for c in all_comps:
        by_cat[c.category].append(c)

    all_total = db.execute(select(func.count()).select_from(SalaryComponent)).scalar_one()

    return ComponentsMasterResponse(
        earnings=by_cat[ComponentCategory.EARNINGS],
        deductions=by_cat[ComponentCategory.DEDUCTIONS],
        employer_contributions=by_cat[ComponentCategory.EMPLOYER_CONTRIBUTION],
        reimbursements=by_cat[ComponentCategory.REIMBURSEMENT],
        total_components=all_total,
        active_components=len(all_comps),
        taxable_components=sum(1 for c in all_comps if c.is_taxable),
        statutory_components=sum(1 for c in all_comps if c.is_statutory),
        fixed_components=sum(1 for c in all_comps if c.component_type == "fixed"),
        variable_components=sum(1 for c in all_comps if c.component_type == "variable"),
    )


def create_component(db: Session, payload: SalaryComponentCreate) -> SalaryComponent:
    _assert_unique_component(db, payload.component_code, payload.component_name)
    obj = SalaryComponent(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_component(db: Session, component_id: int) -> SalaryComponent:
    obj = db.get(SalaryComponent, component_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Component not found")
    return obj


def list_components(
    db: Session,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[SalaryComponent]:
    q = select(SalaryComponent)
    if category:
        q = q.where(SalaryComponent.category == category)
    if is_active is not None:
        q = q.where(SalaryComponent.is_active == is_active)
    return db.execute(q).scalars().all()


def update_component(
    db: Session, component_id: int, payload: SalaryComponentUpdate
) -> SalaryComponent:
    obj = get_component(db, component_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_component(db: Session, component_id: int) -> None:
    obj = get_component(db, component_id)
    # Soft-delete: keep history intact
    obj.is_active = False
    db.commit()


# ═══════════════════════════════════════════════
# 2. Structure Templates
# ═══════════════════════════════════════════════

def get_templates_overview(
    db: Session,
    status: Optional[str] = None,
    category: Optional[str] = None,
    grade: Optional[str] = None,
    department: Optional[str] = None,
) -> StructureTemplatesOverview:
    q = select(SalaryStructureTemplate).options(
        joinedload(SalaryStructureTemplate.component_lines)
        .joinedload(StructureComponentLine.component)
    )
    if status:
        q = q.where(SalaryStructureTemplate.status == status)
    if category:
        q = q.where(SalaryStructureTemplate.category == category)
    if grade:
        q = q.where(SalaryStructureTemplate.grade == grade)
    if department:
        q = q.where(SalaryStructureTemplate.department == department)

    templates = db.execute(q).unique().scalars().all()

    def _cnt(s):
        return sum(1 for t in templates if t.status == s)

    return StructureTemplatesOverview(
        total_structures=len(templates),
        active_structures=_cnt(StructureStatus.ACTIVE),
        draft_structures=_cnt(StructureStatus.DRAFT),
        inactive_structures=_cnt(StructureStatus.INACTIVE),
        templates=templates,
    )


def create_template(
    db: Session, payload: SalaryStructureTemplateCreate
) -> SalaryStructureTemplate:
    _assert_unique_template_code(db, payload.template_code)

    lines_data = payload.model_dump(exclude={"component_lines"})
    obj = SalaryStructureTemplate(**lines_data)
    db.add(obj)
    db.flush()  # get obj.id before adding lines

    for line in payload.component_lines:
        db.add(StructureComponentLine(template_id=obj.id, **line.model_dump()))

    db.commit()
    db.refresh(obj)
    return obj


def get_template(db: Session, template_id: int) -> SalaryStructureTemplate:
    obj = db.execute(
        select(SalaryStructureTemplate)
        .options(
            joinedload(SalaryStructureTemplate.component_lines)
            .joinedload(StructureComponentLine.component)
        )
        .where(SalaryStructureTemplate.id == template_id)
    ).unique().scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Salary structure template not found")
    return obj


def update_template(
    db: Session, template_id: int, payload: SalaryStructureTemplateUpdate
) -> SalaryStructureTemplate:
    obj = get_template(db, template_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def activate_template(db: Session, template_id: int) -> SalaryStructureTemplate:
    obj = get_template(db, template_id)
    obj.status = StructureStatus.ACTIVE
    db.commit()
    db.refresh(obj)
    return obj


def deactivate_template(db: Session, template_id: int) -> SalaryStructureTemplate:
    obj = get_template(db, template_id)
    obj.status = StructureStatus.INACTIVE
    db.commit()
    db.refresh(obj)
    return obj


def delete_template(db: Session, template_id: int) -> None:
    obj = get_template(db, template_id)
    if obj.status == StructureStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an active template. Deactivate it first.",
        )
    db.delete(obj)
    db.commit()


# ═══════════════════════════════════════════════
# 3. Structure Assignments
# ═══════════════════════════════════════════════

def list_assignments(
    db: Session,
    department: Optional[str] = None,
    grade: Optional[str] = None,
    template_id: Optional[int] = None,
) -> List[StructureAssignment]:
    q = select(StructureAssignment)
    if template_id:
        q = q.where(StructureAssignment.template_id == template_id)
    return db.execute(q).scalars().all()


def create_or_update_assignment(
    db: Session, payload: StructureAssignmentCreate
) -> StructureAssignment:
    """
    Upsert logic: if an active (effective_to=None) assignment exists for the
    employee, close it and create a new one (history-preserving approach).
    """
    existing = db.execute(
        select(StructureAssignment)
        .where(
            StructureAssignment.employee_id == payload.employee_id,
            StructureAssignment.effective_to == None,  # noqa: E711
        )
    ).scalar_one_or_none()

    if existing:
        from datetime import date
        existing.effective_to = date.today()
        db.flush()

    obj = StructureAssignment(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Update template employee count
    _refresh_employee_count(db, payload.template_id)
    return obj


def get_employee_assignment(db: Session, employee_id: int) -> StructureAssignment:
    obj = db.execute(
        select(StructureAssignment)
        .where(
            StructureAssignment.employee_id == employee_id,
            StructureAssignment.effective_to == None,  # noqa: E711
        )
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(
            status_code=404, detail="No active salary assignment found for this employee"
        )
    return obj


def update_assignment(
    db: Session, assignment_id: int, payload: StructureAssignmentUpdate
) -> StructureAssignment:
    obj = db.get(StructureAssignment, assignment_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Assignment not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_assignment(db: Session, assignment_id: int) -> None:
    obj = db.get(StructureAssignment, assignment_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(obj)
    db.commit()


# ═══════════════════════════════════════════════
# 4. Legacy helpers (backward-compat)
# ═══════════════════════════════════════════════

def create_salary_structure(db: Session, payload: SalaryStructureCreate) -> SalaryStructure:
    existing = db.execute(
        select(SalaryStructure).where(SalaryStructure.structure_name == payload.structure_name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Salary structure '{payload.structure_name}' already exists",
        )
    obj = SalaryStructure(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_salary_structures(db: Session) -> List[SalaryStructure]:
    return db.execute(select(SalaryStructure)).scalars().all()


def get_salary_structure(db: Session, structure_id: int) -> SalaryStructure:
    obj = db.get(SalaryStructure, structure_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Salary structure not found")
    return obj


def update_salary_structure(
    db: Session, structure_id: int, payload: SalaryStructureUpdate
) -> SalaryStructure:
    obj = get_salary_structure(db, structure_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_salary_structure(db: Session, structure_id: int) -> None:
    obj = get_salary_structure(db, structure_id)
    db.delete(obj)
    db.commit()


def assign_employee_to_structure(
    db: Session, payload: EmployeeSalaryMappingCreate
) -> EmployeeSalaryMapping:
    existing = db.execute(
        select(EmployeeSalaryMapping).where(
            EmployeeSalaryMapping.employee_id == payload.employee_id
        )
    ).scalar_one_or_none()
    if existing:
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


def get_employee_salary_mapping(db: Session, employee_id: int) -> EmployeeSalaryMapping:
    obj = db.execute(
        select(EmployeeSalaryMapping).where(
            EmployeeSalaryMapping.employee_id == employee_id
        )
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(
            status_code=404, detail="No salary mapping found for this employee"
        )
    return obj


# ═══════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════

def _assert_unique_component(db: Session, code: str, name: str) -> None:
    dup = db.execute(
        select(SalaryComponent).where(
            (SalaryComponent.component_code == code)
            | (SalaryComponent.component_name == name)
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=409,
            detail=f"Component with code '{code}' or name '{name}' already exists",
        )


def _assert_unique_template_code(db: Session, code: str) -> None:
    dup = db.execute(
        select(SalaryStructureTemplate).where(SalaryStructureTemplate.template_code == code)
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=409,
            detail=f"Template code '{code}' already exists",
        )


def _refresh_employee_count(db: Session, template_id: int) -> None:
    count = db.execute(
        select(func.count())
        .select_from(StructureAssignment)
        .where(
            StructureAssignment.template_id == template_id,
            StructureAssignment.effective_to == None,  # noqa: E711
        )
    ).scalar_one()
    db.execute(
        SalaryStructureTemplate.__table__.update()
        .where(SalaryStructureTemplate.id == template_id)
        .values(employee_count=count)
    )
    db.commit()