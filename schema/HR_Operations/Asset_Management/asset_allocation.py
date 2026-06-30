

from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


AllocationType   = Literal["Permanent", "Temporary", "Project-Based"]
AllocationStatus = Literal["Active", "Returned", "Transferred"]


class AssetAllocationCreate(BaseModel):
    asset_id:          int    = Field(..., gt=0)
    employee_id:       str    = Field(..., min_length=1, max_length=50)
    employee_name:     str    = Field(..., min_length=1, max_length=255)
    department:        str    = Field(..., min_length=1, max_length=150)
    allocation_type:   AllocationType
    allocation_reason: str    = Field(..., min_length=1)
    approved_by:       Optional[str]  = None
    insurance_covered: bool           = False


class AssetAllocationUpdate(BaseModel):
    approved_by:       Optional[str]            = None
    approved_at:       Optional[datetime]        = None
    insurance_covered: Optional[bool]            = None
    status:            Optional[AllocationStatus]= None


class AssetAllocationResponse(BaseModel):
    id:                UUID
    asset_id:          int
    employee_id:       str
    employee_name:     str
    department:        str
    allocation_type:   str
    allocation_reason: str
    approved_by:       Optional[str]
    approved_at:       Optional[datetime]
    insurance_covered: bool
    status:            str
    allocated_at:      datetime
    updated_at:        datetime

    model_config = ConfigDict(from_attributes=True)
