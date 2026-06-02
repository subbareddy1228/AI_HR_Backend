# app/schemas/asset_return.py

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class AssetReturnCreate(BaseModel):
    allocation_id: UUID
    return_reason: str
    condition_at_return: str
    missing_items: str | None = None
    damage_details: str | None = None


class AssetReturnResponse(BaseModel):
    id: UUID                # ✅ MUST be UUID
    allocation_id: UUID
    return_reason: str
    condition_at_return: str
    missing_items: str | None = None
    damage_details: str | None = None
    returned_at: datetime

    model_config = ConfigDict(from_attributes=True)
