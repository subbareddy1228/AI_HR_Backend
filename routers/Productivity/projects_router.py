from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from model.Productivity.productivity import Productivity as ProjectModel
from schema.Productivity.projects import Project as ProjectSchema, ProjectCreate, ProjectUpdate
from core.database import get_db

router = APIRouter(
    prefix="/projectmanagement",
    tags=["ProductivityProject Management"]
)

@router.post("/", response_model=ProjectSchema)
def create_project(
    ProductivityProject: ProjectCreate,
    db: Session = Depends(get_db)
):
    new_project = ProjectModel(**ProductivityProject.dict())
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
    ProductivityProject = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()

    if not ProductivityProject:
        raise HTTPException(status_code=404, detail="ProductivityProject not found")

    #  What client actually sent
    payload = request.dict(exclude_unset=True)
    print("PATCH payload from client:", payload)

    for key, value in payload.items():
        setattr(ProductivityProject, key, value)

    db.commit()
    db.refresh(ProductivityProject)
    return ProductivityProject


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    ProductivityProject = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not ProductivityProject:
        raise HTTPException(status_code=404, detail="ProductivityProject not found")

    db.delete(ProductivityProject)
    db.commit()
    return {"message": "ProductivityProject deleted successfully"}
