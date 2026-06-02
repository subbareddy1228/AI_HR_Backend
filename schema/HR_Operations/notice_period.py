from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional


class NoticePeriodCreate(BaseModel):
    employee_id: int
    notice_start_date: date
    notice_end_date: date
    notice_period_days: int
    waiver_requested: Optional[str] = "NO"
    buyout_amount: Optional[int] = None
    remarks: Optional[str] = None


class NoticePeriodUpdate(BaseModel):
    last_working_date: Optional[date] = None
    serving_days: Optional[int] = None
    waiver_requested: Optional[str] = None
    waiver_approved: Optional[str] = None
    buyout_amount: Optional[int] = None
    status: Optional[str] = None
    remarks: Optional[str] = None


class NoticePeriodResponse(BaseModel):
    id: int
    employee_id: int
    notice_start_date: date
    notice_end_date: date
    notice_period_days: int
    serving_days: Optional[int]
    waiver_requested: str
    waiver_approved: str
    buyout_amount: Optional[int]
    status: str
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
