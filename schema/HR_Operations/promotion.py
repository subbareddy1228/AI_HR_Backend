# schema/HR_Operations/promotion.py

from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional
from decimal import Decimal


class EmployeeBasic(BaseModel):
    id:             int
    first_name:     str
    last_name:      Optional[str] = None
    employee_code:  Optional[str] = None
    designation:    Optional[str] = None
    department:     Optional[str] = None
    location:       Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Create (New Nomination) ───────────────────────────────────────────────────
class PromotionCreate(BaseModel):
    employee_id:             int
    from_grade:              Optional[str]     = None
    to_grade:                Optional[str]     = None
    from_designation:        str
    to_designation:          str
    current_salary:          Optional[Decimal] = None
    revised_salary:          Optional[Decimal] = None
    salary_increase_percent: Optional[Decimal] = None   # auto-computed if omitted
    tenure_years:            Optional[Decimal] = None
    effective_date:          Optional[date]    = None
    nomination_date:         Optional[date]    = None
    reason:                  Optional[str]     = None


# ── Update (workflow + approval) ──────────────────────────────────────────────
class PromotionUpdate(BaseModel):
    # Status: Under Review | Approved | Rejected | Pending
    status:                  Optional[str]     = None
    revised_salary:          Optional[Decimal] = None
    salary_increase_percent: Optional[Decimal] = None
    effective_date:          Optional[date]    = None
    review_date:             Optional[date]    = None
    is_eligible:             Optional[bool]    = None
    # Approval workflow step flags
    step_m_done:             Optional[bool]    = None  # Manager
    step_d_done:             Optional[bool]    = None  # Director
    step_h_done:             Optional[bool]    = None  # HR
    step_p_done:             Optional[bool]    = None  # Panel
    step_l_done:             Optional[bool]    = None  # Leadership
    letter_generated:        Optional[bool]    = None
    approved_by:             Optional[int]     = None
    remarks:                 Optional[str]     = None


# ── Response ──────────────────────────────────────────────────────────────────
class PromotionResponse(BaseModel):
    id:                      int
    employee_id:             int
    employee:                Optional[EmployeeBasic] = None
    from_grade:              Optional[str]
    to_grade:                Optional[str]
    from_designation:        str
    to_designation:          str
    current_salary:          Optional[Decimal]
    revised_salary:          Optional[Decimal]
    salary_increase_percent: Optional[Decimal]
    tenure_years:            Optional[Decimal]
    status:                  str
    is_eligible:             bool
    approval_step:           int
    approval_total:          int
    step_m_done:             bool
    step_d_done:             bool
    step_h_done:             bool
    step_p_done:             bool
    step_l_done:             bool
    effective_date:          Optional[date]
    nomination_date:         Optional[date]
    review_date:             Optional[date]
    reason:                  Optional[str]
    letter_generated:        bool
    approved_by:             Optional[int]
    remarks:                 Optional[str]
    created_at:              datetime
    updated_at:              datetime

    model_config = ConfigDict(from_attributes=True)


# ── Dashboard stat cards ──────────────────────────────────────────────────────
class PromotionDashboard(BaseModel):
    total_nominations:          int
    approved:                   int
    approved_success_rate_pct:  float
    under_review:               int
    avg_salary_increase_pct:    float
    letters_generated:          int
    rejected:                   int
