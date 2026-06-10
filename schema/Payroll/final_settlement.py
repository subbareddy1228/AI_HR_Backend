
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class FinalSettlementBase(BaseModel):
    employee_id: int
    last_working_date: date
    notice_period_days: Optional[int] = 0
    notice_period_shortfall_days: Optional[int] = 0
    basic_salary: Decimal
    gratuity_amount: Optional[Decimal] = Decimal("0.00")
    leave_encashment_days: Optional[int] = 0
    leave_encashment_amount: Optional[Decimal] = Decimal("0.00")
    pending_reimbursements: Optional[Decimal] = Decimal("0.00")
    loan_recovery: Optional[Decimal] = Decimal("0.00")
    tds_deduction: Optional[Decimal] = Decimal("0.00")
    total_payable: Decimal
    settlement_status: Optional[str] = "Draft"
    approved_by: Optional[str] = None
    remarks: Optional[str] = None


class FinalSettlementCreate(FinalSettlementBase):
    pass


class FinalSettlementUpdate(BaseModel):
    last_working_date: Optional[date] = None
    notice_period_days: Optional[int] = None
    notice_period_shortfall_days: Optional[int] = None
    basic_salary: Optional[Decimal] = None
    gratuity_amount: Optional[Decimal] = None
    leave_encashment_days: Optional[int] = None
    leave_encashment_amount: Optional[Decimal] = None
    pending_reimbursements: Optional[Decimal] = None
    loan_recovery: Optional[Decimal] = None
    tds_deduction: Optional[Decimal] = None
    total_payable: Optional[Decimal] = None
    settlement_status: Optional[str] = None
    approved_by: Optional[str] = None
    remarks: Optional[str] = None


class FinalSettlementResponse(FinalSettlementBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
