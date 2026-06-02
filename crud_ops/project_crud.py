from sqlalchemy.orm import Session
from typing import List, Optional

from model.project import Project
from schema.project import ProjectCreate, ProjectUpdate


def get_project(db: Session, project_id: int) -> Optional[Project]:
    return db.query(Project).filter(Project.id == project_id).first()


def list_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
    return db.query(Project).offset(skip).limit(limit).all()


def create_project(db: Session, project: ProjectCreate) -> Project:
    db_obj = Project(
        client_id=project.client_id,
        name=project.name,
        start_date=project.start_date,
        end_date=project.end_date,
        description=project.description,
        active=project.active
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_project(db: Session, db_project: Project, updates: ProjectUpdate) -> Project:
    update_data = updates.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_project, field, value)

    db.commit()
    db.refresh(db_project)
    return db_project


def delete_project(db: Session, project_id: int):
    project = get_project(db, project_id)
    if project:
        db.delete(project)
        db.commit()
    return project
