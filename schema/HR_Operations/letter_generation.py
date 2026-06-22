"""
schema/HR_Operations/letter_generation.py

Pydantic schemas for the HR Letter Generation module.
"""

from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
from typing import Optional, List


# ======================================================
# TEMPLATE SCHEMAS
# ======================================================
class LetterTemplateCreate(BaseModel):
    name: str
    code: str
    category: str                # Employment | Financial | Exit | Legal | Career | Disciplinary
    description: Optional[str] = None
    template_body: str
    subject_template: str
    is_ai_optimized: bool = True
    auto_approve: bool = False


class LetterTemplateUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    template_body: Optional[str] = None
    subject_template: Optional[str] = None
    is_ai_optimized: Optional[bool] = None
    auto_approve: Optional[bool] = None
    is_active: Optional[bool] = None


class LetterTemplateResponse(BaseModel):
    id: int
    name: str
    code: str
    category: str
    description: Optional[str]
    template_body: str
    subject_template: str
    is_ai_optimized: bool
    auto_approve: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# LETTER REQUEST SCHEMAS
# ======================================================
class LetterRequestCreate(BaseModel):
    employee_id: int
    template_id: Optional[int] = None
    letter_type: str
    subject: Optional[str] = None          # auto-filled from template if omitted
    body: Optional[str] = None             # auto-filled from template if omitted
    letter_date: Optional[date] = None     # defaults to today
    generated_by: Optional[int] = None
    # Extra fields used to fill {{placeholders}} in the template, e.g.
    # {"designation": "Software Engineer", "salary": "45000", "reason": "personal"}
    placeholders: Optional[dict] = None


class LetterRequestAIGenerate(BaseModel):
    """Payload for the 'AI' generate button on the dashboard."""
    employee_id: int
    letter_type: str
    template_id: Optional[int] = None
    tone: Optional[str] = Field(default="formal", description="formal | friendly | strict")
    extra_instructions: Optional[str] = None
    placeholders: Optional[dict] = None
    letter_date: Optional[date] = None
    generated_by: Optional[int] = None


class LetterRequestUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    letter_type: Optional[str] = None


class LetterRequestApprove(BaseModel):
    approved_by: int


class LetterRequestReject(BaseModel):
    approved_by: int
    rejection_reason: str


class EmployeeMini(BaseModel):
    """Lightweight employee info embedded in letter request responses."""
    id: int
    employee_code: str
    full_name: str
    department: Optional[str] = None
    designation: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LetterRequestResponse(BaseModel):
    id: int
    request_code: str
    employee_id: int
    template_id: Optional[int]
    letter_type: str
    subject: str
    body: str
    status: str
    generated_by: Optional[int]
    approved_by: Optional[int]
    rejection_reason: Optional[str]
    is_ai_generated: bool
    auto_approved: bool
    letter_date: date
    approved_at: Optional[datetime]
    download_count: int
    created_at: datetime
    updated_at: datetime

    employee: Optional[EmployeeMini] = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================
# DASHBOARD / STATS SCHEMAS
# ======================================================
class CategoryCount(BaseModel):
    category: str
    count: int


class LetterDashboardStats(BaseModel):
    total_templates: int
    ai_optimized_templates: int
    total_requests: int
    approved_requests: int
    pending_requests: int
    rejected_requests: int
    auto_approved_requests: int
    total_downloads: int
    category_breakdown: List[CategoryCount]