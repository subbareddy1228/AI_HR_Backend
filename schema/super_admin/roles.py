# schema/super_admin/roles.py
# Pydantic schemas for Role management

from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime


class RoleBase(BaseModel):
    role_name: str
    description: Optional[str] = None
    permissions: Optional[Dict[str, List[str]]] = None  # {"module": ["read","write","delete"]}


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
