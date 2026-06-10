from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, time, datetime


class AttendanceCreate(BaseModel):
    employee_id: int
    attendance_date: date
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    status: Optional[str] = "PRESENT"   
    remarks: Optional[str] = None


class AttendanceUpdate(BaseModel):
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    status: Optional[str] = None
    remarks: Optional[str] = None


class AttendanceOut(BaseModel):
    id: int
    employee_id: int
    attendance_date: date
    check_in: Optional[time]
    check_out: Optional[time]
    status: str
    remarks: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
