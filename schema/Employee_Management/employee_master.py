# FILE 4 of 12 | schema/Employee_Management/employee_master.py
# Schemas: EmployeeMasterBase, EmployeeMasterCreate, EmployeeMasterUpdate, EmployeeMasterResponse

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class EmployeeMasterBase(BaseModel):
    employee_id: int
    employment_type: str  # Full-Time/Part-Time/Contract/Intern
    probation_end_date: Optional[date] = None
    confirmed_date: Optional[date] = None
    reporting_manager_id: Optional[int] = None
    work_location: Optional[str] = None
    employment_status: Optional[str] = "Active"  # Active/Inactive/On Leave/Resigned/Terminated
    notice_period_days: Optional[int] = 30


class EmployeeMasterCreate(EmployeeMasterBase):
    pass


class EmployeeMasterUpdate(BaseModel):
    employment_type: Optional[str] = None
    probation_end_date: Optional[date] = None
    confirmed_date: Optional[date] = None
    reporting_manager_id: Optional[int] = None
    work_location: Optional[str] = None
    employment_status: Optional[str] = None
    notice_period_days: Optional[int] = None


class EmployeeMasterResponse(EmployeeMasterBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
