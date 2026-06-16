from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime


# ── Reimbursement Type (Master) ───────────────────────────────────────────────

class ReimbursementTypeCreate(BaseModel):
    component    : str   = Field(..., min_length=1, max_length=200)
    description  : Optional[str] = None
    category     : str   = Field(..., max_length=100)   # Health / Communication / Travel / Education / Other
    limit_amount : float = Field(..., gt=0)
    frequency    : str   = Field(..., max_length=50)    # Monthly / Yearly / Quarterly / Ad-hoc
    is_taxable   : bool  = False
    is_active    : bool  = True


class ReimbursementTypeUpdate(BaseModel):
    component    : Optional[str]   = Field(None, min_length=1, max_length=200)
    description  : Optional[str]   = None
    category     : Optional[str]   = None
    limit_amount : Optional[float] = Field(None, gt=0)
    frequency    : Optional[str]   = None
    is_taxable   : Optional[bool]  = None
    is_active    : Optional[bool]  = None


class ReimbursementTypeResponse(BaseModel):
    id           : int
    component    : str
    description  : Optional[str]
    category     : str
    limit_amount : float
    frequency    : str
    is_taxable   : bool
    is_active    : bool
    created_at   : datetime
    updated_at   : datetime

    class Config:
        from_attributes = True


# ── Reimbursement Claim ───────────────────────────────────────────────────────

class ReimbursementClaimCreate(BaseModel):
    employee_id           : int
    reimbursement_type_id : int
    amount                : float = Field(..., gt=0)
    claim_date            : date
    description           : Optional[str] = None
    receipt_url           : Optional[str] = Field(None, max_length=500)
    receipt_filename      : Optional[str] = Field(None, max_length=255)
    payroll_id            : Optional[int] = None

    @validator("claim_date")
    def claim_date_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Claim date cannot be in the future.")
        return v


class ReimbursementClaimUpdate(BaseModel):
    amount                : Optional[float] = Field(None, gt=0)
    claim_date            : Optional[date]  = None
    description           : Optional[str]   = None
    receipt_url           : Optional[str]   = None
    receipt_filename      : Optional[str]   = None
    payroll_id            : Optional[int]   = None


class ManagerApprovalRequest(BaseModel):
    approved_by : Optional[str] = None
    remarks     : Optional[str] = None


class FinanceApprovalRequest(BaseModel):
    approved_by : Optional[str] = None
    remarks     : Optional[str] = None


class ReimbursementClaimResponse(BaseModel):
    id                     : int
    employee_id            : int
    reimbursement_type_id  : int
    amount                 : float
    claim_date             : date
    description            : Optional[str]
    receipt_url            : Optional[str]
    receipt_filename       : Optional[str]
    status                 : str
    manager_status         : str
    manager_approved_by    : Optional[str]
    manager_approved_date  : Optional[date]
    manager_remarks        : Optional[str]
    finance_status         : str
    finance_approved_by    : Optional[str]
    finance_approved_date  : Optional[date]
    finance_remarks        : Optional[str]
    payroll_id             : Optional[int]
    payroll_processed_date : Optional[date]
    is_taxable             : bool
    tax_amount             : float
    created_at             : datetime
    updated_at             : datetime

    class Config:
        from_attributes = True


# ── Reimbursement Balance ─────────────────────────────────────────────────────

class ReimbursementBalanceResponse(BaseModel):
    id                    : int
    employee_id           : int
    reimbursement_type_id : int
    period                : str
    limit_amount          : float
    used_amount           : float
    remaining_amount      : float
    created_at            : datetime
    updated_at            : datetime

    class Config:
        from_attributes = True


# ── Reports ───────────────────────────────────────────────────────────────────

class ClaimsByTypeReport(BaseModel):
    reimbursement_type_id : int
    component             : str
    category              : str
    count                 : int
    total_amount          : float
    avg_amount            : float


class TaxAnalysisReport(BaseModel):
    total_taxable_amount    : float
    total_tax_amount        : float
    total_non_taxable_amount: float


class MonthlyTrendReport(BaseModel):
    month        : str    # "January 2024"
    claims       : int
    total_amount : float
    approved     : int
    pending      : int
    rejected     : int


class ReimbursementReportsResponse(BaseModel):
    claims_by_type : List[ClaimsByTypeReport]
    tax_analysis   : TaxAnalysisReport
    monthly_trend  : List[MonthlyTrendReport]


# ── Dashboard summary ─────────────────────────────────────────────────────────

class ReimbursementDashboard(BaseModel):
    total_claims   : int
    total_amount   : float
    approved       : int
    approved_amount: float
    pending        : int
    pending_amount : float
    tax_amount     : float