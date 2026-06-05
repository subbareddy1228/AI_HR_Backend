# schema/Employee_Management/employee_lifecycle.py
# Pydantic v2 schemas for all Employee Lifecycle resources

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime

# ─── Allowed event types ──────────────────────────────────────────────────────
ALLOWED_EVENT_TYPES = {
    "Joining", "Probation_Start", "Probation_Extension", "Confirmation",
    "Promotion", "Demotion", "Department_Change", "Location_Change",
    "Manager_Change", "Designation_Change", "Grade_Change", "Salary_Revision",
    "Contract_Renewal", "Resignation", "Termination", "Retirement",
    "Rehire", "Transfer", "Suspension", "Reinstatement",
    "Work_Anniversary", "Background_Verification", "Training_Completion",
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Core Lifecycle Event
# ══════════════════════════════════════════════════════════════════════════════

class LifecycleEventCreate(BaseModel):
    employee_id: int
    event_type: str
    event_date: date
    effective_date: Optional[date] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    from_department: Optional[str] = None
    to_department: Optional[str] = None
    from_designation: Optional[str] = None
    to_designation: Optional[str] = None
    from_grade: Optional[str] = None
    to_grade: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    from_manager_id: Optional[int] = None
    to_manager_id: Optional[int] = None
    from_salary: Optional[str] = None
    to_salary: Optional[str] = None
    initiated_by: Optional[int] = None
    approved_by: Optional[int] = None
    approval_status: Optional[str] = "Approved"
    remarks: Optional[str] = None
    reference_document: Optional[str] = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v):
        if v not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"event_type must be one of {sorted(ALLOWED_EVENT_TYPES)}")
        return v

    @field_validator("approval_status")
    @classmethod
    def validate_approval_status(cls, v):
        if v and v not in ("Pending", "Approved", "Rejected"):
            raise ValueError("approval_status must be Pending, Approved, or Rejected")
        return v


class LifecycleEventUpdate(BaseModel):
    event_type: Optional[str] = None
    event_date: Optional[date] = None
    effective_date: Optional[date] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    from_department: Optional[str] = None
    to_department: Optional[str] = None
    from_designation: Optional[str] = None
    to_designation: Optional[str] = None
    from_grade: Optional[str] = None
    to_grade: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    from_manager_id: Optional[int] = None
    to_manager_id: Optional[int] = None
    from_salary: Optional[str] = None
    to_salary: Optional[str] = None
    initiated_by: Optional[int] = None
    approved_by: Optional[int] = None
    approval_status: Optional[str] = None
    remarks: Optional[str] = None
    reference_document: Optional[str] = None


class LifecycleEventResponse(BaseModel):
    id: int
    employee_id: int
    event_type: str
    event_date: Optional[date] = None
    effective_date: Optional[date] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    from_department: Optional[str] = None
    to_department: Optional[str] = None
    from_designation: Optional[str] = None
    to_designation: Optional[str] = None
    from_grade: Optional[str] = None
    to_grade: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    from_manager_id: Optional[int] = None
    to_manager_id: Optional[int] = None
    from_salary: Optional[str] = None
    to_salary: Optional[str] = None
    initiated_by: Optional[int] = None
    approved_by: Optional[int] = None
    approval_status: Optional[str] = None
    remarks: Optional[str] = None
    reference_document: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LifecycleEventCount(BaseModel):
    event_type: str
    count: int


class LifecycleAnalyticsResponse(BaseModel):
    employee_id: int
    total_events: int
    events_by_type: List[LifecycleEventCount]
    tenure_days: Optional[int] = None
    joining_date: Optional[date] = None
    current_designation: Optional[str] = None
    current_department: Optional[str] = None
    promotions_count: int = 0
    transfers_count: int = 0
    is_confirmed: bool = False
    current_status: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# 2. Onboarding / Joining Tasks  (Joining Process tab)
# ══════════════════════════════════════════════════════════════════════════════

class OnboardingTaskCreate(BaseModel):
    employee_id: int
    task: str
    assigned_to: str
    due_date: Optional[date] = None
    status: Optional[str] = "pending"
    remarks: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"pending", "in-progress", "completed"}
        if v and v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class OnboardingTaskUpdate(BaseModel):
    task: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    remarks: Optional[str] = None


class OnboardingTaskResponse(BaseModel):
    id: int
    employee_id: int
    task: str
    assigned_to: str
    due_date: Optional[date] = None
    status: str
    completed_at: Optional[datetime] = None
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Probation Reviews  (Active Employment tab)
# ══════════════════════════════════════════════════════════════════════════════

class ProbationReviewCreate(BaseModel):
    employee_id: int
    review_date: date
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    status: Optional[str] = "pending"
    remarks: Optional[str] = None


class ProbationReviewUpdate(BaseModel):
    review_date: Optional[date] = None
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    status: Optional[str] = None
    rating: Optional[str] = None
    remarks: Optional[str] = None
    eligibility_check_status: Optional[str] = None
    manager_review_status: Optional[str] = None
    letter_generation_status: Optional[str] = None


class ProbationReviewResponse(BaseModel):
    id: int
    employee_id: int
    review_date: date
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    status: str
    rating: Optional[str] = None
    remarks: Optional[str] = None
    eligibility_check_status: str
    manager_review_status: str
    letter_generation_status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Transfer Requests  (Transfers & Movements tab)
