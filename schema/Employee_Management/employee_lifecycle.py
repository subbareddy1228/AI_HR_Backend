# schema/Employee_Management/employee_lifecycle.py
# Pydantic schemas for Employee Lifecycle
# This file does NOT exist yet — create it here

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime


# ──────────────────────────────────────────────────────────────────────────────
# Generic (used by admin / migration endpoints)
# ──────────────────────────────────────────────────────────────────────────────

class LifecycleEventBase(BaseModel):
    employee_id: int
    stage: str
    status: Optional[str] = "PENDING"
    effective_date: date
    end_date: Optional[date] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    sub_type: Optional[str] = None
    remarks: Optional[str] = None
    initiated_by: Optional[int] = None
    approved_by: Optional[int] = None


class LifecycleEventCreate(LifecycleEventBase):
    pass


class LifecycleEventUpdate(BaseModel):
    status: Optional[str] = None
    end_date: Optional[date] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    remarks: Optional[str] = None
    approved_by: Optional[int] = None


class LifecycleEventResponse(LifecycleEventBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Stage-specific request schemas
# ──────────────────────────────────────────────────────────────────────────────

class JoiningCreate(BaseModel):
    """Called when a candidate is converted to an employee."""
    employee_id: int
    effective_date: date
    remarks: Optional[str] = None
    initiated_by: Optional[int] = None


class ProbationCreate(BaseModel):
    """Start a probation period for a new joiner."""
    employee_id: int
    effective_date: date       # probation start date
    end_date: date             # probation end date
    remarks: Optional[str] = None
    initiated_by: Optional[int] = None


class ProbationReview(BaseModel):
    """
    HR / Manager submits the probation review outcome.
    status must be: CONFIRMED | EXTENDED | TERMINATED
    """
    status: str
    end_date: Optional[date] = None    # new end date if extended
    remarks: Optional[str] = None
    approved_by: Optional[int] = None


class TransferCreate(BaseModel):
    """Raise a transfer request."""
    employee_id: int
    from_value: str            # current department or location
    to_value: str              # target department or location
    sub_type: str              # INTER_DEPARTMENT | INTER_LOCATION | INTER_COMPANY
    effective_date: date
    remarks: Optional[str] = None
    initiated_by: Optional[int] = None


class PromotionCreate(BaseModel):
    """Raise a promotion request."""
    employee_id: int
    from_value: str            # current designation
    to_value: str              # new designation
    effective_date: date
    remarks: Optional[str] = None
    initiated_by: Optional[int] = None


class ExitCreate(BaseModel):
    """Start the exit process for an employee."""
    employee_id: int
    sub_type: str              # RESIGNATION | TERMINATION | RETIREMENT | ABSCONDING
    effective_date: date       # resignation submission / notice start date
    end_date: Optional[date] = None    # last working day
    remarks: Optional[str] = None
    initiated_by: Optional[int] = None


class StatusUpdate(BaseModel):
    """
    Generic approve / reject / complete action for any PENDING event.
    Used by the /action endpoint.
    status: APPROVED | REJECTED | COMPLETED | CANCELLED
    """
    status: str
    remarks: Optional[str] = None
    approved_by: Optional[int] = None


# ──────────────────────────────────────────────────────────────────────────────
# Timeline response
# ──────────────────────────────────────────────────────────────────────────────

class EmployeeTimeline(BaseModel):
    """Full lifecycle timeline for one employee."""
    employee_id: int
    events: List[LifecycleEventResponse]
