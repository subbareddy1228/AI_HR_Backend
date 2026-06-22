"""
schema/HR_Operations/notice_period.py

Pydantic schemas for the Notice Period Tracking & Management module.
"""

from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
from typing import Optional, List


# ======================================================
# EMPLOYEE MINI (embedded in responses)
# ======================================================
class EmployeeMini(BaseModel):
    id: int
    employee_code: str
    full_name: str
    department: Optional[str] = None
    designation: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# 1. NOTICE PERIOD
# ======================================================
class NoticePeriodCreate(BaseModel):
    employee_id: int
    notice_start_date: date
    notice_end_date: date
    notice_period_days: int
    waiver_requested: Optional[str] = "NO"
    buyout_amount: Optional[int] = None
    remarks: Optional[str] = None


class NoticePeriodUpdate(BaseModel):
    notice_end_date: Optional[date] = None
    serving_days: Optional[int] = None
    waiver_requested: Optional[str] = None
    waiver_approved: Optional[str] = None
    buyout_amount: Optional[int] = None
    status: Optional[str] = None
    manager_ack_status: Optional[str] = None
    remarks: Optional[str] = None


class NoticePeriodResponse(BaseModel):
    id: int
    employee_id: int
    notice_start_date: date
    notice_end_date: date
    notice_period_days: int
    serving_days: Optional[int]
    waiver_requested: str
    waiver_approved: str
    buyout_amount: Optional[int]
    status: str
    manager_ack_status: str
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    employee: Optional[EmployeeMini] = None
    days_left: Optional[int] = None
    progress_percent: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# 2. RESIGNATION SUBMISSION (Submit Resignation modal)
# ======================================================
class ResignationSubmissionCreate(BaseModel):
    employee_id: int
    department: str
    role: str
    resignation_date: date
    notice_period_days: int = Field(description="30 | 45 | 60 | 90")
    resignation_reason: str
    additional_comments: Optional[str] = None
    reporting_manager_email: str


class ResignationSubmissionResponse(BaseModel):
    id: int
    employee_id: int
    notice_period_id: Optional[int]
    department: str
    role: str
    resignation_date: date
    notice_period_days: int
    resignation_reason: str
    additional_comments: Optional[str]
    reporting_manager_email: str
    ai_retention_probability: Optional[float]
    ai_risk_level: Optional[str]
    ai_recommendation: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    employee: Optional[EmployeeMini] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# 3. BUYOUT REQUEST
# ======================================================
class BuyoutRequestCreate(BaseModel):
    employee_id: int
    notice_period_id: Optional[int] = None
    requested_date: Optional[date] = None
    monthly_salary: float
    days_to_buyout: int
    remarks: Optional[str] = None


class BuyoutApprovalAction(BaseModel):
    approver_role: str = Field(description="MANAGER | HR | FINANCE")
    decision: str = Field(description="APPROVED | REJECTED")
    remarks: Optional[str] = None


class BuyoutRequestResponse(BaseModel):
    id: int
    employee_id: int
    notice_period_id: Optional[int]
    requested_date: date
    monthly_salary: float
    days_to_buyout: int
    buyout_amount: float
    status: str
    manager_approval: str
    hr_approval: str
    finance_approval: str
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    employee: Optional[EmployeeMini] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# 4. WAIVER REQUEST + DOCUMENTS
# ======================================================
class WaiverRequestCreate(BaseModel):
    employee_id: int
    notice_period_id: Optional[int] = None
    requested_date: Optional[date] = None
    waiver_days: int
    reason: str
    remarks: Optional[str] = None


class WaiverApprovalAction(BaseModel):
    approver_role: str = Field(description="MANAGER | HR | DIRECTOR")
    decision: str = Field(description="APPROVED | REJECTED")
    remarks: Optional[str] = None


class WaiverDocumentResponse(BaseModel):
    id: int
    waiver_request_id: int
    file_name: str
    file_path: str
    content_type: Optional[str]
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WaiverRequestResponse(BaseModel):
    id: int
    employee_id: int
    notice_period_id: Optional[int]
    requested_date: date
    waiver_days: int
    reason: str
    status: str
    manager_approval: str
    hr_approval: str
    director_approval: str
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    employee: Optional[EmployeeMini] = None
    documents: List[WaiverDocumentResponse] = []
    document_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# 5. COUNTER OFFER & RETENTION
# ======================================================
class CounterOfferCreate(BaseModel):
    employee_id: int
    notice_period_id: Optional[int] = None
    current_salary: float
    offered_salary: float
    remarks: Optional[str] = None


class CounterOfferDecision(BaseModel):
    decision: str = Field(description="ACCEPTED | REJECTED")
    remarks: Optional[str] = None


class CounterOfferResponse(BaseModel):
    id: int
    employee_id: int
    notice_period_id: Optional[int]
    current_salary: float
    offered_salary: float
    hike_percent: float
    retention_probability: Optional[float]
    ai_rationale: Optional[str]
    status: str
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    employee: Optional[EmployeeMini] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# 6. EXTENSION REQUEST
# ======================================================
class ExtensionRequestCreate(BaseModel):
    employee_id: int
    notice_period_id: Optional[int] = None
    current_lwd: date
    requested_lwd: date
    reason: str
    remarks: Optional[str] = None


class ExtensionApprovalAction(BaseModel):
    approver_role: str = Field(description="MANAGER | HR")
    decision: str = Field(description="APPROVED | REJECTED")
    remarks: Optional[str] = None


class ExtensionRequestResponse(BaseModel):
    id: int
    employee_id: int
    notice_period_id: Optional[int]
    current_lwd: date
    requested_lwd: date
    extension_days: int
    reason: str
    status: str
    manager_approval: str
    hr_approval: str
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    employee: Optional[EmployeeMini] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# 7. CALCULATORS
# ======================================================
class LWDCalculatorRequest(BaseModel):
    resignation_date: date
    notice_period_days: int


class LWDCalculatorResponse(BaseModel):
    resignation_date: date
    notice_period_days: int
    last_working_day: date


class BuyoutCalculatorRequest(BaseModel):
    monthly_salary: float
    days_to_buyout: int


class BuyoutCalculatorResponse(BaseModel):
    monthly_salary: float
    days_to_buyout: int
    per_day_salary: float
    buyout_amount: float


class WaiverCalculatorRequest(BaseModel):
    current_notice_period_days: int
    waiver_days_requested: int


class WaiverCalculatorResponse(BaseModel):
    current_notice_period_days: int
    waiver_days_requested: int
    remaining_notice_days: int


class ShortfallCalculatorRequest(BaseModel):
    required_notice_period_days: int
    actual_service_days: int


class ShortfallCalculatorResponse(BaseModel):
    required_notice_period_days: int
    actual_service_days: int
    shortfall_days: int
    is_shortfall: bool


# ======================================================
# 8. DASHBOARD
# ======================================================
class NoticePeriodDashboardStats(BaseModel):
    active_cases: int
    active_cases_delta_this_week: int
    pending_approvals: int
    ai_time_saved_hours: float
    retention_success_count: int
    retention_success_rate_percent: float
    prediction_accuracy_percent: float = 95.0
    auto_processing_enabled: bool = True


# ======================================================
# 9. EXPORT REPORTS
# ======================================================
class ExportReportsRequest(BaseModel):
    export_format: str = Field(description="JSON | CSV | PDF | EXCEL")
    include_cases: bool = True
    include_requests: bool = True
    include_statistics: bool = True
    include_analytics: bool = True