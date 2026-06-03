# from fastapi import APIRouter

# router = APIRouter()





# routers/Employee_Management/org_hierarchy.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from model.Employee_Management.org_hierarchy import Department
from schema.Employee_Management.org_hierarchy import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentTree,
)

router = APIRouter(prefix="/api/org-hierarchy", tags=["Org Hierarchy"])


# ── Tree builder ──────────────────────────────────────────────────────────────

def _build_tree(dept: Department, dept_map: dict) -> DepartmentTree:
    node = DepartmentTree.model_validate(dept)
    for child in dept_map.get(dept.id, []):
        node.children.append(_build_tree(child, dept_map))
    return node


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/departments", response_model=DepartmentResponse, status_code=201)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    existing = db.execute(
        select(Department).where(Department.name == payload.name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Department '{payload.name}' already exists.")

    if payload.parent_department_id:
        parent = db.get(Department, payload.parent_department_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent department not found.")

    obj = Department(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/departments", response_model=List[DepartmentResponse])
def list_departments(
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Department)
    if is_active is not None:
        stmt = stmt.where(Department.is_active == is_active)
    return db.execute(stmt).scalars().all()


# ── Get by ID ─────────────────────────────────────────────────────────────────

@router.get("/departments/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = db.get(Department, department_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Department not found.")
    return obj


# ── Update ────────────────────────────────────────────────────────────────────

@router.put("/departments/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    obj = db.get(Department, department_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Department not found.")
    if payload.parent_department_id and payload.parent_department_id == department_id:
        raise HTTPException(status_code=400, detail="A department cannot be its own parent.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/departments/{department_id}", status_code=204)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    obj = db.get(Department, department_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Department not found.")
    children = db.execute(
        select(func.count()).where(Department.parent_department_id == department_id)
    ).scalar_one()
    if children > 0:
        raise HTTPException(status_code=400, detail="Cannot delete a department that has sub-departments.")
    db.delete(obj)
    db.commit()


# ── Full Org Tree ─────────────────────────────────────────────────────────────

@router.get("/tree", response_model=List[DepartmentTree])
def get_org_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    all_depts = db.execute(
        select(Department).where(Department.is_active == True)
    ).scalars().all()

    dept_map = {}
    roots = []
    for d in all_depts:
        if d.parent_department_id is None:
            roots.append(d)
        else:
            dept_map.setdefault(d.parent_department_id, []).append(d)

    return [_build_tree(r, dept_map) for r in roots]


# ── Sub-tree from a department ────────────────────────────────────────────────

@router.get("/tree/{department_id}", response_model=DepartmentTree)
def get_dept_subtree(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    root = db.get(Department, department_id)
    if not root:
        raise HTTPException(status_code=404, detail="Department not found.")

    all_depts = db.execute(
        select(Department).where(Department.is_active == True)
    ).scalars().all()

    dept_map = {}
    for d in all_depts:
        if d.parent_department_id is not None:
            dept_map.setdefault(d.parent_department_id, []).append(d)

    return _build_tree(root, dept_map)