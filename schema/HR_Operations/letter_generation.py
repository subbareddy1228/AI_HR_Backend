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
Pydantic / SQLModel request & response schemas
for HR Operations — Letters & Exit Management
"""
 
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, validator
 
from model.HR_Operations.letter_generation import (
    LetterType, LetterStatus,
    ResignationStatus, ClearanceStatus, ClearanceDepartment,
    SettlementStatus,
)
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  HR LETTER TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════
 
class HRLetterTemplateCreate(BaseModel):
    name: str
    letter_type: LetterType
    subject: str
    body_html: str
    variables: Optional[List[str]] = None   # e.g. ["employee_name", "effective_date"]
 
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Appointment Letter Template",
                "letter_type": "appointment",
                "subject": "Appointment Letter — {{employee_name}}",
                "body_html": "<p>Dear {{employee_name}},</p><p>We are pleased to offer you ...</p>",
                "variables": ["employee_name", "designation", "joining_date", "ctc"]
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
    variables: Optional[List[str]]
    is_active: bool
    created_by: int
    created_at: datetime
 
    class Config:
        from_attributes = True
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  ISSUED HR LETTERS
# ═══════════════════════════════════════════════════════════════════════════════
 
class HRLetterIssueRequest(BaseModel):
    employee_id: int
    template_id: Optional[int] = None      # if using a saved template
    letter_type: LetterType
    subject: str
    body_html: str                          # pre-rendered or passed as-is
    issued_on: Optional[date] = None
    notes: Optional[str] = None
 
    class Config:
        json_schema_extra = {
            "example": {
                "employee_id": 42,
                "template_id": 3,
                "letter_type": "increment",
                "subject": "Salary Increment Letter — Priya Sharma",
                "body_html": "<p>Dear Priya, We are pleased to inform you ...</p>",
                "issued_on": "2026-06-01"
            }
        }
 
 
class HRLetterStatusUpdate(BaseModel):
    status: LetterStatus
    revoke_reason: Optional[str] = None
 
 
class HRLetterResponse(BaseModel):
    id: int
    employee_id: int
    template_id: Optional[int]
    letter_type: LetterType
    subject: str
    body_html: str
    pdf_path: Optional[str]
    status: LetterStatus
    issued_by: int
    issued_on: Optional[date]
    sent_at: Optional[datetime]
    created_at: datetime
 
    class Config:
        from_attributes = True
 
 
class SendLetterEmailRequest(BaseModel):
    letter_id: int
    recipient_email: str
    cc: Optional[List[str]] = None
    email_body: Optional[str] = None        # custom message; letter PDF attached
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  RESIGNATION
# ═══════════════════════════════════════════════════════════════════════════════
 
class ResignationCreate(BaseModel):
    resignation_date: date
    reason: Optional[str] = None
 
    @validator("resignation_date")
    def not_in_past(cls, v):
        if v < date.today():
            raise ValueError("Resignation date cannot be in the past.")
        return v
 
 
class ResignationAccept(BaseModel):
    last_working_day: date
    hr_remarks: Optional[str] = None
 
    @validator("last_working_day")
    def lwd_after_today(cls, v):
        if v <= date.today():
            raise ValueError("Last working day must be a future date.")
        return v
 
 
class ResignationResponse(BaseModel):
    id: int
    employee_id: int
    resignation_date: date
    last_working_day: Optional[date]
    notice_period_days: int
    reason: Optional[str]
    status: ResignationStatus
    accepted_by: Optional[int]
    accepted_at: Optional[datetime]
    hr_remarks: Optional[str]
    created_at: datetime
 
    class Config:
        from_attributes = True
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  CLEARANCE CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════
 
class ClearanceInitiateRequest(BaseModel):
    resignation_id: int
    # Optionally pass custom tasks; otherwise defaults are seeded
    custom_tasks: Optional[List[dict]] = None
    # e.g. [{"department": "IT", "task_description": "Return laptop"}]
 
 
class ClearanceItemUpdate(BaseModel):
    remarks: Optional[str] = None
 
 
class ClearanceItemResponse(BaseModel):
    id: int
    department: ClearanceDepartment
    task_description: str
    is_completed: bool
    completed_by: Optional[int]
    completed_at: Optional[datetime]
    remarks: Optional[str]
 
    class Config:
        from_attributes = True
 
 
class ClearanceChecklistResponse(BaseModel):
    id: int
    employee_id: int
    resignation_id: int
    overall_status: ClearanceStatus
    initiated_by: int
    initiated_at: datetime
    completed_at: Optional[datetime]
    items: List[ClearanceItemResponse]
 
    class Config:
        from_attributes = True
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  EXIT INTERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
 
class ExitInterviewSubmit(BaseModel):
    resignation_id: int
    reason_for_leaving: Optional[str] = None
    job_satisfaction_score: Optional[int] = Field(default=None, ge=1, le=10)
    management_score: Optional[int] = Field(default=None, ge=1, le=10)
    work_environment_score: Optional[int] = Field(default=None, ge=1, le=10)
    growth_opportunity_score: Optional[int] = Field(default=None, ge=1, le=10)
    would_rejoin: Optional[bool] = None
    suggestions: Optional[str] = None
    additional_comments: Optional[str] = None
 
 
class ExitInterviewResponse(BaseModel):
    id: int
    employee_id: int
    resignation_id: int
    reason_for_leaving: Optional[str]
    job_satisfaction_score: Optional[int]
    management_score: Optional[int]
    work_environment_score: Optional[int]
    growth_opportunity_score: Optional[int]
    would_rejoin: Optional[bool]
    suggestions: Optional[str]
    additional_comments: Optional[str]
    sentiment_label: Optional[str]
    sentiment_score: Optional[float]
    ai_summary: Optional[str]
    submitted_at: datetime
 
    class Config:
        from_attributes = True
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  FULL & FINAL SETTLEMENT
# ═══════════════════════════════════════════════════════════════════════════════
 
class FnFCalculateRequest(BaseModel):
    resignation_id: int
    basic_salary: float = Field(ge=0)
    hra: float = Field(default=0.0, ge=0)
    other_allowances: float = Field(default=0.0, ge=0)
    leave_encashment: float = Field(default=0.0, ge=0)
    gratuity: float = Field(default=0.0, ge=0)
    bonus_payout: float = Field(default=0.0, ge=0)
    notice_period_payment: float = Field(default=0.0, ge=0)
    notice_period_recovery: float = Field(default=0.0, ge=0)
    loan_recovery: float = Field(default=0.0, ge=0)
    advance_recovery: float = Field(default=0.0, ge=0)
    tax_deduction: float = Field(default=0.0, ge=0)
    other_deductions: float = Field(default=0.0, ge=0)
    remarks: Optional[str] = None
 
 
class FnFSettlementResponse(BaseModel):
    id: int
    employee_id: int
    resignation_id: int
    basic_salary: float
    hra: float
    other_allowances: float
    leave_encashment: float
    gratuity: float
    bonus_payout: float
    notice_period_payment: float
    notice_period_recovery: float
    loan_recovery: float
    advance_recovery: float
    tax_deduction: float
    other_deductions: float
    gross_earnings: float
    total_deductions: float
    net_payable: float
    status: SettlementStatus
    calculated_by: Optional[int]
    calculated_at: Optional[datetime]
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    paid_at: Optional[datetime]
    pdf_path: Optional[str]
    remarks: Optional[str]
 
    class Config:
        from_attributes = True
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
 
class ExitAnalyticsResponse(BaseModel):
    total_resignations: int
    accepted: int
    revoked: int
    pending: int
    avg_notice_period_days: float
    top_exit_reasons: List[dict]            # [{"reason": "...", "count": N}]
    monthly_attrition: List[dict]           # [{"month": "2026-05", "count": N}]
    sentiment_breakdown: dict               # {"positive": N, "neutral": N, "negative": N}
    avg_scores: dict                        # avg per exit interview dimension
    department_attrition: List[dict]        # [{"department": "...", "count": N}]