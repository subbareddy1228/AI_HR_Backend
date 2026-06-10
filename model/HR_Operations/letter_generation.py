"""
model/HR_Operations/letter_generation.py
SQLModel table definitions for HR Letters ONLY
(Resignation, Clearance, ExitInterview, FnFSettlement live in exit_management.py)
"""

from datetime import datetime, date
from typing import Optional, List
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship


# ─── Enums ────────────────────────────────────────────────────────────────────

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


# ─── HR Letter Template ───────────────────────────────────────────────────────

class HRLetterTemplate(SQLModel, table=True):
    __tablename__ = "hr_letter_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    letter_type: LetterType
    subject: str
    body_html: str
    variables: Optional[str] = None        # JSON list of variable names
    is_active: bool = Field(default=True)
    created_by: int = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)

    issued_letters: List["HRLetter"] = Relationship(back_populates="template")


# ─── Issued HR Letter ─────────────────────────────────────────────────────────

class HRLetter(SQLModel, table=True):
    __tablename__ = "hr_letters"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(index=True)
    template_id: Optional[int] = Field(default=None, foreign_key="hr_letter_templates.id")
    letter_type: LetterType
    subject: str
    body_html: str
    pdf_path: Optional[str] = None
    status: LetterStatus = Field(default=LetterStatus.DRAFT)
    issued_by: int = Field()
    issued_on: Optional[date] = None
    sent_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)

    template: Optional[HRLetterTemplate] = Relationship(back_populates="issued_letters")
"""
model/HR_Operations/letter_settings.py
Tables: LetterSettings, LetterApprovalWorkflow, LetterRequest, LetterApprovalStep
"""

from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class LetterSettings(SQLModel, table=True):
    __tablename__ = "letter_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Auto-approval
    auto_approve_salary_certificate: bool = Field(default=True)
    auto_approve_experience_certificate: bool = Field(default=False)
    # Default format
    default_letter_format: str = Field(default="PDF")
    # Audit trail retention in days
    audit_trail_retention_days: int = Field(default=30)
    # Notification settings
    email_new_requests: bool = Field(default=True)
    email_approvals: bool = Field(default=True)
    email_downloads: bool = Field(default=False)
    # SLA in hours
    default_workflow_sla_hours: int = Field(default=24)
    high_priority_sla_hours: int = Field(default=4)
    medium_priority_sla_hours: int = Field(default=8)
    low_priority_sla_hours: int = Field(default=24)
    # Digital signature
    default_digital_signature: str = Field(default="Enable for all letters")

    updated_by: Optional[int] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LetterRequest(SQLModel, table=True):
    __tablename__ = "letter_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(index=True)          # e.g. LTR-REQ-2024-001
    employee_id: int = Field(index=True)
    letter_type: str
    purpose: Optional[str] = None
    priority: str = Field(default="medium")      # high / medium / low
    status: str = Field(default="pending")       # pending / approved / rejected / generated
    requested_by: int
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[int] = None
    rejected_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    hr_letter_id: Optional[int] = None           # link to HRLetter once generated
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)

    approval_steps: List["LetterApprovalStep"] = Relationship(back_populates="request")


class LetterApprovalStep(SQLModel, table=True):
    __tablename__ = "letter_approval_steps"

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: int = Field(foreign_key="letter_requests.id", index=True)
    step_order: int
    approver_role: str                           # manager / hr / hr_admin
    approver_id: Optional[int] = None
    status: str = Field(default="pending")       # pending / approved / rejected / skipped
    actioned_at: Optional[datetime] = None
    remarks: Optional[str] = None

    request: Optional[LetterRequest] = Relationship(back_populates="approval_steps")