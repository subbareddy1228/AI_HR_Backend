# from sqlalchemy.orm import Session
# from sqlalchemy.exc import IntegrityError
# from fastapi import HTTPException, status
# from typing import List, Optional

# from app.payroll.models.salary_structure import (
#     SalaryStructure,
#     SalaryComponent,
#     EmployeeSalaryStructure,
# )
# from app.payroll.schemas.salary_structure import (
#     SalaryStructureCreate,
#     SalaryStructureUpdate,
#     SalaryComponentCreate,
#     SalaryComponentUpdate,
#     EmployeeSalaryStructureCreate,
#     EmployeeSalaryStructureUpdate,
#     SalaryBreakdownResponse,
#     ComponentBreakdown,
# )


# # ─────────────────────────────────────────────
# # Salary Structure CRUD
# # ─────────────────────────────────────────────

# def create_salary_structure(db: Session, data: SalaryStructureCreate) -> SalaryStructure:
#     existing = db.query(SalaryStructure).filter(SalaryStructure.name == data.name).first()
#     if existing:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Salary structure with name '{data.name}' already exists."
#         )
#     structure = SalaryStructure(
#         name=data.name,
#         description=data.description,
#         is_active=data.is_active,
#     )
#     db.add(structure)
#     db.flush()  # get structure.id before adding components

#     for comp_data in data.components:
#         component = SalaryComponent(structure_id=structure.id, **comp_data.model_dump())
#         db.add(component)

#     db.commit()
#     db.refresh(structure)
#     return structure


# def get_salary_structure(db: Session, structure_id: int) -> SalaryStructure:
#     structure = db.query(SalaryStructure).filter(SalaryStructure.id == structure_id).first()
#     if not structure:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Salary structure with id {structure_id} not found."
#         )
#     return structure


# def get_all_salary_structures(
#     db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None
# ) -> List[SalaryStructure]:
#     query = db.query(SalaryStructure)
#     if is_active is not None:
#         query = query.filter(SalaryStructure.is_active == is_active)
#     return query.offset(skip).limit(limit).all()


# def update_salary_structure(
#     db: Session, structure_id: int, data: SalaryStructureUpdate
# ) -> SalaryStructure:
#     structure = get_salary_structure(db, structure_id)
#     update_data = data.model_dump(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(structure, key, value)
#     db.commit()
#     db.refresh(structure)
#     return structure


# def delete_salary_structure(db: Session, structure_id: int) -> dict:
#     structure = get_salary_structure(db, structure_id)
#     db.delete(structure)
#     db.commit()
#     return {"message": f"Salary structure '{structure.name}' deleted successfully."}


# # ─────────────────────────────────────────────
# # Salary Component CRUD
# # ─────────────────────────────────────────────

# def add_component_to_structure(
#     db: Session, structure_id: int, data: SalaryComponentCreate
# ) -> SalaryComponent:
#     get_salary_structure(db, structure_id)  # validate structure exists

#     duplicate = db.query(SalaryComponent).filter(
#         SalaryComponent.structure_id == structure_id,
#         SalaryComponent.code == data.code
#     ).first()
#     if duplicate:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Component with code '{data.code}' already exists in this structure."
#         )

#     component = SalaryComponent(structure_id=structure_id, **data.model_dump())
#     db.add(component)
#     db.commit()
#     db.refresh(component)
#     return component


# def get_component(db: Session, component_id: int) -> SalaryComponent:
#     component = db.query(SalaryComponent).filter(SalaryComponent.id == component_id).first()
#     if not component:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Component with id {component_id} not found."
#         )
#     return component


# def update_component(
#     db: Session, component_id: int, data: SalaryComponentUpdate
# ) -> SalaryComponent:
#     component = get_component(db, component_id)
#     update_data = data.model_dump(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(component, key, value)
#     db.commit()
#     db.refresh(component)
#     return component


