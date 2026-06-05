# schema/Employee_Management/employee_lifecycle.py
# D5 - Employee Org & Lifecycle
# Pydantic schemas: Create / Update / Response / Analytics

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime

# ─── Allowed event types (for validation) ────────────────────────────────────
ALLOWED_EVENT_TYPES = {
    "Joining", "Probation_Start", "Probation_Extension", "Confirmation",
    "Promotion", "Demotion", "Department_Change", "Location_Change",
    "Manager_Change", "Designation_Change", "Grade_Change", "Salary_Revision",
    "Contract_Renewal", "Resignation", "Termination", "Retirement",
    "Rehire", "Transfer", "Suspension", "Reinstatement",
    "Work_Anniversary", "Background_Verification", "Training_Completion",
}


# ─── Create ───────────────────────────────────────────────────────────────────
class LifecycleEventCreate(BaseModel):
    employee_id: int
    event_type: str
    event_date: date
    effective_date: Optional[date] = None

    from_value: Optional[str] = None
    to_value: Optional[str] = None

    from_department: Optional[str] = None
    to_department: Optional[str] = None
    from_designation: Optional[str] = None
    to_designation: Optional[str] = None
    from_grade: Optional[str] = None
    to_grade: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    from_manager_id: Optional[int] = None
    to_manager_id: Optional[int] = None
    from_salary: Optional[str] = None
    to_salary: Optional[str] = None

    initiated_by: Optional[int] = None
    approved_by: Optional[int] = None
    approval_status: Optional[str] = "Approved"

    remarks: Optional[str] = None
    reference_document: Optional[str] = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v):
        if v not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"event_type must be one of {sorted(ALLOWED_EVENT_TYPES)}")
        return v

    @field_validator("approval_status")
    @classmethod
    def validate_approval_status(cls, v):
        if v and v not in ("Pending", "Approved", "Rejected"):
            raise ValueError("approval_status must be Pending, Approved, or Rejected")
        return v


# ─── Update ───────────────────────────────────────────────────────────────────
class LifecycleEventUpdate(BaseModel):
    event_type: Optional[str] = None
    event_date: Optional[date] = None
    effective_date: Optional[date] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    from_department: Optional[str] = None
    to_department: Optional[str] = None
    from_designation: Optional[str] = None
    to_designation: Optional[str] = None
    from_grade: Optional[str] = None
    to_grade: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    from_manager_id: Optional[int] = None
    to_manager_id: Optional[int] = None
    from_salary: Optional[str] = None
    to_salary: Optional[str] = None
    initiated_by: Optional[int] = None
    approved_by: Optional[int] = None
    approval_status: Optional[str] = None
    remarks: Optional[str] = None
    reference_document: Optional[str] = None


# ─── Response ─────────────────────────────────────────────────────────────────
class LifecycleEventResponse(BaseModel):
    id: int
    employee_id: int
    event_type: str
    event_date: Optional[date] = None
    effective_date: Optional[date] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    from_department: Optional[str] = None
    to_department: Optional[str] = None
    from_designation: Optional[str] = None
    to_designation: Optional[str] = None
    from_grade: Optional[str] = None
    to_grade: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    from_manager_id: Optional[int] = None
    to_manager_id: Optional[int] = None
    from_salary: Optional[str] = None
    to_salary: Optional[str] = None
    initiated_by: Optional[int] = None
    approved_by: Optional[int] = None
    approval_status: Optional[str] = None
    remarks: Optional[str] = None
    reference_document: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Analytics response schemas ───────────────────────────────────────────────
class LifecycleEventCount(BaseModel):
    event_type: str
    count: int


class LifecycleAnalyticsResponse(BaseModel):
    employee_id: int
    total_events: int
    events_by_type: List[LifecycleEventCount]
    tenure_days: Optional[int] = None
    joining_date: Optional[date] = None
    current_designation: Optional[str] = None
    current_department: Optional[str] = None
    promotions_count: int = 0
    transfers_count: int = 0
    is_confirmed: bool = False
    current_status: Optional[str] = None  # Active / Resigned / Terminated etc.
