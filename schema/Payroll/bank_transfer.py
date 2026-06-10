
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class BankTransferBase(BaseModel):
    payroll_run_id: Optional[int] = None
    employee_id: int
    employee_name: str
    bank_account: str
    bank_name: str
    ifsc_code: str
    transfer_amount: Decimal
    transfer_date: date
    utr_number: Optional[str] = None
    status: Optional[str] = "Pending"
    remarks: Optional[str] = None


class BankTransferCreate(BankTransferBase):
    pass


class BankTransferUpdate(BaseModel):
    utr_number: Optional[str] = None
    status: Optional[str] = None
    transfer_date: Optional[date] = None
    transfer_amount: Optional[Decimal] = None
    remarks: Optional[str] = None


class BankTransferResponse(BankTransferBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
