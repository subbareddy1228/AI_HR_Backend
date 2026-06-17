
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ORM = ConfigDict(from_attributes=True)


class ReimbursementTypeCreate(BaseModel):

    name:         str     = Field(..., min_length=1, max_length=255,
                                  description="Component column value")
    description:  Optional[str]  = Field(None, description="Sub-text below name")
    category:     str     = Field(
        "OTHER",
        pattern=r"^(HEALTH|TRAVEL|COMMUNICATION|EDUCATION|OTHER)$",
        description="Category badge colour",
    )
    limit_amount: Decimal = Field(..., gt=0, decimal_places=2,
                                  description="Limit (₹) column")
    frequency:    str     = Field(
        "MONTHLY",
        pattern=r"^(MONTHLY|QUARTERLY|YEARLY|AD_HOC)$",
        description="Frequency column",
    )
    is_taxable:   bool    = Field(False, description="Taxable badge")


class ReimbursementTypeUpdate(BaseModel):
    """Body for PATCH /types/{id}  (Edit button → Save)"""
    name:         Optional[str]     = Field(None, min_length=1, max_length=255)
    description:  Optional[str]     = None
    category:     Optional[str]     = Field(
        None, pattern=r"^(HEALTH|TRAVEL|COMMUNICATION|EDUCATION|OTHER)$"
    )
    limit_amount: Optional[Decimal] = Field(None, gt=0)
    frequency:    Optional[str]     = Field(
        None, pattern=r"^(MONTHLY|QUARTERLY|YEARLY|AD_HOC)$"
    )
    is_taxable:   Optional[bool]    = None
    is_active:    Optional[bool]    = None


class ReimbursementTypeResponse(BaseModel):
    id:           int
    name:         str
    description:  Optional[str]
    category:     str
    limit_amount: Decimal
    frequency:    str
    is_taxable:   bool
    is_active:    bool
    created_at:   datetime
    updated_at:   datetime

    model_config = _ORM


class ReimbursementClaimCreate(BaseModel):

    employee_id:      int     = Field(..., description="FK → employees.id")
    employee_code:    str     = Field(..., min_length=1, max_length=50,
                                      description="Shown below name in table (EMP001)")
    employee_name:    str     = Field(..., min_length=1, max_length=255)
    type_id:          int     = Field(..., description="FK → reimbursement_types.id")
    claimed_amount:   Decimal = Field(..., gt=0, decimal_places=2)
    description:      Optional[str] = None
    receipt_path:     Optional[str] = Field(None, description="Server-side storage path")
    receipt_filename: Optional[str] = Field(None, description="Original filename for UI display")

    @field_validator("claimed_amount")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("claimed_amount must be > 0")
        return v


class ReimbursementClaimResponse(BaseModel):

    id:                      int
    employee_id:             int
    employee_code:           str
    employee_name:           str
    type_id:                 int
    type_name:               str
    frequency:               str
    claimed_amount:          Decimal
    tax_amount:              Decimal
    net_amount:              Decimal
    claim_date:              datetime
    description:             Optional[str]
    receipt_path:            Optional[str]
    receipt_filename:        Optional[str]

    status:                  str   

    manager_approval_status: str
    manager_approved_by:     Optional[str]
    manager_approved_at:     Optional[datetime]
    manager_remarks:         Optional[str]

    finance_approval_status: str
    finance_approved_by:     Optional[str]
    finance_approved_at:     Optional[datetime]
    finance_remarks:         Optional[str]

    payroll_processed:       bool
    payroll_run_id:          Optional[int]
    payroll_processed_date:  Optional[datetime]

    balance_used:            Optional[Decimal]
    balance_remaining:       Optional[Decimal]

    created_at:              datetime
    updated_at:              datetime

    model_config = _ORM


class ClaimListItem(BaseModel):

    id:                      int
    employee_id:             int
    employee_code:           str
    employee_name:           str
    type_name:               str
    frequency:               str
    claimed_amount:          Decimal
    tax_amount:              Decimal
    net_amount:              Decimal
    claim_date:              datetime
    receipt_filename:        Optional[str]

    status:                  str
    manager_approval_status: str
    manager_approved_at:     Optional[datetime]
    manager_approved_by:     Optional[str]
    finance_approval_status: str
    finance_approved_at:     Optional[datetime]
    finance_approved_by:     Optional[str]
    payroll_processed:       bool
    payroll_processed_date:  Optional[datetime]

    model_config = _ORM


class ManagerApprovalRequest(BaseModel):

    approved_by: Optional[str] = Field(None, description="Name of approving manager")
    remarks:     Optional[str] = Field(None, description="Optional comment")


class FinanceApprovalRequest(BaseModel):

    approved_by: Optional[str] = None
    remarks:     Optional[str] = None


class MarkPaidRequest(BaseModel):

    payroll_run_id:         int
    payroll_processed_date: Optional[datetime] = None
    processed_by:           Optional[str]      = None


class ClaimApprovalLogResponse(BaseModel):

    id:             int
    claim_id:       int
    from_status:    Optional[str]
    to_status:      str
    action_by_role: str 
    action_by_name: Optional[str]
    remarks:        Optional[str]
    created_at:     datetime

    model_config = _ORM


class ReimbursementBalanceResponse(BaseModel):

    id:               int
    employee_id:      int
    employee_code:    str
    employee_name:    str
    type_id:          int
    type_name:        str
    period:           str
    limit_amount:     Decimal
    used_amount:      Decimal
    remaining_amount: Decimal
    utilisation_pct:   float   
    utilisation_label: str     
    model_config = _ORM



class ReimbursementDashboard(BaseModel):

    total_claims:    int
    total_amount:    Decimal

    approved_claims: int
    approved_amount: Decimal

    pending_claims:  int     
    pending_amount:  Decimal

    rejected_claims: int
    rejected_amount: Decimal

    total_tax_amount: Decimal  


class ClaimsByTypeRow(BaseModel):

    type_name:    str
    category:     str
    claim_count:  int
    total_amount: Decimal
    avg_amount:   Decimal


class TaxAnalysis(BaseModel):

    total_taxable_amount:     Decimal 
    total_tax_amount:         Decimal   
    total_non_taxable:        Decimal   


class MonthlyTrendRow(BaseModel):

    month:        str      
    claim_count:  int
    total_amount: Decimal
    approved:     int
    pending:      int
    rejected:     int


class TopEmployeeRow(BaseModel):

    employee_id:   int
    employee_name: str
    claim_count:   int
    total_amount:  Decimal


class ReimbursementReports(BaseModel):
    """Full Reports tab payload"""
    by_type:       List[ClaimsByTypeRow]
    tax_analysis:  TaxAnalysis
    monthly_trend: List[MonthlyTrendRow]
    top_employees: List[TopEmployeeRow]


class ClaimExportRow(BaseModel):
    """Flat row for CSV / Excel export (Export button in Claims tab)"""
    id:             int
    employee:       str
    employee_id:    str
    type:           str
    amount:         Decimal
    tax_amount:     Decimal
    net_amount:     Decimal
    date:           str
    status:         str
    manager_status: str
    finance_status: str
    payroll_status: str
    description:    Optional[str]