from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional


class TransferCreate(BaseModel):
    employee_id: int
    from_department: str
    to_department: str
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    transfer_type: str      # INTER_DEPARTMENT | INTER_LOCATION | INTER_COMPANY
    effective_date: date
    reason: Optional[str] = None


class TransferUpdate(BaseModel):
    status: Optional[str] = None    # PENDING | APPROVED | REJECTED | COMPLETED
    approved_by: Optional[int] = None
    remarks: Optional[str] = None


class TransferResponse(BaseModel):
    id: int
    employee_id: int
    from_department: str
    to_department: str
    from_location: Optional[str]
    to_location: Optional[str]
    transfer_type: str
    effective_date: date
    reason: Optional[str]
    status: str
    approved_by: Optional[int]
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
