from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CurrencySettingCreate(BaseModel):
    primary_currency: str
    secondary_currency: Optional[str]
    multi_currency_enabled: bool
    auto_update: bool
    update_frequency: Optional[str]

class ExchangeRateCreate(BaseModel):
    from_currency: str
    to_currency: str
    rate: float
    effective_date: datetime

class ExchangeRateUpdate(BaseModel):
    rate: float
    status: str
