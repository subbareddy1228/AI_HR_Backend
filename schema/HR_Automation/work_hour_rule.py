from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class WorkHourRuleBase(BaseModel):
    rule_name: str
    daily_hours: Optional[float] = 8.0
    weekly_hours: Optional[float] = 40.0
    overtime_threshold_daily: Optional[float] = 8.0
    overtime_multiplier: Optional[float] = 1.5
    work_days: Optional[str] = "MON,TUE,WED,THU,FRI"
    half_day_hours: Optional[float] = 4.0
    min_hours_for_full_day: Optional[float] = 6.0
    min_hours_for_half_day: Optional[float] = 3.0
    is_active: Optional[bool] = True


class WorkHourRuleCreate(WorkHourRuleBase):
    pass


class WorkHourRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    daily_hours: Optional[float] = None
    weekly_hours: Optional[float] = None
    overtime_threshold_daily: Optional[float] = None
    overtime_multiplier: Optional[float] = None
    work_days: Optional[str] = None
    half_day_hours: Optional[float] = None
    min_hours_for_full_day: Optional[float] = None
    min_hours_for_half_day: Optional[float] = None
    is_active: Optional[bool] = None


class WorkHourRuleResponse(WorkHourRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
