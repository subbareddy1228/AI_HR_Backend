# app/schemas/asset_maintenance.py

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class AssetMaintenanceCreate(BaseModel):
    asset_id: int
    maintenance_type: str
    maintenance_date: datetime
    cost: float
    performed_by: str
    description: str


class AssetMaintenanceResponse(BaseModel):
    id: UUID              
    asset_id: int
    maintenance_type: str
    maintenance_date: datetime
    cost: float
    performed_by: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}
