

from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime, date




class EmployeeReportStats(BaseModel):
    total_headcount: int
    active_employees: int
    retention_rate_pct: float
    attrition_rate_pct: float
    avg_time_to_join_days: float
    promotion_rate_pct: float


class HeadcountDeptItem(BaseModel):
    department: str
    location: Optional[str]
    headcount: int
    growth_pct: float
    male: int
    female: int
    permanent: int
    contract: int
    intern: int


class AgeDistributionItem(BaseModel):
    age_range: str       
    count: int
    percentage: float


class TenureDistributionItem(BaseModel):
    tenure_range: str      
    count: int
    percentage: float


class GenderDiversityItem(BaseModel):
    department: str
    male: int
    female: int
    female_pct: float


class EmploymentTypeItem(BaseModel):
    department: str
    permanent: int
    contract: int
    intern: int


class LocationDistributionItem(BaseModel):
    location: str
    total_employees: int
    pct_of_total: float


class GradeLevelItem(BaseModel):
    grade: str
    count: int
    pct_of_total: float


class EmployeeListItem(BaseModel):
    name: str
    employee_id: str
    department: Optional[str]
    location: Optional[str]
    status: str
    grade: Optional[str]
    tenure: str
    joining_date: date


class NewJoinerItem(BaseModel):
    period: str
    count: int
    accepted: int
    declined: int


class AttritionAnalyticsItem(BaseModel):
    department: str
    location: Optional[str]
    total: int
    voluntary: int
    involuntary: int
    regrettable: int
    non_regrettable: int
    attrition_rate_pct: float
    avg_tenure: float


class AttritionTrendItem(BaseModel):
    period: str
    attrition_rate_pct: float
    voluntary_pct: float
    involuntary_pct: float


class AttritionReasonItem(BaseModel):
    reason: str
    count: int
    percentage: float


class ExitInterviewInsightItem(BaseModel):
    insight: str
    mentions: int
    severity: str           


class ReplacementCostItem(BaseModel):
    department: str
    avg_cost_per_hire: float
    total_replacement_cost: float
    hires_needed: int

class JoiningOnboardingItem(BaseModel):
    department: str
    location: Optional[str]
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


class OfferDeclineReasonItem(BaseModel):
    reason: str
    count: int
    percentage: float


class JoiningDateVarianceItem(BaseModel):
    department: str
    on_time: int
    delayed: int
    avg_variance_days: float


class EmployeeMovementItem(BaseModel):
    type: str              
    employee_name: str
    employee_id: str
    from_value: str
    to_value: str
    department: Optional[str]
    location: Optional[str]
    date: date
    salary_change_pct: Optional[float]
    effective_date: datetime


class SalaryRevisionItem(BaseModel):
    employee_name: str
    employee_id: str
    department: Optional[str]
    type: str
    old_salary: float
    new_salary: float
    change_pct: float
    effective_date: date


class DeptStrengthOverTimeItem(BaseModel):
    department: str
    oct_2023: int
    nov_2023: int
    dec_2023: int
    jan_2024: int
    feb_2024: int
    mar_2024: int
    trend: str            


class JoiningMetrics(BaseModel):
    offer_acceptance_rate: float
    onboarding_completion: float
    probation_completion: float
    first_year_attrition: float
