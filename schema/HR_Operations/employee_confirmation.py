"""
schema/HR_Operations/employee_confirmation.py

Pydantic schemas for the Employee Confirmation Management module.
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
# APPROVAL STAGE
# ======================================================
class ApprovalStageResponse(BaseModel):
    id: int
    confirmation_id: int
    stage_name: str
    stage_order: int
    status: str
    approver_id: Optional[int]
    acted_at: Optional[datetime]
    remarks: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ApprovalStageAction(BaseModel):
    stage_name: str = Field(description="MANAGER | HR | DEPT_HEAD | AUTHORITY")
    decision: str = Field(description="APPROVED | REJECTED")
    approver_id: Optional[int] = None
    remarks: Optional[str] = None


# ======================================================
# EMPLOYEE CONFIRMATION
# ======================================================
class EmployeeConfirmationCreate(BaseModel):
    employee_id: int
    probation_start_date: date
    probation_end_date: date
    reporting_manager_id: Optional[int] = None
    reviewed_by: Optional[int] = None
    remarks: Optional[str] = None


class EmployeeConfirmationUpdate(BaseModel):
    confirmation_date: Optional[date] = None
    performance_rating: Optional[str] = None    # EXCELLENT | GOOD | SATISFACTORY | POOR
    status: Optional[str] = None
    manager_recommendation: Optional[str] = None   # RECOMMENDED | CONDITIONAL | NOT_RECOMMENDED | PENDING
    reviewed_by: Optional[int] = None
    remarks: Optional[str] = None


class ExtendProbationRequest(BaseModel):
    extended_till: date
    remarks: Optional[str] = None


class EmployeeConfirmationResponse(BaseModel):
    id: int
    employee_id: int
    probation_start_date: date
    probation_end_date: date
    confirmation_date: Optional[date]
    performance_rating: Optional[str]
    status: str
    eligibility: str
    extension_count: int
    extended_till: Optional[date]
    manager_recommendation: str
    reporting_manager_id: Optional[int]
    reviewed_by: Optional[int]
    last_reminder_sent_at: Optional[datetime]
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    employee: Optional[EmployeeMini] = None
    approval_stages: List[ApprovalStageResponse] = []

    # computed time-status fields, e.g. "60 days overdue" vs "15 days" left
    days_until_due: Optional[int] = None
    is_overdue: bool = False

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# DASHBOARD / SUMMARY
# ======================================================
class ConfirmationDashboardStats(BaseModel):
    total: int
    pending_review: int
    pending_approval: int
    confirmed: int
    overdue: int
    due_this_week: int
class ConfirmationDashboard(BaseModel):
    for_confirmation: int
    confirmed: int
    confirmed_rate_pct: float
    pending: int
    overdue: int
    auto_triggered: int
    letters_sent: int

# ======================================================
# QUICK ACTIONS
# ======================================================
class SendRemindersResponse(BaseModel):
    employees_notified: int
    message: str


class ApprovePendingResponse(BaseModel):
    approvals_confirmed: int
    message: str


class AutoTriggerReviewsResponse(BaseModel):
    employees_triggered: int
    message: str


class BulkActionRequest(BaseModel):
    confirmation_ids: List[int]
    action: str = Field(description="SEND_REMINDER | APPROVE_PENDING | MARK_UNDER_REVIEW")


# ======================================================
# REPORTS
# ======================================================
class ConfirmationReportRequest(BaseModel):
    start_date: date
    end_date: date
    department: Optional[str] = None
    status: Optional[str] = None
    export_format: str = Field(default="JSON", description="JSON | CSV | PDF | EXCEL")


class ConfirmationReportPreview(BaseModel):
    total_records: int
    includes: List[str]