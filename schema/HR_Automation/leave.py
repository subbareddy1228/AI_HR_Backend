from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type: str             # CASUAL | SICK | EARNED | MATERNITY | PATERNITY | UNPAID | COMP_OFF
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveRequestUpdate(BaseModel):
    status: Optional[str] = None    # PENDING | APPROVED | REJECTED | CANCELLED
    approved_by: Optional[int] = None
    rejection_reason: Optional[str] = None


class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: Optional[str]
    status: str
    approved_by: Optional[int]
    rejection_reason: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