# def delete_component(db: Session, component_id: int) -> dict:
#     component = get_component(db, component_id)
#     db.delete(component)
#     db.commit()
#     return {"message": f"Component '{component.name}' deleted successfully."}


# def get_components_by_structure(
#     db: Session, structure_id: int
# ) -> List[SalaryComponent]:
#     get_salary_structure(db, structure_id)
#     return (
#         db.query(SalaryComponent)
#         .filter(SalaryComponent.structure_id == structure_id)
#         .order_by(SalaryComponent.sequence)
#         .all()
#     )


# # ─────────────────────────────────────────────
# # Employee Salary Structure Assignment
# # ─────────────────────────────────────────────

# def assign_structure_to_employee(
#     db: Session, data: EmployeeSalaryStructureCreate
# ) -> EmployeeSalaryStructure:
#     get_salary_structure(db, data.structure_id)

#     # Deactivate any existing active assignment for this employee
#     existing = db.query(EmployeeSalaryStructure).filter(
#         EmployeeSalaryStructure.employee_id == data.employee_id,
#         EmployeeSalaryStructure.is_active == True
#     ).first()
#     if existing:
#         existing.is_active = False

#     assignment = EmployeeSalaryStructure(**data.model_dump())
#     db.add(assignment)
#     db.commit()
#     db.refresh(assignment)
#     return assignment


# def get_employee_salary_structure(
#     db: Session, employee_id: int
# ) -> EmployeeSalaryStructure:
#     assignment = db.query(EmployeeSalaryStructure).filter(
#         EmployeeSalaryStructure.employee_id == employee_id,
#         EmployeeSalaryStructure.is_active == True
#     ).first()
#     if not assignment:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No active salary structure found for employee {employee_id}."
#         )
#     return assignment


# def update_employee_salary_structure(
#     db: Session, assignment_id: int, data: EmployeeSalaryStructureUpdate
# ) -> EmployeeSalaryStructure:
#     assignment = db.query(EmployeeSalaryStructure).filter(
#         EmployeeSalaryStructure.id == assignment_id
#     ).first()
#     if not assignment:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Assignment with id {assignment_id} not found."
#         )
#     update_data = data.model_dump(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(assignment, key, value)
#     db.commit()
#     db.refresh(assignment)
#     return assignment


# def get_all_employee_assignments(
#     db: Session, employee_id: int
# ) -> List[EmployeeSalaryStructure]:
#     return db.query(EmployeeSalaryStructure).filter(
#         EmployeeSalaryStructure.employee_id == employee_id
#     ).order_by(EmployeeSalaryStructure.effective_from.desc()).all()


# # ─────────────────────────────────────────────
# # Salary Breakdown Calculation
# # ─────────────────────────────────────────────

# def calculate_salary_breakdown(
#     db: Session, employee_id: int
# ) -> SalaryBreakdownResponse:
#     assignment = get_employee_salary_structure(db, employee_id)
#     structure = get_salary_structure(db, assignment.structure_id)

#     components = (
#         db.query(SalaryComponent)
#         .filter(
#             SalaryComponent.structure_id == structure.id,
#             SalaryComponent.is_active == True
#         )
#         .order_by(SalaryComponent.sequence)
#         .all()
#     )

#     computed: dict[str, float] = {
#         "BASIC": assignment.basic_salary,
#         "CTC": assignment.ctc,
#     }
#     breakdown = []
#     gross_earnings = 0.0
#     total_deductions = 0.0

#     for comp in components:
#         amount = 0.0

#         if comp.calculation_type == "fixed":
#             amount = comp.value

#         elif comp.calculation_type == "percentage":
#             base_code = comp.depends_on or "BASIC"
#             base_val = computed.get(base_code, 0.0)
#             amount = (comp.value / 100) * base_val

#         elif comp.calculation_type == "formula" and comp.formula:
#             try:
#                 amount = float(eval(comp.formula, {"__builtins__": {}}, computed))
#             except Exception:
#                 amount = 0.0

