

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator



AssetStatus = Literal["AVAILABLE", "ALLOCATED", "UNDER_MAINTENANCE", "RETIRED"]
AssetCondition = Literal["New", "Good", "Fair", "Poor"]
DepreciationMethod = Literal["Straight Line", "Declining Balance", "Written-Down-Value"]




class AssetBase(BaseModel):
    asset_name:          str  = Field(..., min_length=1, max_length=255)
    category:            str  = Field(..., min_length=1, max_length=100)
    make:                str  = Field(..., min_length=1, max_length=100)
    model:               str  = Field(..., min_length=1, max_length=150)
    serial_number:       str  = Field(..., min_length=1, max_length=120)

    purchase_date:       date
    purchase_price:      Decimal = Field(..., gt=0, decimal_places=2)

    depreciation_rate:   int     = Field(..., ge=0, le=100, description="Percentage per year")
    depreciation_method: DepreciationMethod = "Straight Line"
    useful_life_years:   Optional[int] = Field(None, gt=0, le=50)

    condition:           AssetCondition
    location:            str = Field(..., min_length=1, max_length=150)
    department:          str = Field(..., min_length=1, max_length=150)

    warranty_until:      Optional[date] = None
    notes:               Optional[str]  = None

    @field_validator("warranty_until")
    @classmethod
    def warranty_after_purchase(cls, v: Optional[date], info) -> Optional[date]:
        if v and "purchase_date" in info.data and v < info.data["purchase_date"]:
            raise ValueError("warranty_until must be on or after purchase_date")
        return v


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    
    asset_name:          Optional[str]               = None
    category:            Optional[str]               = None
    make:                Optional[str]               = None
    model:               Optional[str]               = None

    purchase_price:      Optional[Decimal]           = Field(None, gt=0, decimal_places=2)
    depreciation_rate:   Optional[int]               = Field(None, ge=0, le=100)
    depreciation_method: Optional[DepreciationMethod]= None
    useful_life_years:   Optional[int]               = Field(None, gt=0, le=50)

    condition:           Optional[AssetCondition]    = None
    location:            Optional[str]               = None
    department:          Optional[str]               = None
    warranty_until:      Optional[date]              = None
    notes:               Optional[str]               = None
    status:              Optional[AssetStatus]       = None


class AssetResponse(AssetBase):
    id:         int
    status:     AssetStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




class DepreciationScheduleItem(BaseModel):
    
    asset_id:            int
    asset_name:          str
    serial_number:       str
    purchase_price:      Decimal
    depreciation_rate:   int
    depreciation_method: str
    useful_life_years:   Optional[int]


    current_value:        Decimal
    yearly_depreciation:  Decimal
    accumulated:          Decimal
    net_book_value:       Decimal
    next_calculation_date: Optional[date]

    model_config = ConfigDict(from_attributes=True)



class AssetDashboardStats(BaseModel):
    total_assets:       int
    allocated:          int
    available:          int
    under_repair:       int
    retired:            int
    pending_returns:    int
    upcoming_maintenance: int
    expiring_insurance: int
    total_asset_value:  Decimal
    utilization_rate:   float   




class AssetReportRow(BaseModel):
    asset_id:        int
    asset_name:      str
    category:        str
    serial_number:   str
    status:          str
    condition:       str
    department:      str
    location:        str
    purchase_price:  Decimal
    current_value:   Decimal
    allocated_to:    Optional[str]
    warranty_until:  Optional[date]

    model_config = ConfigDict(from_attributes=True)
