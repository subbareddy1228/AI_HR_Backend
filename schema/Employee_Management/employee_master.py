# schema/HRMS/employee_reports.py

from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from enum import Enum


# ─────────────────────────────────────────
# Enums
# ─────────────────────────────────────────

class EmploymentTypeEnum(str, Enum):
    permanent = "Permanent"
    contract = "Contract"
    intern = "Intern"

class EmployeeStatusEnum(str, Enum):
    active = "Active"
    on_notice = "On Notice"
    resigned = "Resigned"
    terminated = "Terminated"

class MovementTypeEnum(str, Enum):
    promotion = "Promotion"
    transfer = "Transfer"
    designation_change = "Designation Change"
    department_change = "Department Change"
    inter_location_transfer = "Inter-location Transfer"


# ─────────────────────────────────────────
# Headcount & Demographics
# ─────────────────────────────────────────

class HeadcountSummaryItem(BaseModel):
    department: str
    location: str
    headcount: int
    growth_pct: float
    male: int
    female: int
    permanent: int
    contract: int
    intern: int

    model_config = {"from_attributes": True}


class DepartmentStrengthItem(BaseModel):
    department: str
    month: str       # e.g. "Oct 2023"
    headcount: int

    model_config = {"from_attributes": True}


class AgeDistributionItem(BaseModel):
    age_group: str   # e.g. "20-25"
    count: int
    percentage: float

    model_config = {"from_attributes": True}


class TenureDistributionItem(BaseModel):
    tenure_group: str  # e.g. "0-1 years"
    count: int
    percentage: float

    model_config = {"from_attributes": True}


class GenderDiversityItem(BaseModel):
    department: str
    male: int
    female: int
    female_pct: float

    model_config = {"from_attributes": True}


class EmploymentTypeBreakdownItem(BaseModel):
    department: str
    permanent: int
    contract: int
    intern: int

    model_config = {"from_attributes": True}


class LocationDistributionItem(BaseModel):
    location: str
    total_employees: int
    percentage: float

    model_config = {"from_attributes": True}


class GradeDistributionItem(BaseModel):
    grade: str
    count: int
    percentage: float

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# Employee List
# ─────────────────────────────────────────

class EmployeeListItem(BaseModel):
    employee_id: str
    full_name: str
    department: Optional[str]
    location: Optional[str]
    status: str
    grade: Optional[str]
    tenure: str           # calculated e.g. "2.5 years"
    joining_date: Optional[date]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# Attrition Analytics
# ─────────────────────────────────────────

class AttritionAnalyticsItem(BaseModel):
    department: str
    location: str
    total: int
    voluntary: int
    involuntary: int
    regrettable: int
    non_regrettable: int
    attrition_rate_pct: float
    avg_tenure: float

    model_config = {"from_attributes": True}


class AttritionTrendItem(BaseModel):
    period: str           # e.g. "7.2"
    attrition_rate_pct: float
    voluntary_pct: float
    involuntary_pct: float

    model_config = {"from_attributes": True}


class AttritionReasonItem(BaseModel):
    reason: str
    count: int
    percentage: float

    model_config = {"from_attributes": True}


class ExitInterviewInsightItem(BaseModel):
    insight: str
    mentions: int
    severity: str   # "High" | "Medium" | "Low"

    model_config = {"from_attributes": True}


class ReplacementCostItem(BaseModel):
    department: str
    avg_cost_per_hire: float
    total_replacement_cost: float
    hires_needed: int

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# Joining & Onboarding
# ─────────────────────────────────────────

class JoiningOnboardingItem(BaseModel):
    department: str
    location: str
    new_joiners: int
    accepted: int
    declined: int
    acceptance_rate_pct: float
    time_to_join_days: float
    joining_variance_days: float
    onboarding_complete: int
    onboarding_rate_pct: float
    probation_complete: int
    confirmation_rate_pct: float
    first_year_attrition: int
    first_year_attrition_rate_pct: float

    model_config = {"from_attributes": True}


class OfferDeclineReasonItem(BaseModel):
    reason: str
    count: int
    percentage: float

    model_config = {"from_attributes": True}


class JoiningVarianceItem(BaseModel):
    department: str
    on_time: int
    delayed: int
    avg_variance_days: float

    model_config = {"from_attributes": True}


class NewJoinerMonthlyItem(BaseModel):
    period: str
    count: int
    accepted: int
    declined: int

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# Employee Movement
# ─────────────────────────────────────────

class EmployeeMovementItem(BaseModel):
    movement_type: str
    employee_name: str
    employee_code: str
    from_value: Optional[str]
    to_value: Optional[str]
    department: Optional[str]
    location: Optional[str]
    movement_date: Optional[date]
    salary_change_pct: Optional[float]
    effective_date: Optional[date]

    model_config = {"from_attributes": True}


class SalaryRevisionItem(BaseModel):
    employee_name: str
    employee_code: str
    department: Optional[str]
    movement_type: str
    old_salary: Optional[float]
    new_salary: Optional[float]
    change_pct: Optional[float]
    effective_date: Optional[date]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# Summary KPIs (top of page)
# ─────────────────────────────────────────

class EmployeeReportKPIs(BaseModel):
    total_headcount: int
    active_employees: int
    retention_rate_pct: float
    attrition_rate_pct: float
    avg_time_to_join_days: float
    promotion_rate_pct: float

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# Available Reports Checklist
# ─────────────────────────────────────────

class AvailableReportItem(BaseModel):
    name: str
    available: bool

    model_config = {"from_attributes": True}


class AvailableReportsResponse(BaseModel):
    headcount_demographics: List[AvailableReportItem]
    attrition_analytics: List[AvailableReportItem]
    joining_movement: List[AvailableReportItem]

    model_config = {"from_attributes": True}
