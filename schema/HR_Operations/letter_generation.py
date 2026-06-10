"""
schema/HR_Operations/letter_generation.py
Pydantic V2 schemas for HR Letters module
"""

import json
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────────────────────

class LetterType(str, Enum):
    APPOINTMENT  = "appointment"
    CONFIRMATION = "confirmation"
    PROMOTION    = "promotion"
    INCREMENT    = "increment"
    WARNING      = "warning"
    TERMINATION  = "termination"
    EXPERIENCE   = "experience"
    RELIEVING    = "relieving"
    NOC          = "noc"
    TRANSFER     = "transfer"
    CUSTOM       = "custom"


class LetterStatus(str, Enum):
    DRAFT   = "draft"
    ISSUED  = "issued"
    SENT    = "sent"
    REVOKED = "revoked"


# ── Letter Templates ──────────────────────────────────────────────────────────

class HRLetterTemplateCreate(BaseModel):
    name: str
    letter_type: LetterType
    subject: str
    body_html: str
    variables: Optional[List[str]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Appointment Letter Template",
                "letter_type": "appointment",
                "subject": "Appointment Letter - {{employee_name}}",
                "body_html": "<p>Dear {{employee_name}},</p>",
                "variables": ["employee_name", "designation", "joining_date", "ctc"]
            }
        }
    }


class HRLetterTemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None


class HRLetterTemplateResponse(BaseModel):
    id: int
    name: str
    letter_type: str
    subject: str
    body_html: str
    variables: Optional[List[str]] = None
    is_active: bool
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("variables", mode="before")
    @classmethod
    def parse_variables(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v

    @field_validator("letter_type", mode="before")
    @classmethod
    def parse_letter_type(cls, v):
        if hasattr(v, 'value'):
            return v.value
        return str(v).lower()


# ── Issued Letters ────────────────────────────────────────────────────────────

class HRLetterIssueRequest(BaseModel):
    employee_id: int
    template_id: Optional[int] = None
    letter_type: LetterType
    subject: str
    body_html: str
    issued_on: Optional[date] = None
    notes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "employee_id": 1,
                "letter_type": "appointment",
                "subject": "Appointment Letter",
                "body_html": "<p>Dear Employee,</p>",
                "issued_on": "2026-06-05"
            }
        }
    }


class HRLetterStatusUpdate(BaseModel):
    status: LetterStatus
    revoke_reason: Optional[str] = None


class HRLetterResponse(BaseModel):
    id: int
    employee_id: int
    template_id: Optional[int] = None
    letter_type: str
    subject: str
    body_html: str
    pdf_path: Optional[str] = None
    status: str
    issued_by: int
    issued_on: Optional[date] = None
    sent_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("letter_type", "status", mode="before")
    @classmethod
    def parse_enum_value(cls, v):
        if hasattr(v, 'value'):
            return v.value
        return str(v).lower()


# ── Email ─────────────────────────────────────────────────────────────────────

class SendLetterEmailRequest(BaseModel):
    letter_id: int
    recipient_email: str
    cc: Optional[List[str]] = None
    email_body: Optional[str] = None


class SendLetterEmailResponse(BaseModel):
    message: str
    letter_id: int
    recipient_email: str


# ── Download ──────────────────────────────────────────────────────────────────

class LetterDownloadResponse(BaseModel):
    download_url: str
    expires_in: int
"""
schema/HR_Operations/letter_settings.py
Pydantic V2 schemas for Settings, Workflow, Employee Portal, Reports
"""

import json
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, field_validator


# ═══════════════════════════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

class LetterSettingsUpdate(BaseModel):
    auto_approve_salary_certificate: Optional[bool] = None
    auto_approve_experience_certificate: Optional[bool] = None
    default_letter_format: Optional[str] = None
    audit_trail_retention_days: Optional[int] = None
    email_new_requests: Optional[bool] = None
    email_approvals: Optional[bool] = None
    email_downloads: Optional[bool] = None
    default_workflow_sla_hours: Optional[int] = None
    high_priority_sla_hours: Optional[int] = None
    medium_priority_sla_hours: Optional[int] = None
    low_priority_sla_hours: Optional[int] = None
    default_digital_signature: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "auto_approve_salary_certificate": True,
                "auto_approve_experience_certificate": False,
                "default_letter_format": "PDF",
                "audit_trail_retention_days": 30,
                "email_new_requests": True,
                "email_approvals": True,
                "email_downloads": False,
                "default_workflow_sla_hours": 24,
                "high_priority_sla_hours": 4,
                "medium_priority_sla_hours": 8,
                "low_priority_sla_hours": 24,
                "default_digital_signature": "Enable for all letters"
            }
        }
    }


class LetterSettingsResponse(BaseModel):
    id: int
    auto_approve_salary_certificate: bool
    auto_approve_experience_certificate: bool
    default_letter_format: str
    audit_trail_retention_days: int
    email_new_requests: bool
    email_approvals: bool
    email_downloads: bool
    default_workflow_sla_hours: int
    high_priority_sla_hours: int
    medium_priority_sla_hours: int
    low_priority_sla_hours: int
    default_digital_signature: str
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
#  LETTER REQUEST (Employee Portal + Workflow)
# ═══════════════════════════════════════════════════════════════════════════════

class LetterRequestCreate(BaseModel):
    letter_type: str
    purpose: Optional[str] = None
    priority: str = "medium"
    notes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "letter_type": "experience",
                "purpose": "CANADA VISA APPLICATION",
                "priority": "high",
                "notes": "Required urgently"
            }
        }
    }


class LetterRequestApprove(BaseModel):
    remarks: Optional[str] = None


class LetterRequestReject(BaseModel):
    reject_reason: str


class LetterApprovalStepResponse(BaseModel):
    id: int
    step_order: int
    approver_role: str
    approver_id: Optional[int] = None
    status: str
    actioned_at: Optional[datetime] = None
    remarks: Optional[str] = None

    model_config = {"from_attributes": True}


class LetterRequestResponse(BaseModel):
    id: int
    request_id: str
    employee_id: int
    letter_type: str
    purpose: Optional[str] = None
    priority: str
    status: str
    requested_by: int
    requested_at: datetime
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[int] = None
    rejected_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    hr_letter_id: Optional[int] = None
    notes: Optional[str] = None
    approval_steps: List[LetterApprovalStepResponse] = []

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
#  REPORTS
# ═══════════════════════════════════════════════════════════════════════════════

class LetterUsageReportResponse(BaseModel):
    total_requests: int
    approved: int
    pending: int
    rejected: int
    template_usage: List[dict]       # [{"letter_type": "experience", "count": N}]
    monthly_trends: List[dict]       # [{"month": "2024-03", "count": N}]
    approval_rate_pct: float
    avg_approval_time_hours: Optional[float] = None
    download_frequency: List[dict]   # [{"letter_type": "...", "downloads": N}]


class EmployeeWiseReportResponse(BaseModel):
    total_active_employees: int
    pending_requests: int
    employee_data: List[dict]        # per employee summary
    most_requested_letter_types: List[dict]
    department_wise: List[dict]