# ══════════════════════════════════════════════════════════════════════════════

class TransferRequestCreate(BaseModel):
    employee_id: int
    employee_name: Optional[str] = None
    transfer_type: str
    from_department: Optional[str] = None
    to_department: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    request_date: date
    effective_date: Optional[date] = None
    remarks: Optional[str] = None

    @field_validator("transfer_type")
    @classmethod
    def validate_transfer_type(cls, v):
        allowed = {"Inter-department", "Inter-location", "Internal Job Posting"}
        if v not in allowed:
            raise ValueError(f"transfer_type must be one of {allowed}")
        return v


class TransferRequestUpdate(BaseModel):
    transfer_type: Optional[str] = None
    from_department: Optional[str] = None
    to_department: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    effective_date: Optional[date] = None
    status: Optional[str] = None
    approved_by: Optional[int] = None
    workflow_stage: Optional[int] = None
    remarks: Optional[str] = None


class TransferRequestResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    transfer_type: str
    from_department: Optional[str] = None
    to_department: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    request_date: date
    effective_date: Optional[date] = None
    status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    workflow_stage: int
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Exit Processes  (Exit Management tab)
# ══════════════════════════════════════════════════════════════════════════════

class ExitProcessCreate(BaseModel):
    employee_id: int
    employee_name: Optional[str] = None
    resignation_date: Optional[date] = None
    notice_period_start: Optional[date] = None
    notice_period_end: Optional[date] = None
    last_working_day: Optional[date] = None
    exit_type: Optional[str] = None
    exit_reason: Optional[str] = None
    exit_remarks: Optional[str] = None


class ExitProcessUpdate(BaseModel):
    resignation_date: Optional[date] = None
    notice_period_start: Optional[date] = None
    notice_period_end: Optional[date] = None
    last_working_day: Optional[date] = None
    exit_type: Optional[str] = None
    exit_reason: Optional[str] = None
    exit_remarks: Optional[str] = None
    status: Optional[str] = None
    it_clearance: Optional[bool] = None
    admin_clearance: Optional[bool] = None
    finance_clearance: Optional[bool] = None
    hr_clearance: Optional[bool] = None
    relieving_letter_generated: Optional[bool] = None
    relieving_letter_date: Optional[date] = None


class ExitProcessResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    resignation_date: Optional[date] = None
    notice_period_start: Optional[date] = None
    notice_period_end: Optional[date] = None
    last_working_day: Optional[date] = None
    exit_type: Optional[str] = None
    exit_reason: Optional[str] = None
    exit_remarks: Optional[str] = None
    status: str
    it_clearance: bool
    admin_clearance: bool
    finance_clearance: bool
    hr_clearance: bool
    relieving_letter_generated: bool
    relieving_letter_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Computed field for clearance_pending count
class ExitProcessWithClearance(ExitProcessResponse):
    clearance_pending: int = 0  # computed by service


# ══════════════════════════════════════════════════════════════════════════════
# 6. Contract Renewals  (Dashboard / Active Employment)
# ══════════════════════════════════════════════════════════════════════════════

class ContractRenewalCreate(BaseModel):
    employee_id: int
    employee_name: Optional[str] = None
    contract_type: Optional[str] = None
    contract_start: Optional[date] = None
    contract_end: date
    renewal_status: Optional[str] = "pending"
    renewed_until: Optional[date] = None
    remarks: Optional[str] = None


class ContractRenewalUpdate(BaseModel):
    contract_type: Optional[str] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    renewal_status: Optional[str] = None
    renewed_until: Optional[date] = None
    remarks: Optional[str] = None


class ContractRenewalResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    contract_type: Optional[str] = None
    contract_start: Optional[date] = None
    contract_end: date
    renewal_status: str
    renewed_until: Optional[date] = None
    remarks: Optional[str] = None
    days_remaining: Optional[int] = None   # computed by service
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ══════════════════════════════════════════════════════════════════════════════
# 7. Dashboard Summary  (Lifecycle Dashboard tab)
# ══════════════════════════════════════════════════════════════════════════════

class LifecycleDashboardResponse(BaseModel):
    new_joinings_this_month: int = 0
    pending_probation_reviews: int = 0
    transfer_requests_awaiting: int = 0
    active_exits: int = 0
    total_active_employees: int = 0
    onboarding_tasks_total: int = 0
    transfer_requests_total: int = 0
    exit_processes_total: int = 0
    contract_renewals_total: int = 0


# ══════════════════════════════════════════════════════════════════════════════
# 8. Reports & Analytics  (Reports & Analytics tab)
# ══════════════════════════════════════════════════════════════════════════════

class ExitAnalyticsResponse(BaseModel):
    attrition_rate: float = 0.0
    voluntary_exits: int = 0
    involuntary_exits: int = 0
    avg_tenure_years: float = 0.0
    top_exit_reasons: List[dict] = []      # [{"reason": str, "percentage": float}]


class LifecycleReportItem(BaseModel):
    id: int
    report_name: str
    generated_date: date
    report_type: str                       # Exit Analysis / Joining / Headcount
    generated_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
