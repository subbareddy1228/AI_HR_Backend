# schema/HR_Operations/exit_management.py

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator



class _OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ExitCaseCreate(BaseModel):
    employee_id       : int
    exit_type         : str   = Field(..., description="Resignation|Termination|Retirement|Absconding|Contract End")
    resignation_date  : date
    last_working_date : Optional[date] = None
    exit_reason       : Optional[str] = None
    reason_detail     : Optional[str] = None
    remarks           : Optional[str] = None

    @field_validator("exit_type")
    @classmethod
    def validate_exit_type(cls, v: str) -> str:
        allowed = ["Resignation", "Termination", "Retirement", "Absconding", "Contract End"]
        if v not in allowed:
            raise ValueError(f"exit_type must be one of {allowed}")
        return v


class ExitCaseUpdate(BaseModel):
    exit_type            : Optional[str]  = None
    last_working_date    : Optional[date] = None
    expected_last_day    : Optional[date] = None
    exit_reason          : Optional[str]  = None
    reason_detail        : Optional[str]  = None
    status               : Optional[str]  = None
    clearance_status     : Optional[str]  = None
    exit_interview_done  : Optional[bool] = None
    exit_interview_date  : Optional[date] = None
    approved_by          : Optional[int]  = None
    remarks              : Optional[str]  = None


class ExitCaseResponse(_OrmBase):
    id                  : int
    employee_id         : int
    exit_type           : str
    resignation_date    : date
    last_working_date   : Optional[date]
    expected_last_day   : Optional[date]
    exit_reason         : Optional[str]
    reason_detail       : Optional[str]
    status              : str
    clearance_status    : str
    exit_interview_done : bool
    exit_interview_date : Optional[date]
    initiated_by        : Optional[int]
    approved_by         : Optional[int]
    remarks             : Optional[str]
    created_at          : datetime
    updated_at          : datetime


class ExitCaseListItem(_OrmBase):

    id                  : int
    employee_id         : int
    employee_name       : Optional[str] = None  
    employee_code       : Optional[str] = None
    department          : Optional[str] = None
    designation         : Optional[str] = None
    location            : Optional[str] = None
    exit_type           : str
    resignation_date    : date
    last_working_date   : Optional[date]
    exit_reason         : Optional[str]
    status              : str
    clearance_status    : str
    clearance_progress  : int = 0            
    pending_items_count : int = 0
    exit_interview_done : bool
    created_at          : datetime


class ExitCaseDetailResponse(ExitCaseResponse):

    employee_name      : Optional[str]      = None
    employee_code      : Optional[str]      = None
    department         : Optional[str]      = None
    designation        : Optional[str]      = None
    location           : Optional[str]      = None
    joining_date       : Optional[date]     = None
    tenure_months      : Optional[int]      = None
    clearance_items    : List["ClearanceItemResponse"]  = []
    settlement         : Optional["ExitSettlementResponse"] = None
    exit_interview     : Optional["ExitInterviewResponse"]  = None
    alumni_record      : Optional["AlumniRecordResponse"]   = None
    documents          : List["ExitDocumentResponse"]   = []



class ClearanceItemCreate(BaseModel):
    exit_case_id   : int
    department     : str
    item_name      : str
    assigned_to_id : Optional[int]  = None
    is_mandatory   : bool           = True
    sort_order     : int            = 0
    remarks        : Optional[str]  = None


class ClearanceItemUpdate(BaseModel):
    assigned_to_id : Optional[int]  = None
    status         : Optional[str]  = None
    remarks        : Optional[str]  = None
    completed_at   : Optional[datetime] = None


class ClearanceItemResponse(_OrmBase):
    id             : int
    exit_case_id   : int
    department     : str
    item_name      : str
    assigned_to_id : Optional[int]
    status         : str
    completed_at   : Optional[datetime]
    remarks        : Optional[str]
    is_mandatory   : bool
    sort_order     : int
    created_at     : datetime
    updated_at     : datetime


class BulkClearanceUpdateRequest(BaseModel):
    item_ids : List[int]
    status   : str
    remarks  : Optional[str] = None


class InterviewResponse(BaseModel):
    question : str
    answer   : str


class ExitInterviewCreate(BaseModel):
    exit_case_id         : int
    interview_date       : Optional[date]  = None
    interviewer_id       : Optional[int]   = None
    interview_mode       : Optional[str]   = None
    overall_satisfaction : Optional[int]   = Field(None, ge=1, le=10)
    job_satisfaction     : Optional[int]   = Field(None, ge=1, le=10)
    management_rating    : Optional[int]   = Field(None, ge=1, le=10)
    culture_rating       : Optional[int]   = Field(None, ge=1, le=10)
    primary_reason       : Optional[str]   = None
    would_recommend      : Optional[bool]  = None
    open_to_return       : Optional[bool]  = None
    responses            : List[InterviewResponse] = []
    additional_comments  : Optional[str]   = None