#         computed[comp.code] = amount

#         breakdown.append(ComponentBreakdown(
#             code=comp.code,
#             name=comp.name,
#             component_type=comp.component_type,
#             amount=round(amount, 2),
#             is_taxable=comp.is_taxable,
#         ))

#         if comp.component_type == "earning":
#             gross_earnings += amount
#         elif comp.component_type in ("deduction", "statutory"):
#             total_deductions += amount

#     net_salary = assignment.basic_salary + gross_earnings - total_deductions

#     return SalaryBreakdownResponse(
#         employee_id=employee_id,
#         structure_name=structure.name,
#         ctc=assignment.ctc,
#         basic_salary=assignment.basic_salary,
#         gross_earnings=round(gross_earnings, 2),
#         total_deductions=round(total_deductions, 2),
#         net_salary=round(net_salary, 2),
#         components=breakdown,
#     )






# from sqlalchemy.orm import Session
# from sqlalchemy.exc import IntegrityError
# from fastapi import HTTPException, status
# from typing import List, Optional

# from model.Payroll.salary_structure import (
#     SalaryStructure,
#     SalaryComponent,
#     EmployeeSalaryStructure,
# )
# from schema.Payroll.salary_structure import (
#     SalaryStructureCreate,
#     SalaryStructureUpdate,
#     SalaryComponentCreate,
#     SalaryComponentUpdate,
#     EmployeeSalaryStructureCreate,
#     EmployeeSalaryStructureUpdate,
#     SalaryBreakdownResponse,
#     ComponentBreakdown,
# )


# # ─────────────────────────────────────────────
# # Salary Structure CRUD
# # ─────────────────────────────────────────────

# def create_salary_structure(db: Session, data: SalaryStructureCreate) -> SalaryStructure:
#     existing = db.query(SalaryStructure).filter(SalaryStructure.name == data.name).first()
#     if existing:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Salary structure with name '{data.name}' already exists."
#         )
#     structure = SalaryStructure(
#         name=data.name,
#         description=data.description,
#         is_active=data.is_active,
#     )
#     db.add(structure)
#     db.flush()  # get structure.id before adding components

#     for comp_data in data.components:
#         component = SalaryComponent(structure_id=structure.id, **comp_data.model_dump())
#         db.add(component)

#     db.commit()
#     db.refresh(structure)
#     return structure


# def get_salary_structure(db: Session, structure_id: int) -> SalaryStructure:
#     structure = db.query(SalaryStructure).filter(SalaryStructure.id == structure_id).first()
#     if not structure:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Salary structure with id {structure_id} not found."
#         )
#     return structure


# def get_all_salary_structures(
#     db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None
# ) -> List[SalaryStructure]:
#     query = db.query(SalaryStructure)
#     if is_active is not None:
#         query = query.filter(SalaryStructure.is_active == is_active)
#     return query.offset(skip).limit(limit).all()


# def update_salary_structure(
#     db: Session, structure_id: int, data: SalaryStructureUpdate
# ) -> SalaryStructure:
#     structure = get_salary_structure(db, structure_id)
#     update_data = data.model_dump(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(structure, key, value)
#     db.commit()
#     db.refresh(structure)
#     return structure


# def delete_salary_structure(db: Session, structure_id: int) -> dict:
#     structure = get_salary_structure(db, structure_id)
#     db.delete(structure)
#     db.commit()
#     return {"message": f"Salary structure '{structure.name}' deleted successfully."}


# # ─────────────────────────────────────────────
# # Salary Component CRUD
# # ─────────────────────────────────────────────

# def add_component_to_structure(
#     db: Session, structure_id: int, data: SalaryComponentCreate
# ) -> SalaryComponent:
#     get_salary_structure(db, structure_id)  # validate structure exists

