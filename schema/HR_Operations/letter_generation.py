# from pydantic import BaseModel, ConfigDict
# from datetime import date, datetime
# from typing import Optional


# class LetterGenerationCreate(BaseModel):
#     employee_id: int
#     letter_type: str        # OFFER | APPOINTMENT | CONFIRMATION | RELIEVING | EXPERIENCE | SALARY | WARNING | TERMINATION
#     letter_date: date
#     subject: str
#     body: str
#     generated_by: Optional[int] = None


# class LetterGenerationUpdate(BaseModel):
#     subject: Optional[str] = None
#     body: Optional[str] = None
#     status: Optional[str] = None


# class LetterGenerationResponse(BaseModel):
#     id: int
#     employee_id: int
#     letter_type: str
#     letter_date: date
#     subject: str
#     body: str
#     generated_by: Optional[int]
#     status: str
#     created_at: datetime
#     updated_at: datetime

#     model_config = ConfigDict(from_attributes=True)
"""
schemas/hr_letters_schema.py
Pydantic V2 schemas for HR Letters module only
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
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


# ═══════════════════════════════════════════════════════════════════════════════
#  LETTER TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

class HRLetterTemplateCreate(BaseModel):
    name: str
    letter_type: LetterType
    subject: str
    body_html: str
    variables: Optional[List[str]] = None
    # variables = Jinja2 placeholder names e.g. ["employee_name", "joining_date"]

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Appointment Letter Template",
                "letter_type": "appointment",
                "subject": "Appointment Letter - {{employee_name}}",
                "body_html": "<p>Dear {{employee_name}},</p><p>We are pleased to offer you the position of {{designation}}.</p>",
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
    letter_type: LetterType
    subject: str
    body_html: str
    variables: Optional[List[str]] = None
    is_active: bool
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
#  ISSUED LETTERS
# ═══════════════════════════════════════════════════════════════════════════════

class HRLetterIssueRequest(BaseModel):
    employee_id: int
    template_id: Optional[int] = None      # if using a saved template
    letter_type: LetterType
    subject: str
    body_html: str                          # pre-rendered HTML content
    issued_on: Optional[date] = None
    notes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "employee_id": 42,
                "template_id": 3,
                "letter_type": "increment",
                "subject": "Salary Increment Letter - Priya Sharma",
                "body_html": "<p>Dear Priya, We are pleased to inform you of your salary increment.</p>",
                "issued_on": "2026-06-01",
                "notes": "Effective from June 2026"
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
    letter_type: LetterType
    subject: str
    body_html: str
    pdf_path: Optional[str] = None
    status: LetterStatus
    issued_by: int
    issued_on: Optional[date] = None
    sent_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
#  EMAIL
# ═══════════════════════════════════════════════════════════════════════════════

class SendLetterEmailRequest(BaseModel):
    letter_id: int
    recipient_email: str
    cc: Optional[List[str]] = None
    email_body: Optional[str] = None        # optional custom message; letter PDF attached

    model_config = {
        "json_schema_extra": {
            "example": {
                "letter_id": 5,
                "recipient_email": "priya@example.com",
                "cc": ["hr@company.com"],
                "email_body": "Please find your increment letter attached."
            }
        }
    }


class SendLetterEmailResponse(BaseModel):
    message: str
    letter_id: int
    recipient_email: str


# ═══════════════════════════════════════════════════════════════════════════════
#  DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════

class LetterDownloadResponse(BaseModel):
    download_url: str
    expires_in: int     # seconds