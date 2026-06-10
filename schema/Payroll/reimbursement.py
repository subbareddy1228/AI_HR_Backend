
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class ReimbursementBase(BaseModel):
    employee_id: int
    claim_type: str  # Travel/Medical/Food/Internet/Other
    amount: Decimal
    claim_date: date
    description: Optional[str] = None
    receipt_path: Optional[str] = None
    status: Optional[str] = "Pending"
    approved_by: Optional[str] = None
    remarks: Optional[str] = None


class ReimbursementCreate(ReimbursementBase):
    pass


class ReimbursementUpdate(BaseModel):
    claim_type: Optional[str] = None
    amount: Optional[Decimal] = None
    claim_date: Optional[date] = None
    description: Optional[str] = None
    receipt_path: Optional[str] = None
    status: Optional[str] = None
    approved_by: Optional[str] = None
    remarks: Optional[str] = None


class ReimbursementResponse(ReimbursementBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