#     duplicate = db.query(SalaryComponent).filter(
#         SalaryComponent.structure_id == structure_id,
#         SalaryComponent.code == data.code
#     ).first()
#     if duplicate:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Component with code '{data.code}' already exists in this structure."
#         )

#     component = SalaryComponent(structure_id=structure_id, **data.model_dump())
#     db.add(component)
#     db.commit()
#     db.refresh(component)
#     return component


# def get_component(db: Session, component_id: int) -> SalaryComponent:
#     component = db.query(SalaryComponent).filter(SalaryComponent.id == component_id).first()
#     if not component:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Component with id {component_id} not found."
#         )
#     return component


# def update_component(
#     db: Session, component_id: int, data: SalaryComponentUpdate
# ) -> SalaryComponent:
#     component = get_component(db, component_id)
#     update_data = data.model_dump(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(component, key, value)
#     db.commit()
#     db.refresh(component)
#     return component


# def delete_component(db: Session, component_id: int) -> dict:
#     component = get_component(db, component_id)
#     db.delete(component)
#     db.commit()
#     return {"message": f"Component '{component.name}' deleted successfully."}


# def get_components_by_structure(
#     db: Session, structure_id: int
# ) -> List[SalaryComponent]:
#     get_salary_structure(db, structure_id)
#     return (
#         db.query(SalaryComponent)
#         .filter(SalaryComponent.structure_id == structure_id)
#         .order_by(SalaryComponent.sequence)
#         .all()
#     )


# # ─────────────────────────────────────────────
# # Employee Salary Structure Assignment
# # ─────────────────────────────────────────────

# def assign_structure_to_employee(
#     db: Session, data: EmployeeSalaryStructureCreate
# ) -> EmployeeSalaryStructure:
#     get_salary_structure(db, data.structure_id)

#     # Deactivate any existing active assignment for this employee
#     existing = db.query(EmployeeSalaryStructure).filter(
#         EmployeeSalaryStructure.employee_id == data.employee_id,
#         EmployeeSalaryStructure.is_active == True
#     ).first()
#     if existing:
#         existing.is_active = False

#     assignment = EmployeeSalaryStructure(**data.model_dump())
#     db.add(assignment)
#     db.commit()
#     db.refresh(assignment)
#     return assignment


# def get_employee_salary_structure(
#     db: Session, employee_id: int
# ) -> EmployeeSalaryStructure:
#     assignment = db.query(EmployeeSalaryStructure).filter(
#         EmployeeSalaryStructure.employee_id == employee_id,
#         EmployeeSalaryStructure.is_active == True
#     ).first()
#     if not assignment:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No active salary structure found for employee {employee_id}."
#         )
#     return assignment


# def update_employee_salary_structure(
#     db: Session, assignment_id: int, data: EmployeeSalaryStructureUpdate
# ) -> EmployeeSalaryStructure:
#     assignment = db.query(EmployeeSalaryStructure).filter(
#         EmployeeSalaryStructure.id == assignment_id
#     ).first()
#     if not assignment:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Assignment with id {assignment_id} not found."
#         )
#     update_data = data.model_dump(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(assignment, key, value)
#     db.commit()
#     db.refresh(assignment)
#     return assignment


# def get_all_employee_assignments(
#     db: Session, employee_id: int
# ) -> List[EmployeeSalaryStructure]:
#     return db.query(EmployeeSalaryStructure).filter(
#         EmployeeSalaryStructure.employee_id == employee_id
#     ).order_by(EmployeeSalaryStructure.effective_from.desc()).all()


# # ─────────────────────────────────────────────
# # Salary Breakdown Calculation
# # ─────────────────────────────────────────────

# def calculate_salary_breakdown(
#     db: Session, employee_id: int
# ) -> SalaryBreakdownResponse:
#     assignment = get_employee_salary_structure(db, employee_id)
#     structure = get_salary_structure(db, assignment.structure_id)

