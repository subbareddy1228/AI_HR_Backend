# FILE 9 (5/8) | schema/Payroll/loan_advance.py
# Schemas: LoanAdvanceBase/Create/Update/Response

# from pydantic import BaseModel, ConfigDict
# from typing import Optional
# from datetime import date, datetime
# from decimal import Decimal


# class LoanAdvanceBase(BaseModel):
#     employee_id: int
#     loan_type: str  # Loan/Salary Advance
#     amount: Decimal
#     approved_amount: Optional[Decimal] = None
#     emi_amount: Optional[Decimal] = None
#     total_installments: Optional[int] = None
#     paid_installments: Optional[int] = 0
#     start_date: Optional[date] = None
#     status: Optional[str] = "Pending"
#     reason: Optional[str] = None
#     approved_by: Optional[str] = None


# class LoanAdvanceCreate(LoanAdvanceBase):
#     pass


# class LoanAdvanceUpdate(BaseModel):
#     approved_amount: Optional[Decimal] = None
#     emi_amount: Optional[Decimal] = None
#     total_installments: Optional[int] = None
#     paid_installments: Optional[int] = None
#     start_date: Optional[date] = None
#     status: Optional[str] = None
#     reason: Optional[str] = None
#     approved_by: Optional[str] = None


# class LoanAdvanceResponse(LoanAdvanceBase):
#     id: int
#     created_at: Optional[datetime] = None

#     model_config = ConfigDict(from_attributes=True)

# FILE 9 (5/8) | schema/Payroll/loan_advance.py
# Schemas: LoanAdvanceBase/Create/Update/Request/Response


from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
import math


# ── EMI Schedule ──────────────────────────────────────────────────────────────

class LoanEMIScheduleResponse(BaseModel):
    id              : int
    loan_id         : int
    installment_no  : int
    due_date        : date
    emi_amount      : float
    principal_part  : Optional[float]
    interest_part   : Optional[float]
    paid_amount     : float
    paid_date       : Optional[date]
    balance         : Optional[float]
    status          : str
    created_at      : datetime
    updated_at      : datetime

    class Config:
        from_attributes = True


# ── Create ────────────────────────────────────────────────────────────────────

class LoanAdvanceCreate(BaseModel):
    employee_id       : int
    loan_type         : str   = Field(..., min_length=1, max_length=100)
    description       : Optional[str]  = None
    principal_amount  : float = Field(..., gt=0)
    interest_method   : Optional[str]  = Field(None, max_length=50)   # Reducing Balance / No Interest / Flat
    interest_rate     : Optional[float] = Field(0.0, ge=0)
    emi_amount        : Optional[float] = Field(None, gt=0)
    tenure_months     : Optional[int]  = Field(None, gt=0)
    repayment_method  : Optional[str]  = Field("Payroll Deduction", max_length=100)
    issue_date        : date
    start_date        : Optional[date] = None
    end_date          : Optional[date] = None
    payroll_id        : Optional[int]  = None

    @validator("issue_date")
    def issue_date_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Issue date cannot be in the future.")
        return v

    @validator("emi_amount", always=True)
    def compute_emi_if_missing(cls, v, values):
        # Auto-calculate EMI if not provided but principal + tenure given
        if v is None:
            principal = values.get("principal_amount")
            tenure    = values.get("tenure_months")
            rate      = values.get("interest_rate", 0.0) or 0.0
            method    = values.get("interest_method", "")

            if principal and tenure:
                if rate == 0 or method == "No Interest":
                    return round(principal / tenure, 2)
                elif method == "Reducing Balance":
                    r = rate / (12 * 100)
                    emi = principal * r * (1 + r) ** tenure / ((1 + r) ** tenure - 1)
                    return round(emi, 2)
        return v


# ── Update ────────────────────────────────────────────────────────────────────

class LoanAdvanceUpdate(BaseModel):
    loan_type         : Optional[str]   = Field(None, min_length=1, max_length=100)
    description       : Optional[str]   = None
    principal_amount  : Optional[float] = Field(None, gt=0)
    interest_method   : Optional[str]   = None
    interest_rate     : Optional[float] = Field(None, ge=0)
    emi_amount        : Optional[float] = Field(None, gt=0)
    tenure_months     : Optional[int]   = Field(None, gt=0)
    repayment_method  : Optional[str]   = None
    issue_date        : Optional[date]  = None
    start_date        : Optional[date]  = None
    end_date          : Optional[date]  = None
    next_due_date     : Optional[date]  = None
    amount_paid       : Optional[float] = Field(None, ge=0)
    amount_pending    : Optional[float] = Field(None, ge=0)
    status            : Optional[str]   = None
    approved_by       : Optional[str]   = None
    remarks           : Optional[str]   = None
    payroll_id        : Optional[int]   = None


# ── EMI Payment ───────────────────────────────────────────────────────────────

class EMIPaymentRequest(BaseModel):
    installment_no : int   = Field(..., gt=0)
    paid_amount    : float = Field(..., gt=0)
    paid_date      : date


# ── Response ──────────────────────────────────────────────────────────────────

class LoanAdvanceResponse(BaseModel):
    id                : int
    loan_id           : str
    employee_id       : int
    loan_type         : str
    description       : Optional[str]
    principal_amount  : float
    amount_paid       : float
    amount_pending    : float
    interest_method   : Optional[str]
    interest_rate     : Optional[float]
    emi_amount        : Optional[float]
    tenure_months     : Optional[int]
    repayment_method  : Optional[str]
    issue_date        : date
    start_date        : Optional[date]
    end_date          : Optional[date]
    next_due_date     : Optional[date]
    status            : str
    approved_by       : Optional[str]
    remarks           : Optional[str]
    payroll_id        : Optional[int]
    created_at        : datetime
    updated_at        : datetime

    class Config:
        from_attributes = True


class LoanAdvanceDetailResponse(LoanAdvanceResponse):
    """Full detail including EMI schedule."""
    emi_schedules : List[LoanEMIScheduleResponse] = []