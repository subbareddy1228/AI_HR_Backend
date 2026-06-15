"""
Asset Return Pydantic Schemas
Covers: Returns tab — Return ID, Asset Details, Employee Details, Return Date,
Reason, Condition, Penalty, Certificate, Status, Actions.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ReturnCondition = Literal["Good", "Damaged", "Missing Parts", "Beyond Repair"]
ReturnStatus    = Literal["Pending", "Processed", "Disputed"]


class AssetReturnCreate(BaseModel):
    allocation_id:       UUID
    return_reason:       str            = Field(..., min_length=1, max_length=255)
    condition_at_return: ReturnCondition
    missing_items:       Optional[str]  = None
    damage_details:      Optional[str]  = None
    penalty_amount:      Decimal        = Field(default=Decimal("0"), ge=0, decimal_places=2)
    penalty_reason:      Optional[str]  = None


class AssetReturnUpdate(BaseModel):
    """Used to issue certificate or update status."""
    status:                Optional[ReturnStatus] = None
    certificate_issued:    Optional[bool]         = None
    certificate_issued_at: Optional[datetime]     = None
    certificate_issued_by: Optional[str]          = None
    penalty_amount:        Optional[Decimal]      = Field(None, ge=0, decimal_places=2)
    penalty_reason:        Optional[str]          = None


class AssetReturnResponse(BaseModel):
    id:                    UUID
    allocation_id:         UUID
    return_reason:         str
    condition_at_return:   str
    missing_items:         Optional[str]
    damage_details:        Optional[str]
    penalty_amount:        Decimal
    penalty_reason:        Optional[str]
    certificate_issued:    bool
    certificate_issued_at: Optional[datetime]
    certificate_issued_by: Optional[str]
    status:                str
    returned_at:           datetime

    model_config = ConfigDict(from_attributes=True)