class ExitInterviewUpdate(BaseModel):
    interview_date       : Optional[date]  = None
    interviewer_id       : Optional[int]   = None
    interview_mode       : Optional[str]   = None
    overall_satisfaction : Optional[int]   = Field(None, ge=1, le=10)
    job_satisfaction     : Optional[int]   = Field(None, ge=1, le=10)
    management_rating    : Optional[int]   = Field(None, ge=1, le=10)
    culture_rating       : Optional[int]   = Field(None, ge=1, le=10)
    primary_reason       : Optional[str]   = None
    would_recommend      : Optional[bool]  = None
    open_to_return       : Optional[bool]  = None
    responses            : Optional[List[InterviewResponse]] = None
    additional_comments  : Optional[str]   = None


class ExitInterviewResponse(_OrmBase):
    id                   : int
    exit_case_id         : int
    interview_date       : Optional[date]
    interviewer_id       : Optional[int]
    interview_mode       : Optional[str]
    overall_satisfaction : Optional[int]
    job_satisfaction     : Optional[int]
    management_rating    : Optional[int]
    culture_rating       : Optional[int]
    primary_reason       : Optional[str]
    would_recommend      : Optional[bool]
    open_to_return       : Optional[bool]
    responses            : Optional[List[Dict[str, Any]]]
    additional_comments  : Optional[str]
    created_at           : datetime
    updated_at           : datetime


class SettlementCalculateRequest(BaseModel):
  
    exit_case_id          : int
    override_basic_salary : Optional[Decimal] = None   


class ExitSettlementCreate(BaseModel):
    exit_case_id                 : int
    employee_id                  : int
    basic_salary                 : Decimal = Decimal("0")
    last_month_salary            : Decimal = Decimal("0")
    leave_encashment_days        : int     = 0
    leave_encashment_amount      : Decimal = Decimal("0")
    gratuity_amount              : Decimal = Decimal("0")
    bonus_amount                 : Decimal = Decimal("0")
    pending_reimbursements       : Decimal = Decimal("0")
    other_earnings               : Decimal = Decimal("0")
    notice_period_shortfall_days : int     = 0
    notice_recovery_amount       : Decimal = Decimal("0")
    loan_recovery                : Decimal = Decimal("0")
    asset_recovery               : Decimal = Decimal("0")
    tds_deduction                : Decimal = Decimal("0")
    other_deductions             : Decimal = Decimal("0")
    remarks                      : Optional[str] = None


class ExitSettlementUpdate(BaseModel):
    basic_salary                 : Optional[Decimal] = None
    last_month_salary            : Optional[Decimal] = None
    leave_encashment_days        : Optional[int]     = None
    leave_encashment_amount      : Optional[Decimal] = None
    gratuity_amount              : Optional[Decimal] = None
    bonus_amount                 : Optional[Decimal] = None
    pending_reimbursements       : Optional[Decimal] = None
    other_earnings               : Optional[Decimal] = None
    notice_period_shortfall_days : Optional[int]     = None
    notice_recovery_amount       : Optional[Decimal] = None
    loan_recovery                : Optional[Decimal] = None
    asset_recovery               : Optional[Decimal] = None
    tds_deduction                : Optional[Decimal] = None
    other_deductions             : Optional[Decimal] = None
    settlement_status            : Optional[str]     = None
    payment_date                 : Optional[date]    = None
    payment_reference            : Optional[str]     = None
    remarks                      : Optional[str]     = None


class ExitSettlementResponse(_OrmBase):
    id                           : int
    exit_case_id                 : int
    employee_id                  : int
    basic_salary                 : Decimal
    last_month_salary            : Decimal
    leave_encashment_days        : int
    leave_encashment_amount      : Decimal
    gratuity_amount              : Decimal
    bonus_amount                 : Decimal
    pending_reimbursements       : Decimal
    other_earnings               : Decimal
    notice_period_shortfall_days : int
    notice_recovery_amount       : Decimal
    loan_recovery                : Decimal
    asset_recovery               : Decimal
    tds_deduction                : Decimal
    other_deductions             : Decimal
    total_earnings               : Decimal
    total_deductions             : Decimal
    net_payable                  : Decimal
    settlement_status            : str
    payment_date                 : Optional[date]
    payment_reference            : Optional[str]
    approved_by_id               : Optional[int]
    approved_at                  : Optional[datetime]
    remarks                      : Optional[str]
    created_at                   : datetime
    updated_at                   : datetime


class SettlementListItem(_OrmBase):
  
    id               : int
    exit_case_id     : int
    employee_id      : int
    employee_name    : Optional[str] = None
    employee_code    : Optional[str] = None
    department       : Optional[str] = None
    net_payable      : Decimal
    payment_date     : Optional[date]
    settlement_status: str
    created_at       : datetime


class ApproveSettlementRequest(BaseModel):
    approved_by_id    : int
    payment_reference : Optional[str] = None
    payment_date      : Optional[date] = None
    remarks           : Optional[str]  = None



