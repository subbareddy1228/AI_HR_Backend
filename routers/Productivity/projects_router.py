from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from model.Productivity.project import Project as ProjectModel
from schema.Productivity.projects import Project as ProjectSchema, ProjectCreate,ProjectUpdate
from core.database import get_db

router = APIRouter(
    prefix="/projectmanagement",
    tags=["Project Management"]
)

@router.post("/", response_model=ProjectSchema)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db)
):
    new_project = ProjectModel(**project.dict())
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("/", response_model=List[ProjectSchema])
def get_projects(db: Session = Depends(get_db)):
    return db.query(ProjectModel).all()

@router.patch("/{project_id}", response_model=ProjectSchema)
def update_project(
    project_id: int,
    request: ProjectUpdate,
    db: Session = Depends(get_db)
):
    print(request)
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    #  What client actually sent
    payload = request.dict(exclude_unset=True)
    print("PATCH payload from client:", payload)

    for key, value in payload.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}
