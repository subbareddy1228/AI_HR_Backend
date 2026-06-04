# from pydantic import BaseModel, ConfigDict
# from datetime import date, datetime
# from typing import Optional


# class ExitManagementCreate(BaseModel):
#     employee_id: int
#     resignation_date: date
#     last_working_date: Optional[date] = None
#     exit_type: str          # RESIGNATION | TERMINATION | RETIREMENT | ABSCONDING
#     reason: Optional[str] = None
#     remarks: Optional[str] = None


# class ExitManagementUpdate(BaseModel):
#     last_working_date: Optional[date] = None
#     status: Optional[str] = None
#     exit_interview_done: Optional[str] = None
#     clearance_status: Optional[str] = None
#     remarks: Optional[str] = None


# class ExitManagementResponse(BaseModel):
#     id: int
#     employee_id: int
#     resignation_date: date
#     last_working_date: Optional[date]
#     exit_type: str
#     reason: Optional[str]
#     status: str
#     exit_interview_done: str
#     clearance_status: str
#     remarks: Optional[str]
#     created_at: datetime
#     updated_at: datetime

#     model_config = ConfigDict(from_attributes=True)
"""
schemas/exit_schema.py
Pydantic V2 schemas for Employee Separation & Exit Management module
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────────────────────

class ResignationStatus(str, Enum):
    PENDING  = "pending"
    ACCEPTED = "accepted"
    REVOKED  = "revoked"
    REJECTED = "rejected"


class ClearanceStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"


class ClearanceDepartment(str, Enum):
    IT      = "IT"
    FINANCE = "Finance"
    ADMIN   = "Admin"
    HR      = "HR"


class SettlementStatus(str, Enum):
    DRAFT      = "draft"
    CALCULATED = "calculated"
    APPROVED   = "approved"
    PAID       = "paid"


# ═══════════════════════════════════════════════════════════════════════════════
#  RESIGNATION
# ═══════════════════════════════════════════════════════════════════════════════

class ResignationCreate(BaseModel):
    resignation_date: date
    reason: Optional[str] = None

    @field_validator("resignation_date")
    @classmethod
    def not_in_past(cls, v):
        if v < date.today():
            raise ValueError("Resignation date cannot be in the past.")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "resignation_date": "2026-06-10",
                "reason": "Better opportunity"
            }
        }
    }


class ResignationAccept(BaseModel):
    last_working_day: date
    hr_remarks: Optional[str] = None

    @field_validator("last_working_day")
    @classmethod
    def lwd_after_today(cls, v):
        if v <= date.today():
            raise ValueError("Last working day must be a future date.")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "last_working_day": "2026-07-10",
                "hr_remarks": "Notice period of 30 days confirmed."
            }
        }
    }


class ResignationResponse(BaseModel):
    id: int
    employee_id: int
    resignation_date: date
    last_working_day: Optional[date] = None
    notice_period_days: int
    reason: Optional[str] = None
    status: ResignationStatus
    accepted_by: Optional[int] = None
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    hr_remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
#  NOTICE PERIOD
# ═══════════════════════════════════════════════════════════════════════════════

class NoticePeriodStatusResponse(BaseModel):
    employee_id: int
    resignation_date: date
    last_working_day: Optional[date] = None
    notice_period_days: int
    days_served: int
    days_remaining: int
    notice_served_pct: float


# ═══════════════════════════════════════════════════════════════════════════════
#  CLEARANCE CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════

class ClearanceTaskInput(BaseModel):
    department: ClearanceDepartment
    task_description: str


class ClearanceInitiateRequest(BaseModel):
    resignation_id: int
    custom_tasks: Optional[List[ClearanceTaskInput]] = None
    # if None, default tasks are seeded for IT / Finance / Admin / HR

    model_config = {
        "json_schema_extra": {
            "example": {
                "resignation_id": 12,
                "custom_tasks": [
                    {"department": "IT", "task_description": "Return laptop and peripherals"},
                    {"department": "Finance", "task_description": "Clear pending advances"}
                ]
            }
        }
    }


class ClearanceItemUpdate(BaseModel):
    remarks: Optional[str] = None


class ClearanceItemResponse(BaseModel):
    id: int
    department: ClearanceDepartment
    task_description: str
    is_completed: bool
    completed_by: Optional[int] = None
    completed_at: Optional[datetime] = None
    remarks: Optional[str] = None

    model_config = {"from_attributes": True}


class ClearanceChecklistResponse(BaseModel):
    id: int
    employee_id: int
    resignation_id: int
    overall_status: ClearanceStatus
    initiated_by: int
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    items: List[ClearanceItemResponse] = []

    model_config = {"from_attributes": True}


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

    model_config = {
        "json_schema_extra": {
            "example": {
                "resignation_id": 12,
                "reason_for_leaving": "Looking for better growth opportunities",
                "job_satisfaction_score": 7,
                "management_score": 8,
                "work_environment_score": 9,
                "growth_opportunity_score": 5,
                "would_rejoin": True,
                "suggestions": "More structured career growth paths would help.",
                "additional_comments": "Overall a good experience."
            }
        }
    }


class ExitInterviewResponse(BaseModel):
    id: int
    employee_id: int
    resignation_id: int
    reason_for_leaving: Optional[str] = None
    job_satisfaction_score: Optional[int] = None
    management_score: Optional[int] = None
    work_environment_score: Optional[int] = None
    growth_opportunity_score: Optional[int] = None
    would_rejoin: Optional[bool] = None
    suggestions: Optional[str] = None
    additional_comments: Optional[str] = None
    # AI-generated fields (filled asynchronously after submission)
    sentiment_label: Optional[str] = None      # positive / neutral / negative
    sentiment_score: Optional[float] = None    # 0.0 – 1.0
    ai_summary: Optional[str] = None
    submitted_at: datetime
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


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
    notice_period_payment: float = Field(default=0.0, ge=0)    # payment in lieu of notice
    notice_period_recovery: float = Field(default=0.0, ge=0)   # if notice not served fully
    loan_recovery: float = Field(default=0.0, ge=0)
    advance_recovery: float = Field(default=0.0, ge=0)
    tax_deduction: float = Field(default=0.0, ge=0)
    other_deductions: float = Field(default=0.0, ge=0)
    remarks: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "resignation_id": 12,
                "basic_salary": 50000,
                "hra": 20000,
                "other_allowances": 10000,
                "leave_encashment": 8000,
                "gratuity": 15000,
                "bonus_payout": 5000,
                "notice_period_payment": 0,
                "notice_period_recovery": 0,
                "loan_recovery": 0,
                "advance_recovery": 2000,
                "tax_deduction": 12000,
                "other_deductions": 0,
                "remarks": "All dues cleared"
            }
        }
    }


class FnFSettlementResponse(BaseModel):
    id: int
    employee_id: int
    resignation_id: int
    # Earnings
    basic_salary: float
    hra: float
    other_allowances: float
    leave_encashment: float
    gratuity: float
    bonus_payout: float
    notice_period_payment: float
    # Deductions
    notice_period_recovery: float
    loan_recovery: float
    advance_recovery: float
    tax_deduction: float
    other_deductions: float
    # Computed totals
    gross_earnings: float
    total_deductions: float
    net_payable: float
    # Status
    status: SettlementStatus
    calculated_by: Optional[int] = None
    calculated_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    pdf_path: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
#  SEPARATION LETTERS
# ═══════════════════════════════════════════════════════════════════════════════

class SeparationLetterRequest(BaseModel):
    letter_types: List[str]
    # accepted values: "experience", "relieving"

    model_config = {
        "json_schema_extra": {
            "example": {
                "letter_types": ["experience", "relieving"]
            }
        }
    }


class SeparationLetterResponse(BaseModel):
    message: str
    letter_ids: List[int]


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

class ExitAnalyticsResponse(BaseModel):
    total_resignations: int
    accepted: int
    revoked: int
    pending: int
    avg_notice_period_days: float
    top_exit_reasons: List[dict]        # [{"reason": "...", "count": N}]
    monthly_attrition: List[dict]       # [{"month": "2026-05", "count": N}]
    sentiment_breakdown: dict           # {"positive": N, "neutral": N, "negative": N}
    avg_scores: dict                    # avg per exit interview dimension
    department_attrition: List[dict]    # [{"department": "...", "count": N}]