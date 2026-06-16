from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime


# ── EMI Schedule ──────────────────────────────────────────────────────────────

class LoanEMIScheduleResponse(BaseModel):
    id             : int
    loan_id        : int
    installment_no : int
    due_date       : date
    emi_amount     : float
    principal_part : Optional[float]
    interest_part  : Optional[float]
    paid_amount    : float
    paid_date      : Optional[date]
    balance        : Optional[float]
    status         : str
    created_at     : datetime
    updated_at     : datetime

    class Config:
        from_attributes = True


# ── Create ────────────────────────────────────────────────────────────────────

class LoanAdvanceCreate(BaseModel):
    employee_id      : int
    loan_type        : str   = Field(..., min_length=1, max_length=100)
    # Educational loan | Emergency loan | Festival advance | Salary advance | Vehicle loan | Personal loan
    description      : Optional[str]   = None
    interest_rate    : float           = Field(0.0, ge=0)
    interest_method  : Optional[str]   = None   # Reducing Balance | No Interest | Flat
    repayment_method : str             = Field("Payroll Deduction", max_length=100)
    principal_amount : float           = Field(..., gt=0)
    emi_amount       : Optional[float] = Field(None, gt=0)
    tenure_months    : Optional[int]   = Field(None, gt=0)
    issue_date       : date
    start_date       : Optional[date]  = None
    end_date         : Optional[date]  = None
    payroll_id       : Optional[int]   = None

    @validator("issue_date")
    def issue_date_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Issue date cannot be in the future.")
        return v

    @validator("emi_amount", always=True)
    def auto_compute_emi(cls, v, values):
        """Auto-calculate EMI if not provided."""
        if v is not None:
            return v
        principal = values.get("principal_amount")
        tenure    = values.get("tenure_months")
        rate      = values.get("interest_rate", 0.0) or 0.0
        method    = values.get("interest_method", "") or ""
        if not (principal and tenure):
            return v
        if rate == 0 or method in ("No Interest", ""):
            return round(principal / tenure, 2)
        if method == "Reducing Balance":
            r = rate / (12 * 100)
            emi = principal * r * (1 + r) ** tenure / ((1 + r) ** tenure - 1)
            return round(emi, 2)
        if method == "Flat":
            total_interest = principal * (rate / 100) * (tenure / 12)
            return round((principal + total_interest) / tenure, 2)
        return round(principal / tenure, 2)


# ── Update ────────────────────────────────────────────────────────────────────

class LoanAdvanceUpdate(BaseModel):
    loan_type        : Optional[str]   = Field(None, min_length=1, max_length=100)
    description      : Optional[str]   = None
    interest_rate    : Optional[float] = Field(None, ge=0)
    interest_method  : Optional[str]   = None
    repayment_method : Optional[str]   = None
    principal_amount : Optional[float] = Field(None, gt=0)
    emi_amount       : Optional[float] = Field(None, gt=0)
    tenure_months    : Optional[int]   = Field(None, gt=0)
    issue_date       : Optional[date]  = None
    start_date       : Optional[date]  = None
    end_date         : Optional[date]  = None
    next_due_date    : Optional[date]  = None
    amount_paid      : Optional[float] = Field(None, ge=0)
    amount_pending   : Optional[float] = Field(None, ge=0)
    status           : Optional[str]   = None
    approved_by      : Optional[str]   = None
    remarks          : Optional[str]   = None
    payroll_id       : Optional[int]   = None


# ── EMI Payment ───────────────────────────────────────────────────────────────

class EMIPaymentRequest(BaseModel):
    installment_no : int   = Field(..., gt=0)
    paid_amount    : float = Field(..., gt=0)
    paid_date      : date


# ── Response ──────────────────────────────────────────────────────────────────

class LoanAdvanceResponse(BaseModel):
    id               : int
    loan_id          : str
    employee_id      : int
    loan_type        : str
    description      : Optional[str]
    interest_rate    : float
    interest_method  : Optional[str]
    repayment_method : str
    principal_amount : float
    amount_paid      : float
    amount_pending   : float
    emi_amount       : Optional[float]
    tenure_months    : Optional[int]
    issue_date       : date
    start_date       : Optional[date]
    end_date         : Optional[date]
    next_due_date    : Optional[date]
    approved_date    : Optional[date]
    status           : str
    approved_by      : Optional[str]
    remarks          : Optional[str]
    payroll_id       : Optional[int]
    created_at       : datetime
    updated_at       : datetime

    class Config:
        from_attributes = True


class LoanAdvanceDetailResponse(LoanAdvanceResponse):
    """Full detail with EMI schedule."""
    emi_schedules : List[LoanEMIScheduleResponse] = []


# ── Dashboard ─────────────────────────────────────────────────────────────────

class LoanDashboard(BaseModel):
    total_loans    : int
    active_loans   : int
    pending_loans  : int
    completed      : int
    total_amount   : float
    pending_amount : float