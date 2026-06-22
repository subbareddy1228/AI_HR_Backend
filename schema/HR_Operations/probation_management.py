# schema/HR_Operations/probation_management.py

from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, List


class EmployeeBasic(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    employee_code: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    official_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Create ────────────────────────────────────────────────────────────────────
class ProbationCreate(BaseModel):
    employee_id:          int
    probation_start_date: date
    probation_end_date:   date
    buddy_id:             Optional[int]  = None
    reviewed_by:          Optional[int]  = None
    remarks:              Optional[str]  = None


# ── Update ────────────────────────────────────────────────────────────────────
class ProbationUpdate(BaseModel):
    probation_end_date:   Optional[date] = None
    extended_end_date:    Optional[date] = None
    milestone_30_status:  Optional[str]  = None   # Exceeds | Meets | Needs | N/A
    milestone_60_status:  Optional[str]  = None
    milestone_90_status:  Optional[str]  = None
    milestone_30_date:    Optional[date] = None
    milestone_60_date:    Optional[date] = None
    milestone_90_date:    Optional[date] = None
    progress_percentage:  Optional[int]  = None
    risk_level:           Optional[str]  = None   # Low | Medium | High
    status:               Optional[str]  = None
    buddy_id:             Optional[int]  = None
    reviewed_by:          Optional[int]  = None
    review_date:          Optional[date] = None
    remarks:              Optional[str]  = None
    auto_scheduled:       Optional[bool] = None


# ── Response ──────────────────────────────────────────────────────────────────
class ProbationResponse(BaseModel):
    id:                   int
    employee_id:          int
    employee:             Optional[EmployeeBasic] = None
    probation_start_date: date
    probation_end_date:   date
    extended_end_date:    Optional[date]
    milestone_30_status:  Optional[str]
    milestone_60_status:  Optional[str]
    milestone_90_status:  Optional[str]
    milestone_30_date:    Optional[date]
    milestone_60_date:    Optional[date]
    milestone_90_date:    Optional[date]
    progress_percentage:  int
    risk_level:           str
    status:               str
    buddy_id:             Optional[int]
    reviewed_by:          Optional[int]
    review_date:          Optional[date]
    remarks:              Optional[str]
    auto_scheduled:       bool
    created_at:           datetime
    updated_at:           datetime

    model_config = ConfigDict(from_attributes=True)


# ── Dashboard stat cards ──────────────────────────────────────────────────────
class ProbationDashboard(BaseModel):
    total_probation:            int
    in_progress:                int
    at_risk:                    int
    ending_soon:                int    # within next 30 days
    extended:                   int
    avg_progress_pct:           float
    reviews_due_next_7_days:    int
