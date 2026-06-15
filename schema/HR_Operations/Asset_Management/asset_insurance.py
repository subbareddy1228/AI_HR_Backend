"""
Asset Insurance Pydantic Schemas
Covers: Insurance tab — Policy ID, Asset Details, Provider, Policy Number,
Coverage Amount, Premium, Coverage Type, Validity, Claims, Status, Actions.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CoverageType     = Literal[
    "Comprehensive", "Third-Party", "Fire & Theft", "All-Risk", "Extended Warranty"
]
InsuranceStatus  = Literal["Active", "Expired", "Cancelled", "Claim Filed"]


class AssetInsuranceCreate(BaseModel):
    asset_id:           int          = Field(..., gt=0)
    insurance_provider: str          = Field(..., min_length=1, max_length=150)
    policy_number:      str          = Field(..., min_length=1, max_length=150)
    coverage_amount:    Decimal      = Field(..., gt=0, decimal_places=2)
    premium_amount:     Decimal      = Field(..., gt=0, decimal_places=2)
    coverage_type:      CoverageType = "Comprehensive"
    start_date:         date
    end_date:           date

    @model_validator(mode="after")
    def end_after_start(self) -> "AssetInsuranceCreate":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class AssetInsuranceUpdate(BaseModel):
    insurance_provider: Optional[str]            = None
    coverage_amount:    Optional[Decimal]        = Field(None, gt=0, decimal_places=2)
    premium_amount:     Optional[Decimal]        = Field(None, gt=0, decimal_places=2)
    coverage_type:      Optional[CoverageType]   = None
    end_date:           Optional[date]           = None
    claims_count:       Optional[int]            = Field(None, ge=0)
    claims_amount:      Optional[Decimal]        = Field(None, ge=0, decimal_places=2)
    claims_notes:       Optional[str]            = None
    status:             Optional[InsuranceStatus]= None


class AssetInsuranceResponse(BaseModel):
    id:                 int
    asset_id:           int
    insurance_provider: str
    policy_number:      str
    coverage_amount:    Decimal
    premium_amount:     Decimal
    coverage_type:      str
    start_date:         date
    end_date:           date
    claims_count:       int
    claims_amount:      Decimal
    claims_notes:       Optional[str]
    status:             str
    created_at:         datetime
    updated_at:         datetime

    model_config = ConfigDict(from_attributes=True)
