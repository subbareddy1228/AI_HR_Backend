

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


MONTHS = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

PERIOD_TYPES = {"Fiscal Year", "Calendar Year", "52-Week Year"}
TAX_ALIGNMENTS = {"Calendar Year", "Fiscal Year", "Custom"}


class FinancialYearCreate(BaseModel):
    start_month:        str
    start_day:          int
    end_month:          str
    end_day:            int
    period_type:        str
    tax_year_alignment: str

    @field_validator("start_month", "end_month")
    @classmethod
    def validate_month(cls, v):
        if v not in MONTHS:
            raise ValueError(f"Month must be one of {MONTHS}")
        return v

    @field_validator("start_day", "end_day")
    @classmethod
    def validate_day(cls, v):
        if v < 1 or v > 31:
            raise ValueError("Day must be between 1 and 31")
        return v

    @field_validator("period_type")
    @classmethod
    def validate_period(cls, v):
        if v not in PERIOD_TYPES:
            raise ValueError(f"period_type must be one of {PERIOD_TYPES}")
        return v


class FinancialYearResponse(FinancialYearCreate):
    id:             int
    tenant_id:      int
    current_year:   str
    previous_year:  str
    next_year:      str
    is_active:      bool
    created_at:     datetime
    updated_at:     datetime

    model_config = {"from_attributes": True}
