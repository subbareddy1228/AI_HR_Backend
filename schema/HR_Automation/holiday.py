from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class HolidayBase(BaseModel):
    holiday_name: str
    holiday_date: date
    holiday_type: str           # NATIONAL | REGIONAL | OPTIONAL | RESTRICTED
    description: Optional[str] = None
    applicable_location: Optional[str] = None
    is_active: Optional[bool] = True


class HolidayCreate(HolidayBase):
    pass


class HolidayUpdate(BaseModel):
    holiday_name: Optional[str] = None
    holiday_date: Optional[date] = None
    holiday_type: Optional[str] = None
    description: Optional[str] = None
    applicable_location: Optional[str] = None
    is_active: Optional[bool] = None


class HolidayResponse(HolidayBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
