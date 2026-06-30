

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


MaintenanceType   = Literal["Preventive", "Corrective", "Emergency", "Inspection"]
MaintenanceStatus = Literal["Scheduled", "In Progress", "Completed", "Cancelled"]


class AssetMaintenanceCreate(BaseModel):
    asset_id:         int             = Field(..., gt=0)
    maintenance_type: MaintenanceType
    maintenance_date: datetime
    cost:             Decimal         = Field(..., ge=0, decimal_places=2)
    performed_by:     str             = Field(..., min_length=1, max_length=255)
    description:      str             = Field(..., min_length=1)
    warranty_until:   Optional[date]  = None
    next_due_date:    Optional[date]  = None
    status:           MaintenanceStatus = "Completed"

    @field_validator("warranty_until")
    @classmethod
    def warranty_after_maintenance(cls, v: Optional[date], info) -> Optional[date]:
        if v and "maintenance_date" in info.data:
            maint_date = info.data["maintenance_date"]
            maint_date_only = maint_date.date() if hasattr(maint_date, "date") else maint_date
            if v < maint_date_only:
                raise ValueError("warranty_until must be on or after maintenance_date")
        return v

    @field_validator("next_due_date")
    @classmethod
    def next_due_in_future(cls, v: Optional[date], info) -> Optional[date]:
        if v and "maintenance_date" in info.data:
            maint_date = info.data["maintenance_date"]
            maint_date_only = maint_date.date() if hasattr(maint_date, "date") else maint_date
            if v <= maint_date_only:
                raise ValueError("next_due_date must be after maintenance_date")
        return v


class AssetMaintenanceUpdate(BaseModel):
    maintenance_type: Optional[MaintenanceType]   = None
    maintenance_date: Optional[datetime]           = None
    cost:             Optional[Decimal]            = Field(None, ge=0, decimal_places=2)
    performed_by:     Optional[str]               = None
    description:      Optional[str]               = None
    warranty_until:   Optional[date]              = None
    next_due_date:    Optional[date]              = None
    status:           Optional[MaintenanceStatus] = None


class AssetMaintenanceResponse(BaseModel):
    id:               UUID
    asset_id:         int
    maintenance_type: str
    maintenance_date: datetime
    cost:             Decimal
    performed_by:     str
    description:      str
    warranty_until:   Optional[date]
    next_due_date:    Optional[date]
    status:           str
    created_at:       datetime

    model_config = ConfigDict(from_attributes=True)
