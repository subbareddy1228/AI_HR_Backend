# schema/super_admin/tenant.py
# Pydantic schemas for multi-tenant management

from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime


class TenantBase(BaseModel):
    tenant_name: str
    domain: Optional[str] = None
    db_schema: Optional[str] = None
    contact_email: str
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    plan: Optional[str] = "BASIC"         # BASIC | STANDARD | ENTERPRISE
    max_employees: Optional[int] = 50


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    tenant_name: Optional[str] = None
    domain: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    plan: Optional[str] = None
    max_employees: Optional[int] = None
    is_active: Optional[bool] = None


class TenantResponse(TenantBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