#     components = (
#         db.query(SalaryComponent)
#         .filter(
#             SalaryComponent.structure_id == structure.id,
#             SalaryComponent.is_active == True
#         )
#         .order_by(SalaryComponent.sequence)
#         .all()
#     )

#     computed: dict[str, float] = {
#         "BASIC": assignment.basic_salary,
#         "CTC": assignment.ctc,
#     }
#     breakdown = []
#     gross_earnings = 0.0
#     total_deductions = 0.0

#     for comp in components:
#         amount = 0.0

#         if comp.calculation_type == "fixed":
#             amount = comp.value

#         elif comp.calculation_type == "percentage":
#             base_code = comp.depends_on or "BASIC"
#             base_val = computed.get(base_code, 0.0)
#             amount = (comp.value / 100) * base_val

#         elif comp.calculation_type == "formula" and comp.formula:
#             try:
#                 amount = float(eval(comp.formula, {"__builtins__": {}}, computed))
#             except Exception:
#                 amount = 0.0

#         computed[comp.code] = amount

#         breakdown.append(ComponentBreakdown(
#             code=comp.code,
#             name=comp.name,
#             component_type=comp.component_type,
#             amount=round(amount, 2),
#             is_taxable=comp.is_taxable,
#         ))

#         if comp.component_type == "earning":
#             gross_earnings += amount
#         elif comp.component_type in ("deduction", "statutory"):
#             total_deductions += amount

#     net_salary = assignment.basic_salary + gross_earnings - total_deductions

#     return SalaryBreakdownResponse(
#         employee_id=employee_id,
#         structure_name=structure.name,
#         ctc=assignment.ctc,
#         basic_salary=assignment.basic_salary,
#         gross_earnings=round(gross_earnings, 2),
#         total_deductions=round(total_deductions, 2),
#         net_salary=round(net_salary, 2),
#         components=breakdown,
#     )







# services/Payroll/salary_structure.py
# REPLACE your entire existing file with this. Clean — no commented duplicates.
# NEW functions added at the top: get_salary_structure_kpi(), export_components_csv()

import csv
import io
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from model.Payroll.salary_structure import (
    SalaryStructure,
    SalaryComponent,
    EmployeeSalaryStructure,
)
from schema.Payroll.salary_structure import (
    SalaryStructureCreate,
    SalaryStructureUpdate,
    SalaryComponentCreate,
    SalaryComponentUpdate,
    EmployeeSalaryStructureCreate,
    EmployeeSalaryStructureUpdate,
    SalaryBreakdownResponse,
    ComponentBreakdown,
    SalaryStructureKPIResponse,
)


# ─────────────────────────────────────────────
# KPI  ← NEW (was missing)
# ─────────────────────────────────────────────

def get_salary_structure_kpi(db: Session) -> SalaryStructureKPIResponse:
    total_structures = db.query(SalaryStructure).count()
    active_structures = db.query(SalaryStructure).filter(SalaryStructure.is_active == True).count()
    draft_structures = total_structures - active_structures

    total_assignments = db.query(EmployeeSalaryStructure).count()
    active_assignments = db.query(EmployeeSalaryStructure).filter(EmployeeSalaryStructure.is_active == True).count()
    pending_assignments = total_assignments - active_assignments

    total_components = db.query(SalaryComponent).count()
    active_components = db.query(SalaryComponent).filter(SalaryComponent.is_active == True).count()
    inactive_components = total_components - active_components

    return SalaryStructureKPIResponse(
        total_structures=total_structures,
        active_structures=active_structures,
        draft_structures=draft_structures,
        active_assignments=active_assignments,
        total_assignments=total_assignments,
        pending_assignments=pending_assignments,
        total_components=total_components,
        active_components=active_components,
        inactive_components=inactive_components,
    )


# ─────────────────────────────────────────────
# Export Components CSV  ← NEW (was missing)
# ─────────────────────────────────────────────

