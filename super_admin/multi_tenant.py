from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

from core.database import Base, get_db
from core.dependencies import require_roles


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

    status = Column(String(20), default="active")                  # active | pending | suspended | inactive
    company_size = Column(String(20), nullable=True)                # Small | Medium | Large | Enterprise
    primary_color = Column(String(20), default="#1890ff")
    logo_url = Column(Text, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    data_usage = Column(String(20), default="0%")
    last_active = Column(DateTime, nullable=True)
    tenant_context = Column(String(255), nullable=True)
    schema_type = Column(String(20), default="shared")              # shared | separate
    data_retention_period = Column(Integer, default=7)               # years
    performance_tier = Column(String(20), default="standard")
    billing_enabled = Column(Boolean, default=False)
    sso_enabled = Column(Boolean, default=False)


class TenantCreate(BaseModel):
    tenant_name: str
    domain: Optional[str] = None
    db_schema: Optional[str] = None
    contact_email: str
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    plan: Optional[str] = "BASIC"
    max_employees: Optional[int] = 50
    status: Optional[str] = "active"
    company_size: Optional[str] = None
    primary_color: Optional[str] = "#1890ff"
    logo_url: Optional[str] = None
    trial_ends_at: Optional[datetime] = None
    data_usage: Optional[str] = "0%"
    last_active: Optional[datetime] = None
    tenant_context: Optional[str] = None
    schema_type: Optional[str] = "shared"
    data_retention_period: Optional[int] = 7
    performance_tier: Optional[str] = "standard"
    billing_enabled: Optional[bool] = False
    sso_enabled: Optional[bool] = False


class TenantUpdate(BaseModel):
    tenant_name: Optional[str] = None
    domain: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    plan: Optional[str] = None
    max_employees: Optional[int] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    company_size: Optional[str] = None
    primary_color: Optional[str] = None
    logo_url: Optional[str] = None
    trial_ends_at: Optional[datetime] = None
    data_usage: Optional[str] = None
    last_active: Optional[datetime] = None
    tenant_context: Optional[str] = None
    schema_type: Optional[str] = None
    data_retention_period: Optional[int] = None
    performance_tier: Optional[str] = None
    billing_enabled: Optional[bool] = None
    sso_enabled: Optional[bool] = None


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
    status: str
    company_size: Optional[str]
    primary_color: Optional[str]
    logo_url: Optional[str]
    trial_ends_at: Optional[datetime]
    data_usage: Optional[str]
    last_active: Optional[datetime]
    tenant_context: Optional[str]
    schema_type: Optional[str]
    data_retention_period: Optional[int]
    performance_tier: Optional[str]
    billing_enabled: Optional[bool]
    sso_enabled: Optional[bool]

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


@router.get("/{tenant_id}/locations")
def list_tenant_locations(
    tenant_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(["superadmin"])),
):
    """
    Superadmin-only: list the branches (CompanyLocation rows) belonging to
    a specific tenant. Needed because the regular
    /company-settings/locations endpoint always scopes to the *caller's own*
    tenant_id — a superadmin has no tenant_id, so it can never be used to
    browse another company's branches. This is what powers the branch
    picker in Super Admin -> User Management when assigning a branch admin.
    """
    from model.Company_Settings.location import CompanyLocation
    locations = (
        db.query(CompanyLocation)
        .filter(CompanyLocation.tenant_id == tenant_id, CompanyLocation.is_active.is_(True))
        .order_by(CompanyLocation.is_default.desc(), CompanyLocation.name)
        .all()
    )
    return [
        {"id": loc.id, "name": loc.name, "is_default": loc.is_default}
        for loc in locations
    ]


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