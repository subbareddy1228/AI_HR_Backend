

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


VALID_FREQUENCIES = {"Daily", "Weekly", "Monthly"}
VALID_STATUSES    = {"active", "inactive"}


class CurrencySettingCreate(BaseModel):
    primary_currency:       str
    secondary_currency:     Optional[str]   = None
    multi_currency_enabled: bool            = False
    auto_update:            bool            = False
    update_frequency:       Optional[str]   = None

    @field_validator("update_frequency")
    @classmethod
    def check_frequency(cls, v):
        if v and v not in VALID_FREQUENCIES:
            raise ValueError(f"update_frequency must be one of {VALID_FREQUENCIES}")
        return v


class CurrencySettingResponse(CurrencySettingCreate):
    id:             int
    tenant_id:      int
    last_updated:   datetime
    exchange_rates: List["ExchangeRateResponse"] = []

    model_config = {"from_attributes": True}


class ExchangeRateCreate(BaseModel):
    from_currency:  str
    to_currency:    str
    rate:           float
    effective_date: datetime

    @field_validator("rate")
    @classmethod
    def rate_positive(cls, v):
        if v <= 0:
            raise ValueError("Exchange rate must be positive")
        return v


class ExchangeRateUpdate(BaseModel):
    rate:   Optional[float]  = None
    status: Optional[str]    = None

    @field_validator("status")
    @classmethod
    def check_status(cls, v):
        if v and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v


class ExchangeRateResponse(ExchangeRateCreate):
    id:           int
    tenant_id:    int
    status:       str
    last_updated: datetime

    model_config = {"from_attributes": True}



CurrencySettingResponse.model_rebuild()