def export_components_csv(
    db: Session,
    structure_id: Optional[int] = None,
    component_type: Optional[str] = None,
) -> bytes:
    query = db.query(SalaryComponent)
    if structure_id:
        query = query.filter(SalaryComponent.structure_id == structure_id)
    if component_type:
        query = query.filter(SalaryComponent.component_type == component_type)

    components = query.order_by(SalaryComponent.sequence).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Code", "Name", "Type", "Calculation", "Value",
        "Depends On", "Taxable", "Status", "Sequence"
    ])
    for c in components:
        writer.writerow([
            c.code, c.name, c.component_type, c.calculation_type, c.value,
            c.depends_on or "", "Yes" if c.is_taxable else "No",
            "Active" if c.is_active else "Inactive", c.sequence,
        ])
    return buf.getvalue().encode("utf-8")


# ─────────────────────────────────────────────
# Salary Structure CRUD
# ─────────────────────────────────────────────

def create_salary_structure(db: Session, data: SalaryStructureCreate) -> SalaryStructure:
    existing = db.query(SalaryStructure).filter(SalaryStructure.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Salary structure with name '{data.name}' already exists."
        )
    structure = SalaryStructure(
        name=data.name,
        description=data.description,
        is_active=data.is_active,
    )
    db.add(structure)
    db.flush()  # get structure.id before adding components

    for comp_data in (data.components or []):
        component = SalaryComponent(structure_id=structure.id, **comp_data.model_dump())
        db.add(component)

    db.commit()
    db.refresh(structure)
    return structure


def get_salary_structure(db: Session, structure_id: int) -> SalaryStructure:
    structure = db.query(SalaryStructure).filter(SalaryStructure.id == structure_id).first()
    if not structure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Salary structure with id {structure_id} not found."
        )
    return structure


def get_all_salary_structures(
    db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None
) -> List[SalaryStructure]:
    query = db.query(SalaryStructure)
    if is_active is not None:
        query = query.filter(SalaryStructure.is_active == is_active)
    return query.offset(skip).limit(limit).all()


def update_salary_structure(
    db: Session, structure_id: int, data: SalaryStructureUpdate
) -> SalaryStructure:
    structure = get_salary_structure(db, structure_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(structure, key, value)
    db.commit()
    db.refresh(structure)
    return structure


def delete_salary_structure(db: Session, structure_id: int) -> dict:
    structure = get_salary_structure(db, structure_id)
    db.delete(structure)
    db.commit()
    return {"message": f"Salary structure '{structure.name}' deleted successfully."}


# ─────────────────────────────────────────────
# Salary Component CRUD
# ─────────────────────────────────────────────

def add_component_to_structure(
    db: Session, structure_id: int, data: SalaryComponentCreate
) -> SalaryComponent:
    get_salary_structure(db, structure_id)  # validate structure exists

    duplicate = db.query(SalaryComponent).filter(
        SalaryComponent.structure_id == structure_id,
        SalaryComponent.code == data.code
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Component with code '{data.code}' already exists in this structure."
        )

    component = SalaryComponent(structure_id=structure_id, **data.model_dump())
    db.add(component)
    db.commit()
    db.refresh(component)
    return component


def get_component(db: Session, component_id: int) -> SalaryComponent:
    component = db.query(SalaryComponent).filter(SalaryComponent.id == component_id).first()
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component with id {component_id} not found."
        )
    return component


