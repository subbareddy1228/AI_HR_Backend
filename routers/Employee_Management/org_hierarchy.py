# FILE 10 of 12 | routers/Employee_Management/org_hierarchy.py
# Router: Departments — prefix: /departments
# Endpoints: POST /  GET /  GET /tree  GET /{dept_id}  PUT /{dept_id}  DELETE /{dept_id}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

from core.database import get_db
from model.Employee_Management.org_hierarchy import Department
from schema.Employee_Management.org_hierarchy import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentTree,
)

router = APIRouter(prefix="/departments", tags=["Employee Management"])


def build_tree(departments: list, parent_id=None) -> List[DepartmentTree]:
    tree = []
    for dept in departments:
        if dept.parent_department_id == parent_id:
            node = DepartmentTree.model_validate(dept)
            node.children = build_tree(departments, parent_id=dept.id)
            tree.append(node)
    return tree


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
    obj = Department(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/", response_model=list[DepartmentResponse])
def list_departments(db: Session = Depends(get_db)):
    return db.execute(select(Department)).scalars().all()


@router.get("/tree", response_model=list[DepartmentTree])
def get_department_tree(db: Session = Depends(get_db)):
    all_depts = db.execute(select(Department)).scalars().all()
    return build_tree(all_depts, parent_id=None)


@router.get("/{dept_id}", response_model=DepartmentResponse)
def get_department(dept_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(Department).where(Department.id == dept_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Department not found")
    return obj


@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(dept_id: int, payload: DepartmentUpdate, db: Session = Depends(get_db)):
    obj = db.execute(
        select(Department).where(Department.id == dept_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Department not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(Department).where(Department.id == dept_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Department not found")
    db.delete(obj)
    db.commit()
