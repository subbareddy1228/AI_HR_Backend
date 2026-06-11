

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


WEEK_DAYS    = {"Monday", "Sunday", "Saturday"}
TIME_FORMATS = {"12-hour (hh:mm AM/PM)", "24-hour (HH:mm)", "12-hour", "24-hour"}


class LocalizationCreate(BaseModel):
    default_language:   str
    default_timezone:   str
    date_format:        str     
    time_format:        str
    number_format:      str   
    decimal_places:     int     = 2
    currency_format:    str  
    first_day_of_week:  str

    @field_validator("decimal_places")
    @classmethod
    def validate_decimal(cls, v):
        if v < 0 or v > 6:
            raise ValueError("decimal_places must be between 0 and 6")
        return v

    @field_validator("first_day_of_week")
    @classmethod
    def validate_week_start(cls, v):
        if v not in WEEK_DAYS:
            raise ValueError(f"first_day_of_week must be one of {WEEK_DAYS}")
        return v


class LocalizationUpdate(LocalizationCreate):
    default_language:  Optional[str] = None
    default_timezone:  Optional[str] = None
    date_format:       Optional[str] = None
    time_format:       Optional[str] = None
    number_format:     Optional[str] = None
    decimal_places:    Optional[int] = None
    currency_format:   Optional[str] = None
    first_day_of_week: Optional[str] = None


class LocalizationResponse(LocalizationCreate):
    id:         int
    tenant_id:  int
    is_active:  bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
