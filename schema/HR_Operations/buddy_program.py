# schema/HR_Operations/buddy_program.py

from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal


class EmployeeBasic(BaseModel):
    id:             int
    first_name:     str
    last_name:      Optional[str] = None
    employee_code:  Optional[str] = None
    designation:    Optional[str] = None
    department:     Optional[str] = None
    location:       Optional[str] = None
    official_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Buddy Create ──────────────────────────────────────────────────────────────
class BuddyCreate(BaseModel):
    buddy_employee_id:    int
    max_capacity:         Optional[int]  = 3
    experience_years:     Optional[int]  = None
    joined_as_buddy_date: Optional[date] = None
    remarks:              Optional[str]  = None


# ── Buddy Update ──────────────────────────────────────────────────────────────
class BuddyUpdate(BaseModel):
    status:           Optional[str]     = None   # Active | Inactive
    max_capacity:     Optional[int]     = None
    rating:           Optional[Decimal] = None
    experience_years: Optional[int]     = None
    remarks:          Optional[str]     = None


# ── Buddy Response ────────────────────────────────────────────────────────────
class BuddyResponse(BaseModel):
    id:                   int
    buddy_employee_id:    int
    buddy:                Optional[EmployeeBasic]       = None
    buddy_code:           Optional[str]
    status:               str
    rating:               Optional[Decimal]
    experience_years:     Optional[int]
    joined_as_buddy_date: Optional[date]
    max_capacity:         int
    current_assignments:  int
    capacity_pct:         float
    feedback_count:       int
    remarks:              Optional[str]
    assigned_new_joiners: List[EmployeeBasic]           = []
    created_at:           datetime
    updated_at:           datetime

    model_config = ConfigDict(from_attributes=True)


# ── Assignment Create ─────────────────────────────────────────────────────────
class BuddyAssignmentCreate(BaseModel):
    buddy_id:                  int
    new_joiner_employee_id:    int
    assigned_date:             Optional[date] = None
    end_date:                  Optional[date] = None


# ── Assignment Response ───────────────────────────────────────────────────────
class BuddyAssignmentResponse(BaseModel):
    id:                        int
    buddy_id:                  int
    new_joiner_employee_id:    int
    new_joiner:                Optional[EmployeeBasic] = None
    assigned_date:             Optional[date]
    end_date:                  Optional[date]
    is_active:                 bool
    feedback:                  Optional[str]
    feedback_date:             Optional[date]
    created_at:                datetime
    updated_at:                datetime

    model_config = ConfigDict(from_attributes=True)


# ── Feedback Submit ───────────────────────────────────────────────────────────
class BuddyFeedbackSubmit(BaseModel):
    assignment_id: int
    feedback:      str
    rating:        Optional[Decimal] = None


# ── Dashboard stat cards ──────────────────────────────────────────────────────
class BuddyDashboard(BaseModel):
    active_buddies:          int
    avg_rating:              float
    total_assignments:       int
    total_feedback_collected: int
    avg_experience_years:    float
    capacity_used_pct:       float
