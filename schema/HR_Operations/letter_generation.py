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