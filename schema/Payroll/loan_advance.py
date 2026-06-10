
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class LoanAdvanceBase(BaseModel):
    employee_id: int
    loan_type: str  # Loan/Salary Advance
    amount: Decimal
    approved_amount: Optional[Decimal] = None
    emi_amount: Optional[Decimal] = None
    total_installments: Optional[int] = None
    paid_installments: Optional[int] = 0
    start_date: Optional[date] = None
    status: Optional[str] = "Pending"
    reason: Optional[str] = None
    approved_by: Optional[str] = None


class LoanAdvanceCreate(LoanAdvanceBase):
    pass


class LoanAdvanceUpdate(BaseModel):
    approved_amount: Optional[Decimal] = None
    emi_amount: Optional[Decimal] = None
    total_installments: Optional[int] = None
    paid_installments: Optional[int] = None
    start_date: Optional[date] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    approved_by: Optional[str] = None


class LoanAdvanceResponse(LoanAdvanceBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
