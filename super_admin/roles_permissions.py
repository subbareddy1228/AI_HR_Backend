from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

from core.database import Base, get_db


# ── Model ──────────────────────────────────────────────────────────────────────
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    permissions = Column(JSON, nullable=True)       # {"module": ["read","write","delete"]}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Schemas ────────────────────────────────────────────────────────────────────
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


# ── Router ─────────────────────────────────────────────────────────────────────
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
