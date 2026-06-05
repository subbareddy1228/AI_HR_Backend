# FILE 9 (4/8) | schema/Payroll/reimbursement.py
# Schemas: ReimbursementBase/Create/Update/Response

# from pydantic import BaseModel, ConfigDict
# from typing import Optional
# from datetime import date, datetime
# from decimal import Decimal


# class ReimbursementBase(BaseModel):
#     employee_id: int
#     claim_type: str  # Travel/Medical/Food/Internet/Other
#     amount: Decimal
#     claim_date: date
#     description: Optional[str] = None
#     receipt_path: Optional[str] = None
#     status: Optional[str] = "Pending"
#     approved_by: Optional[str] = None
#     remarks: Optional[str] = None


# class ReimbursementCreate(ReimbursementBase):
#     pass


# class ReimbursementUpdate(BaseModel):
#     claim_type: Optional[str] = None
#     amount: Optional[Decimal] = None
#     claim_date: Optional[date] = None
#     description: Optional[str] = None
#     receipt_path: Optional[str] = None
#     status: Optional[str] = None
#     approved_by: Optional[str] = None
#     remarks: Optional[str] = None


# class ReimbursementResponse(ReimbursementBase):
#     id: int
#     created_at: Optional[datetime] = None

#     model_config = ConfigDict(from_attributes=True)


# schema/Payroll/reimbursement.py
# Schemas: ReimbursementBase/Create/Update/Response


from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime


# ── Create ────────────────────────────────────────────────────────────────────

class ReimbursementCreate(BaseModel):
    employee_id       : int
    claim_type        : str  = Field(..., min_length=1, max_length=100)
    description       : Optional[str]  = None
    amount            : float          = Field(..., gt=0)
    currency          : str            = Field(default="INR", max_length=10)
    expense_date      : date
    receipt_url       : Optional[str]  = Field(None, max_length=500)
    receipt_filename  : Optional[str]  = Field(None, max_length=255)
    payment_mode      : Optional[str]  = None
    payment_reference : Optional[str]  = None
    payroll_id        : Optional[int]  = None

    @validator("expense_date")
    def expense_date_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Expense date cannot be in the future.")
        return v

    @validator("currency")
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()


# ── Update ────────────────────────────────────────────────────────────────────

class ReimbursementUpdate(BaseModel):
    claim_type        : Optional[str]   = Field(None, min_length=1, max_length=100)
    description       : Optional[str]   = None
    amount            : Optional[float] = Field(None, gt=0)
    currency          : Optional[str]   = Field(None, max_length=10)
    expense_date      : Optional[date]  = None
    receipt_url       : Optional[str]   = Field(None, max_length=500)
    receipt_filename  : Optional[str]   = Field(None, max_length=255)
    status            : Optional[str]   = None
    approved_by       : Optional[str]   = None
    remarks           : Optional[str]   = None
    payment_mode      : Optional[str]   = None
    payment_reference : Optional[str]   = None
    paid_at           : Optional[datetime] = None
    payroll_id        : Optional[int]   = None


# ── Response ──────────────────────────────────────────────────────────────────

class ReimbursementResponse(BaseModel):
    id                : int
    employee_id       : int
    claim_type        : str
    description       : Optional[str]
    amount            : float
    currency          : str
    expense_date      : date
    receipt_url       : Optional[str]
    receipt_filename  : Optional[str]
    status            : str
    approved_by       : Optional[str]
    remarks           : Optional[str]
    payment_mode      : Optional[str]
    payment_reference : Optional[str]
    paid_at           : Optional[datetime]
    payroll_id        : Optional[int]
    created_at        : datetime
    updated_at        : datetime

    class Config:
        from_attributes = True