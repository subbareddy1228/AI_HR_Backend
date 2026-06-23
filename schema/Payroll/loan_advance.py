
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


LoanType = Literal[
    "Educational loan", "Emergency loan", "Festival advance", "Vehicle loan",
    "Salary advance", "Personal loan", "Medical advance", "Other",
]
InterestMethod = Literal["Reducing Balance", "Flat Rate", "Interest Free"]
RepaymentMode  = Literal["Payroll Deduction", "Bank Transfer", "Cash"]
LoanStatus     = Literal["PENDING", "APPROVED", "REJECTED", "ACTIVE", "COMPLETED", "DEFAULTED"]
RepaymentStatus = Literal["PENDING", "PAID", "OVERDUE", "WAIVED"]


class LoanApplicationCreate(BaseModel):
  
    employee_id:      int            = Field(..., gt=0)
    loan_type:         LoanType
    amount:            Decimal        = Field(..., gt=0, decimal_places=2)
    reason:            Optional[str] = None
    interest_rate:     Decimal        = Field(default=Decimal("0"), ge=0, le=100, decimal_places=2)
    interest_method:   InterestMethod = "Interest Free"
    repayment_mode:    RepaymentMode  = "Payroll Deduction"
    requested_tenure_months: Optional[int] = Field(None, gt=0, le=120)

    @model_validator(mode="after")
    def interest_consistency(self) -> "LoanApplicationCreate":
        if self.interest_method == "Interest Free" and self.interest_rate != 0:
            raise ValueError("interest_rate must be 0 when interest_method is 'Interest Free'")
        if self.interest_method != "Interest Free" and self.interest_rate == 0:
            raise ValueError("interest_rate must be greater than 0 for an interest-bearing loan")
        return self


class LoanApprovalRequest(BaseModel):
  
    approved_by:        str            = Field(..., min_length=1, max_length=255)
    approved_amount:    Decimal        = Field(..., gt=0, decimal_places=2)
    interest_rate:      Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    interest_method:    Optional[InterestMethod] = None
    total_installments: int            = Field(..., gt=0, le=120, description="Tenure in months")
    issue_date:         date

    @model_validator(mode="after")
    def issue_not_in_past_excessively(self) -> "LoanApprovalRequest":
        
        if self.issue_date > date.today():
            from datetime import timedelta
            if self.issue_date > date.today() + timedelta(days=30):
                raise ValueError("issue_date cannot be more than 30 days in the future")
        return self


class LoanRejectionRequest(BaseModel):
    approved_by: str = Field(..., min_length=1, max_length=255)
    rejection_reason: str = Field(..., min_length=1)


class LoanAdvanceUpdate(BaseModel):
   
    loan_type:          Optional[LoanType]       = None
    amount:             Optional[Decimal]        = Field(None, gt=0, decimal_places=2)
    reason:             Optional[str]            = None
    interest_rate:      Optional[Decimal]        = Field(None, ge=0, le=100, decimal_places=2)
    interest_method:    Optional[InterestMethod] = None
    repayment_mode:     Optional[RepaymentMode]  = None
    emi_amount:         Optional[Decimal]        = Field(None, gt=0, decimal_places=2)
    total_installments: Optional[int]            = Field(None, gt=0, le=120)
    issue_date:         Optional[date]           = None
    end_date:           Optional[date]           = None
    status:             Optional[LoanStatus]      = None


class RecordRepaymentRequest(BaseModel):
 
    installment_number: Optional[int]  = Field(None, gt=0, description="If omitted, pays the next due installment")
    paid_amount:         Decimal        = Field(..., gt=0, decimal_places=2)
    paid_date:           date           = Field(default_factory=date.today)
    payment_reference:   Optional[str]  = None


class LoanRepaymentResponse(BaseModel):
    id:                  int
    loan_id:             int
    installment_number:  int
    due_date:            date
    emi_amount:          Decimal
    status:              RepaymentStatus
    paid_amount:         Optional[Decimal]
    paid_date:           Optional[date]
    payment_reference:   Optional[str]

    model_config = ConfigDict(from_attributes=True)


class LoanAdvanceResponse(BaseModel):
    id:                  int
    loan_code:           str
    employee_id:         int
    employee_code:       str
    employee_name:       str
    designation:         Optional[str]
    department:          Optional[str]

    loan_type:           str
    amount:              Decimal
    reason:              Optional[str]

    interest_rate:       Decimal
    interest_method:     str
    repayment_mode:      str

    status:              str
    approved_amount:     Optional[Decimal]
    approved_by:         Optional[str]
    approved_at:         Optional[datetime]
    rejection_reason:    Optional[str]

    emi_amount:          Optional[Decimal]
    total_installments:  Optional[int]
    paid_installments:   int

    issue_date:          Optional[date]
    end_date:             Optional[date]
    next_due_date:        Optional[date]
    closed_date:           Optional[date]

    total_paid:           Decimal
    total_pending:        Decimal

    created_at:           datetime
    updated_at:            datetime

    model_config = ConfigDict(from_attributes=True)


class LoanAdvanceDetailResponse(LoanAdvanceResponse):

    repayments: List[LoanRepaymentResponse] = []


class LoanListFilter(BaseModel):
    search:      Optional[str]       = Field(None, description="Employee name, ID, or loan ID")
    loan_type:   Optional[LoanType]  = None
    status:      Optional[LoanStatus] = None

    tab:         Optional[Literal["all", "pending", "active", "completed"]] = "all"
    skip:        int = Field(default=0, ge=0)
    limit:       int = Field(default=6, ge=1, le=200)  # UI default page size = 6



class LoanDashboardStats(BaseModel):
    total_loans:     int
    pending_count:   int
    active_count:    int
    completed_count: int
    total_amount:    Decimal
    pending_amount:  Decimal



class PaginatedLoanResponse(BaseModel):
    items:       List[LoanAdvanceResponse]
    total:       int
    skip:        int
    limit:       int
