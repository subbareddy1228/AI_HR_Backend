from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime

from core.database import Base, get_db
from super_admin.roles_permissions import Role
from model.models import User


class RoleAssignment(Base):
    __tablename__ = "role_assignments"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)


class BulkAssignRequest(BaseModel):
    role_id: int
    user_ids: List[int]


class RoleAssignmentResponse(BaseModel):
    id: int
    role_id: int
    user_id: int
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/roles/assign", tags=["Super Admin"])


@router.post("/bulk", response_model=List[RoleAssignmentResponse], status_code=201)
def bulk_assign_role(payload: BulkAssignRequest, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    created = []
    for user_id in payload.user_ids:
        user = db.get(User, user_id)
        if not user:
            continue

        existing = (
            db.query(RoleAssignment)
            .filter(RoleAssignment.role_id == payload.role_id, RoleAssignment.user_id == user_id)
            .first()
        )
        if existing:
            continue

        assignment = RoleAssignment(role_id=payload.role_id, user_id=user_id)
        db.add(assignment)
        created.append(assignment)

    db.commit()
    for a in created:
        db.refresh(a)
    return created


@router.get("/by-role/{role_id}", response_model=List[RoleAssignmentResponse])
def get_assignments_by_role(role_id: int, db: Session = Depends(get_db)):
    return db.query(RoleAssignment).filter(RoleAssignment.role_id == role_id).all()


@router.get("/by-user/{user_id}", response_model=List[RoleAssignmentResponse])
def get_assignments_by_user(user_id: int, db: Session = Depends(get_db)):
    return db.query(RoleAssignment).filter(RoleAssignment.user_id == user_id).all()


@router.delete("/{assignment_id}")
def unassign_role(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.get(RoleAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
    return {"message": "Role unassigned successfully"}