# schema/HR_Operations/employee_confirmation.py

from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional


class EmployeeBasic(BaseModel):
    id:             int
    first_name:     str
    last_name:      Optional[str] = None
    employee_code:  Optional[str] = None
    designation:    Optional[str] = None
    department:     Optional[str] = None
    location:       Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Create ────────────────────────────────────────────────────────────────────
class EmployeeConfirmationCreate(BaseModel):
    employee_id:  int
    due_date:     date
    reviewed_by:  Optional[int] = None
    remarks:      Optional[str] = None


# ── Update ────────────────────────────────────────────────────────────────────
class EmployeeConfirmationUpdate(BaseModel):
    # Status: Pending Approval | Confirmed | Extended | Terminated
    status:             Optional[str]  = None
    confirmation_date:  Optional[date] = None
    due_date:           Optional[date] = None
    # Performance: Exceeds Expectations | Meets Expectations | Needs Improvement | Unsatisfactory
    performance_rating: Optional[str]  = None
    auto_triggered:     Optional[bool] = None
    letter_sent:        Optional[bool] = None
    # Workflow step flags
    step_1_done:        Optional[bool] = None
    step_2_done:        Optional[bool] = None
    step_3_done:        Optional[bool] = None
    step_4_done:        Optional[bool] = None
    step_5_done:        Optional[bool] = None
    reviewed_by:        Optional[int]  = None
    remarks:            Optional[str]  = None


# ── Response ──────────────────────────────────────────────────────────────────
class EmployeeConfirmationResponse(BaseModel):
    id:                 int
    employee_id:        int
    employee:           Optional[EmployeeBasic] = None
    status:             str
    workflow_step:      int
    workflow_total:     int
    step_1_done:        bool
    step_2_done:        bool
    step_3_done:        bool
    step_4_done:        bool
    step_5_done:        bool
    due_date:           Optional[date]
    confirmation_date:  Optional[date]
    days_remaining:     Optional[int]   # computed at request time; negative = overdue
    performance_rating: Optional[str]
    auto_triggered:     bool
    letter_sent:        bool
    reviewed_by:        Optional[int]
    remarks:            Optional[str]
    created_at:         datetime
    updated_at:         datetime

    model_config = ConfigDict(from_attributes=True)


# ── Dashboard stat cards ──────────────────────────────────────────────────────
class ConfirmationDashboard(BaseModel):
    for_confirmation:   int
    confirmed:          int
    confirmed_rate_pct: float
    pending:            int
    overdue:            int
    auto_triggered:     int
    letters_sent:       int
