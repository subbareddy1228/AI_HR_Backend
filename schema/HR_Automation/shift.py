from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import time, datetime


class ShiftBase(BaseModel):
    shift_name: str
    start_time: time
    end_time: time
    break_duration_minutes: Optional[int] = 30
    grace_period_minutes: Optional[int] = 10
    working_hours: int
    is_night_shift: Optional[bool] = False
    is_active: Optional[bool] = True


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(BaseModel):
    shift_name: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    break_duration_minutes: Optional[int] = None
    grace_period_minutes: Optional[int] = None
    working_hours: Optional[int] = None
    is_night_shift: Optional[bool] = None
    is_active: Optional[bool] = None


class ShiftResponse(ShiftBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
