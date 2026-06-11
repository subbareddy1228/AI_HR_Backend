# schema/induction/induction.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


# ─── Induction Program ────────────────────────────────────────────────────────

class ProgramCreate(BaseModel):
    name:             str
    description:      Optional[str]  = None
    type:             str             = Field("batch", description="batch | individual")
    status:           str             = Field("Upcoming", description="Upcoming | Ongoing | Completed")
    start_date:       date
    end_date:         date
    max_participants: Optional[int]  = None


class ProgramUpdate(BaseModel):
    name:             Optional[str]  = None
    description:      Optional[str]  = None
    type:             Optional[str]  = None
    status:           Optional[str]  = None
    start_date:       Optional[date] = None
    end_date:         Optional[date] = None
    max_participants: Optional[int]  = None


class ProgramResponse(BaseModel):
    id:               int
    name:             str
    description:      Optional[str]
    type:             str
    status:           str
    start_date:       date
    end_date:         date
    max_participants: Optional[int]
    enrolled_count:   int = 0          # filled by service
    avg_rating:       float
    created_at:       datetime
    updated_at:       datetime

    class Config:
        from_attributes = True


# ─── Induction Participant (Employees List) ───────────────────────────────────

class ParticipantAdd(BaseModel):
    employee_id: int
    program_id:  int


class BulkParticipantAdd(BaseModel):
    employee_ids: List[int]
    program_id:   int


class AttendanceUpdate(BaseModel):
    attendance: str = Field(..., description="Present | Absent | Not Marked")


class BulkAttendanceUpdate(BaseModel):
    """Used by 'Mark Attendance' bulk action."""
    updates: List[dict]   # [{"employee_id": 1, "program_id": 2, "attendance": "Present"}, ...]


class ParticipantResponse(BaseModel):
    id:          int
    program_id:  int
    employee_id: int
    attendance:  str
    rating:      Optional[float]
    enrolled_at: datetime

    # Flattened employee fields for the Employees List table
    employee_name:   Optional[str] = None
    employee_code:   Optional[str] = None
    email:           Optional[str] = None
    mobile:          Optional[str] = None
    department:      Optional[str] = None
    designation:     Optional[str] = None
    joining_date:    Optional[date] = None
    program_name:    Optional[str] = None

    class Config:
        from_attributes = True


# ─── Session ─────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    program_id:   int
    title:        str
    description:  Optional[str]  = None
    session_date: date
    start_time:   str             = Field(..., example="9:00 AM")
    end_time:     str             = Field(..., example="10:30 AM")
    duration_hrs: Optional[float] = None
    mode:         str             = Field("on-site", description="on-site | virtual | hybrid")
    status:       str             = Field("Upcoming", description="Upcoming | Ongoing | Completed")


class SessionUpdate(BaseModel):
    title:        Optional[str]   = None
    description:  Optional[str]   = None
    session_date: Optional[date]  = None
    start_time:   Optional[str]   = None
    end_time:     Optional[str]   = None
    duration_hrs: Optional[float] = None
    mode:         Optional[str]   = None
    status:       Optional[str]   = None


class SessionResponse(BaseModel):
    id:           int
    program_id:   int
    program_name: Optional[str] = None   # joined from program
    title:        str
    description:  Optional[str]
    session_date: date
    start_time:   str
    end_time:     str
    duration_hrs: Optional[float]
    mode:         str
    status:       str
    created_at:   datetime

    class Config:
        from_attributes = True


# ─── Induction Policy ────────────────────────────────────────────────────────

class InductionPolicyCreate(BaseModel):
    title:          str
    category:       str   = Field(..., description="general | compliance | security")
    version:        str
    effective_date: date
    status:         str   = Field("Draft", description="Draft | Published | Mandatory")
    total_employees: int  = 0
    total_modules:   int  = 0


class InductionPolicyUpdate(BaseModel):
    title:           Optional[str]  = None
    category:        Optional[str]  = None
    version:         Optional[str]  = None
    effective_date:  Optional[date] = None
    status:          Optional[str]  = None
    total_modules:   Optional[int]  = None


class InductionPolicyResponse(BaseModel):
    id:                  int
    title:               str
    category:            str
    version:             str
    effective_date:      date
    status:              str
    total_employees:     int
    completed_employees: int
    completion_pct:      float = 0.0   # computed by service
    total_modules:       int
    created_at:          datetime

    class Config:
        from_attributes = True


# ─── Policy Acknowledgment ───────────────────────────────────────────────────

class AcknowledgmentUpdate(BaseModel):
    acknowledged:      bool
    modules_completed: Optional[int] = None


class AcknowledgmentResponse(BaseModel):
    id:                int
    policy_id:         int
    employee_id:       int
    acknowledged:      bool
    acknowledged_at:   Optional[datetime]
    modules_completed: int

    class Config:
        from_attributes = True


# ─── Dashboard Stats ─────────────────────────────────────────────────────────

class InductionStats(BaseModel):
    total_programs:    int
    total_participants: int
    policy_completion: float   # percentage e.g. 98.4
    avg_rating:        float   # e.g. 2.4