class AlumniRecordCreate(BaseModel):
    exit_case_id       : int
    employee_id        : int
    rehire_eligible    : bool          = True
    rehire_notes       : Optional[str] = None
    blacklisted        : bool          = False
    blacklist_reason   : Optional[str] = None
    boomerang_interest : Optional[bool] = None
    engagement_level   : Optional[str]  = None
    linkedin_url       : Optional[str]  = None
    current_company    : Optional[str]  = None
    current_designation: Optional[str]  = None
    notes              : Optional[str]  = None


class AlumniRecordUpdate(BaseModel):
    rehire_eligible    : Optional[bool] = None
    rehire_notes       : Optional[str]  = None
    blacklisted        : Optional[bool] = None
    blacklist_reason   : Optional[str]  = None
    boomerang_interest : Optional[bool] = None
    boomerang_applied  : Optional[bool] = None
    boomerang_hired    : Optional[bool] = None
    boomerang_hire_date: Optional[date] = None
    engagement_level   : Optional[str]  = None
    last_contact_date  : Optional[date] = None
    referral_count     : Optional[int]  = None
    linkedin_url       : Optional[str]  = None
    current_company    : Optional[str]  = None
    current_designation: Optional[str]  = None
    notes              : Optional[str]  = None


class AlumniRecordResponse(_OrmBase):
    id                 : int
    exit_case_id       : int
    employee_id        : int
    rehire_eligible    : bool
    rehire_notes       : Optional[str]
    blacklisted        : bool
    blacklist_reason   : Optional[str]
    boomerang_interest : Optional[bool]
    boomerang_applied  : bool
    boomerang_hired    : bool
    boomerang_hire_date: Optional[date]
    engagement_level   : Optional[str]
    last_contact_date  : Optional[date]
    referral_count     : int
    linkedin_url       : Optional[str]
    current_company    : Optional[str]
    current_designation: Optional[str]
    notes              : Optional[str]
    created_at         : datetime
    updated_at         : datetime


class AlumniListItem(_OrmBase):
    
    id                 : int
    employee_id        : int
    employee_name      : Optional[str] = None
    employee_code      : Optional[str] = None
    department         : Optional[str] = None
    exit_date          : Optional[date] = None
    rehire_eligible    : bool
    boomerang_interest : Optional[bool]
    engagement_level   : Optional[str]
    blacklisted        : bool


class ExitDocumentResponse(_OrmBase):
    id             : int
    exit_case_id   : int
    employee_id    : int
    document_type  : str
    file_name      : str
    file_path      : str
    file_size_bytes: Optional[int]
    mime_type      : Optional[str]
    generated_by_id: Optional[int]
    is_generated   : bool
    issued_on      : Optional[date]
    remarks        : Optional[str]
    created_at     : datetime


class ClearanceTemplateCreate(BaseModel):
    department   : str
    item_name    : str
    is_mandatory : bool = True
    sort_order   : int  = 0


class ClearanceTemplateUpdate(BaseModel):
    department   : Optional[str]  = None
    item_name    : Optional[str]  = None
    is_mandatory : Optional[bool] = None
    sort_order   : Optional[int]  = None
    is_active    : Optional[bool] = None


class ClearanceTemplateResponse(_OrmBase):
    id           : int
    department   : str
    item_name    : str
    is_mandatory : bool
    sort_order   : int
    is_active    : bool
    created_at   : datetime
    updated_at   : datetime
class ExitKPISummary(BaseModel):
    total_cases          : int
    pending_cases        : int
    escalated_cases      : int
    completed_cases      : int
    alumni_count         : int
    exit_rate_percent    : float
    avg_tenure_months    : float
    top_exit_reason      : Optional[str]
    pending_settlements  : int
    avg_clearance_days   : Optional[float]


class DepartmentExitStat(BaseModel):
    department      : str
    total_exits     : int
    exit_rate       : float
    top_reason      : Optional[str]


class MonthlyTrend(BaseModel):
    month           : str  
    exit_count      : int
    exit_type_breakdown : Dict[str, int] = {}


class TrendAnalysisResponse(BaseModel):
    period_label         : str
    total_exits          : int
    exit_rate_percent    : float
    avg_tenure_months    : float
    top_exit_reason      : Optional[str]
    monthly_trends       : List[MonthlyTrend]
    department_stats     : List[DepartmentExitStat]
    exit_type_breakdown  : Dict[str, int]
    reason_breakdown     : Dict[str, int]


class ExitReasonStat(BaseModel):
    reason      : str
    count       : int
    percentage  : float


class PaginatedExitCases(BaseModel):
    total       : int
    page        : int
    page_size   : int
    items       : List[ExitCaseListItem]


class PaginatedSettlements(BaseModel):
    total       : int
    page        : int
    page_size   : int
    items       : List[SettlementListItem]


class PaginatedAlumni(BaseModel):
    total       : int
    page        : int
    page_size   : int
    items       : List[AlumniListItem]

class InitiateExitResponse(BaseModel):
  
    exit_case     : ExitCaseResponse
    clearance_items_created : int
    message       : str


class CloseExitRequest(BaseModel):
  
    remarks : Optional[str] = None


ExitCaseDetailResponse.model_rebuild()
