from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional


class EmployeeConfirmationCreate(BaseModel):
    employee_id: int
    probation_start_date: date
    probation_end_date: date
    reviewed_by: Optional[int] = None
    remarks: Optional[str] = None


class EmployeeConfirmationUpdate(BaseModel):
    confirmation_date: Optional[date] = None
    performance_rating: Optional[str] = None    # EXCELLENT | GOOD | SATISFACTORY | POOR
    status: Optional[str] = None                # PENDING | CONFIRMED | EXTENDED | TERMINATED
    extended_till: Optional[date] = None
    reviewed_by: Optional[int] = None
    remarks: Optional[str] = None


class EmployeeConfirmationResponse(BaseModel):
    id: int
    employee_id: int
    probation_start_date: date
    probation_end_date: date
    confirmation_date: Optional[date]
    performance_rating: Optional[str]
    status: str
    extended_till: Optional[date]
    reviewed_by: Optional[int]
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
