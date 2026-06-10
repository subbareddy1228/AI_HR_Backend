from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

from core.database import Base, get_db


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    tenant_name = Column(String(255), unique=True, nullable=False)
    domain = Column(String(255), unique=True, nullable=True)
    db_schema = Column(String(100), unique=True, nullable=True)    # for schema-based isolation
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    plan = Column(String(50), default="BASIC")                     # BASIC | STANDARD | ENTERPRISE
    max_employees = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TenantCreate(BaseModel):
    tenant_name: str
    domain: Optional[str] = None
    db_schema: Optional[str] = None
    contact_email: str
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    plan: Optional[str] = "BASIC"
    max_employees: Optional[int] = 50


class TenantUpdate(BaseModel):
    tenant_name: Optional[str] = None
    domain: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    plan: Optional[str] = None
    max_employees: Optional[int] = None
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    id: int
    tenant_name: str
    domain: Optional[str]
    db_schema: Optional[str]
    contact_email: str
    contact_phone: Optional[str]
    address: Optional[str]
    plan: str
    max_employees: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/tenants", tags=["Super Admin"])


@router.post("/", response_model=TenantResponse, status_code=201)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    existing = db.query(Tenant).filter(Tenant.tenant_name == payload.tenant_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant already exists")
    tenant = Tenant(**payload.model_dump())
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/", response_model=List[TenantResponse])
def list_tenants(db: Session = Depends(get_db)):
    return db.query(Tenant).order_by(Tenant.created_at.desc()).all()


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/{tenant_id}", response_model=TenantResponse)
def update_tenant(tenant_id: int, payload: TenantUpdate, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tenant, key, value)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}")
def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.is_active = False
    db.commit()
    return {"message": f"Tenant '{tenant.tenant_name}' deactivated successfully"}
