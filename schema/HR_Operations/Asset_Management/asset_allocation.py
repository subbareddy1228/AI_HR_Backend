# app/schemas/asset_allocation.py

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class AssetAllocationCreate(BaseModel):
    asset_id: int
    employee_id: str
    employee_name: str
    department: str
    allocation_type: str
    allocation_reason: str


class AssetAllocationResponse(BaseModel):
    id: UUID  # ✅ FIXED — allocation id is UUID
    asset_id: int
    employee_id: str
    employee_name: str
    department: str
    allocation_type: str
    allocation_reason: str
    allocated_at: datetime

    model_config = ConfigDict(from_attributes=True)
