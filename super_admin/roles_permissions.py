from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

from core.database import Base, get_db



class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    permissions = Column(JSON, nullable=True)       
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserRoleAssignment(Base):
    """
    Maps a user to one of the custom roles defined above.

    Deliberately NOT the same as User.role (superadmin/company/recruiter/
    candidate/admin) in model/models.py — that field drives real
    authentication/access-control checks throughout the app
    (ProtectedRoute, require_roles, etc.) and must stay one of those 5
    fixed values. This table is a separate, additive layer for the
    fine-grained permission sets built on this page, so assigning a
    custom role here can never break login/auth elsewhere.
    """
    __tablename__ = "user_role_assignments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    role_id = Column(Integer, nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)


class RoleCreate(BaseModel):
    role_name: str
    description: Optional[str] = None
    permissions: Optional[dict] = None


class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[dict] = None
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    id: int
    role_name: str
    description: Optional[str]
    permissions: Optional[dict]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkAssignRequest(BaseModel):
    role_id: int
    user_ids: List[int]


class UserRoleAssignmentResponse(BaseModel):
    id: int
    user_id: int
    role_id: int
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/roles", tags=["Super Admin"])


@router.post("/", response_model=RoleResponse, status_code=201)
def create_role(payload: RoleCreate, db: Session = Depends(get_db)):
    existing = db.query(Role).filter(Role.role_name == payload.role_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role name already exists")
    role = Role(**payload.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/", response_model=List[RoleResponse])
def list_roles(db: Session = Depends(get_db)):
    return db.query(Role).filter(Role.is_active == True).all()


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(role_id: int, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, payload: RoleUpdate, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(role, key, value)
    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    role.is_active = False
    db.commit()
    return {"message": f"Role '{role.role_name}' deactivated successfully"}


# ---------------- USER <-> ROLE ASSIGNMENT ----------------

@router.post("/assign/bulk", response_model=List[UserRoleAssignmentResponse])
def bulk_assign_role(payload: BulkAssignRequest, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    created = []
    for user_id in payload.user_ids:
        existing = (
            db.query(UserRoleAssignment)
            .filter(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role_id == payload.role_id,
            )
            .first()
        )
        if existing:
            created.append(existing)
            continue
        assignment = UserRoleAssignment(user_id=user_id, role_id=payload.role_id)
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        created.append(assignment)

    return created


@router.get("/assign/by-role/{role_id}", response_model=List[UserRoleAssignmentResponse])
def list_assignments_for_role(role_id: int, db: Session = Depends(get_db)):
    return db.query(UserRoleAssignment).filter(UserRoleAssignment.role_id == role_id).all()


@router.get("/assign/by-user/{user_id}", response_model=List[UserRoleAssignmentResponse])
def list_assignments_for_user(user_id: int, db: Session = Depends(get_db)):
    return db.query(UserRoleAssignment).filter(UserRoleAssignment.user_id == user_id).all()


@router.delete("/assign/{assignment_id}")
def unassign_role(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.query(UserRoleAssignment).filter(UserRoleAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
    return {"message": "Role unassigned successfully"}