def update_component(
    db: Session, component_id: int, data: SalaryComponentUpdate
) -> SalaryComponent:
    component = get_component(db, component_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(component, key, value)
    db.commit()
    db.refresh(component)
    return component


def delete_component(db: Session, component_id: int) -> dict:
    component = get_component(db, component_id)
    db.delete(component)
    db.commit()
    return {"message": f"Component '{component.name}' deleted successfully."}


def get_components_by_structure(
    db: Session, structure_id: int
) -> List[SalaryComponent]:
    get_salary_structure(db, structure_id)
    return (
        db.query(SalaryComponent)
        .filter(SalaryComponent.structure_id == structure_id)
        .order_by(SalaryComponent.sequence)
        .all()
    )


# ─────────────────────────────────────────────
# Employee Salary Structure Assignment
# ─────────────────────────────────────────────

def assign_structure_to_employee(
    db: Session, data: EmployeeSalaryStructureCreate
) -> EmployeeSalaryStructure:
    get_salary_structure(db, data.structure_id)

    # Deactivate any existing active assignment for this employee
    existing = db.query(EmployeeSalaryStructure).filter(
        EmployeeSalaryStructure.employee_id == data.employee_id,
        EmployeeSalaryStructure.is_active == True
    ).first()
    if existing:
        existing.is_active = False

    assignment = EmployeeSalaryStructure(**data.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def get_employee_salary_structure(
    db: Session, employee_id: int
) -> EmployeeSalaryStructure:
    assignment = db.query(EmployeeSalaryStructure).filter(
        EmployeeSalaryStructure.employee_id == employee_id,
        EmployeeSalaryStructure.is_active == True
    ).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active salary structure found for employee {employee_id}."
        )
    return assignment


def update_employee_salary_structure(
    db: Session, assignment_id: int, data: EmployeeSalaryStructureUpdate
) -> EmployeeSalaryStructure:
    assignment = db.query(EmployeeSalaryStructure).filter(
        EmployeeSalaryStructure.id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment with id {assignment_id} not found."
        )
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(assignment, key, value)
    db.commit()
    db.refresh(assignment)
    return assignment


def get_all_employee_assignments(
    db: Session, employee_id: int
) -> List[EmployeeSalaryStructure]:
    return db.query(EmployeeSalaryStructure).filter(
        EmployeeSalaryStructure.employee_id == employee_id
    ).order_by(EmployeeSalaryStructure.effective_from.desc()).all()


# ─────────────────────────────────────────────
# Salary Breakdown Calculation
# ─────────────────────────────────────────────

def calculate_salary_breakdown(
    db: Session, employee_id: int
) -> SalaryBreakdownResponse:
    assignment = get_employee_salary_structure(db, employee_id)
    structure = get_salary_structure(db, assignment.structure_id)

    components = (
        db.query(SalaryComponent)
        .filter(
            SalaryComponent.structure_id == structure.id,
            SalaryComponent.is_active == True
        )
        .order_by(SalaryComponent.sequence)
        .all()
    )

    computed: dict = {
        "BASIC": assignment.basic_salary,
        "CTC": assignment.ctc,
    }
    breakdown = []
    gross_earnings = 0.0
    total_deductions = 0.0

    for comp in components:
        amount = 0.0

        if comp.calculation_type == "fixed":
            amount = comp.value

        elif comp.calculation_type == "percentage":
            base_code = comp.depends_on or "BASIC"
            base_val = computed.get(base_code, 0.0)
            amount = (comp.value / 100) * base_val

        elif comp.calculation_type == "formula" and comp.formula:
            try:
                amount = float(eval(comp.formula, {"__builtins__": {}}, computed))
            except Exception:
                amount = 0.0

        computed[comp.code] = amount

        breakdown.append(ComponentBreakdown(
            code=comp.code,
            name=comp.name,
            component_type=comp.component_type,
            amount=round(amount, 2),
            is_taxable=comp.is_taxable,
        ))

        if comp.component_type == "earning":
            gross_earnings += amount
        elif comp.component_type in ("deduction", "statutory"):
            total_deductions += amount

    net_salary = assignment.basic_salary + gross_earnings - total_deductions

    return SalaryBreakdownResponse(
        employee_id=employee_id,
        structure_name=structure.name,
        ctc=assignment.ctc,
        basic_salary=assignment.basic_salary,
        gross_earnings=round(gross_earnings, 2),
        total_deductions=round(total_deductions, 2),
        net_salary=round(net_salary, 2),
        components=breakdown,
    )
