from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from core.session import get_db
import crud_ops.crud

from schema.project import (ProjectCreate,ProjectUpdate,ProjectOut)

from crud_ops.project_crud import (create_project,list_projects,get_project,update_project,delete_project)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project_route(project_in: ProjectCreate, db: Session = Depends(get_db)):
    return create_project(db, project_in)


@router.get("/", response_model=List[ProjectOut])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return list_projects(db, skip, limit)


@router.get("/{project_id}", response_model=ProjectOut)
def read_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project

@router.patch("/{project_id}", response_model=ProjectOut)
def update_project_route(project_id: int, project_in: ProjectUpdate, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return update_project(db, project, project_in)


@router.delete("/{project_id}", response_model=ProjectOut)
def delete_project_route(project_id: int, db: Session = Depends(get_db)):
    project = delete_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project
