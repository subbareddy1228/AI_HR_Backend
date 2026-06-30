from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import date, datetime


class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type: str             
    start_date: date
    end_date: date
    is_half_day: Optional[bool] = False
    reason: Optional[str] = None

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date cannot be before start_date")
        return v


class LeaveRequestUpdate(BaseModel):
    
    status: Optional[str] = None        
    approved_by: Optional[int] = None
    rejection_reason: Optional[str] = None


class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    leave_type: str
    leave_type_code: str
    start_date: date
    end_date: date
    days: float
    is_half_day: bool
    reason: Optional[str] = None
    status: str
    approved_by: Optional[int] = None
    approved_by_name: Optional[str] = None
    rejection_reason: Optional[str] = None
    applied_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaveApplicationsListResponse(BaseModel):
    applications: list[LeaveRequestOut]
    total: int
