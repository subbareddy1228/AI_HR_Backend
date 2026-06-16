"""
schemas/shift_management.py
Pydantic v2 schemas for Shift Management & Rostering module (all 6 tabs).
"""

from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from model.HR_Automation.shift_management import (
    ShiftTypeEnum, RotationPatternEnum, RosterPeriodEnum,
    RosterStatusEnum, SwapStatusEnum, ArrangementTypeEnum,
    NotificationTypeEnum,
)


# ═══════════════════════════════════════════════════════════
# TAB 1 — SHIFT MASTER
# ═══════════════════════════════════════════════════════════

class BreakTimeIn(BaseModel):
    name:      str   = "Break"
    start_time:str   = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time:  str   = Field(..., pattern=r"^\d{2}:\d{2}$")
    duration:  int   = Field(60, ge=1)
    is_paid:   bool  = False
    mandatory: bool  = True
    auto_deduct:bool = True


class BreakTimeOut(BreakTimeIn):
    id: int
    model_config = {"from_attributes": True}


class ShiftCreateIn(BaseModel):
    name:                  str              = Field(..., max_length=100)
    code:                  str              = Field(..., max_length=20)
    shift_type:            ShiftTypeEnum    = ShiftTypeEnum.general
    start_time:            str              = Field("09:00", pattern=r"^\d{2}:\d{2}$")
    end_time:              str              = Field("18:00", pattern=r"^\d{2}:\d{2}$")
    duration_hours:        float            = Field(8.0, ge=0.5, le=24.0)
    grace_period_minutes:  int              = Field(15,  ge=0, le=120)
    week_offs:             List[str]        = []
    differential_pay:      float            = Field(1.0, ge=1.0, le=5.0)
    is_active:             bool             = True
    description:           str              = ""
    allow_multiple_per_day:bool             = False
    core_hours_start:      Optional[str]    = None   # flexible only
    core_hours_end:        Optional[str]    = None
    rotation_pattern:      Optional[RotationPatternEnum] = None  # rotational only
    break_times:           List[BreakTimeIn] = []

    @field_validator("week_offs")
    @classmethod
    def valid_days(cls, v):
        valid = {"Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"}
        for d in v:
            if d not in valid:
                raise ValueError(f"Invalid day: {d}")
        return v


class ShiftUpdateIn(BaseModel):
    name:                  Optional[str]             = None
    shift_type:            Optional[ShiftTypeEnum]   = None
    start_time:            Optional[str]             = None
    end_time:              Optional[str]             = None
    duration_hours:        Optional[float]           = None
    grace_period_minutes:  Optional[int]             = None
    week_offs:             Optional[List[str]]       = None
    differential_pay:      Optional[float]           = None
    is_active:             Optional[bool]            = None
    description:           Optional[str]             = None
    allow_multiple_per_day:Optional[bool]            = None
    core_hours_start:      Optional[str]             = None
    core_hours_end:        Optional[str]             = None
    rotation_pattern:      Optional[RotationPatternEnum] = None
    break_times:           Optional[List[BreakTimeIn]] = None


class ShiftOut(BaseModel):
    id:                    int
    name:                  str
    code:                  str
    shift_type:            ShiftTypeEnum
    start_time:            str
    end_time:              str
    duration_hours:        float
    grace_period_minutes:  int
    week_offs:             List[str]
    differential_pay:      float
    is_active:             bool
    description:           str
    allow_multiple_per_day:bool
    core_hours_start:      Optional[str]
    core_hours_end:        Optional[str]
    rotation_pattern:      Optional[RotationPatternEnum]
    break_times:           List[BreakTimeOut] = []
    created_at:            datetime

    model_config = {"from_attributes": True}

    @property
    def timing_display(self) -> str:
        """e.g. '09:00 - 18:00' shown in Shift Master table."""
        return f"{self.start_time} - {self.end_time}"

    @property
    def duration_display(self) -> str:
        return f"{int(self.duration_hours)} hrs"

    @property
    def week_offs_display(self) -> str:
        return ", ".join(self.week_offs) if self.week_offs else "None"

    @property
    def differential_pay_display(self) -> str:
        return f"{self.differential_pay}x"


# ═══════════════════════════════════════════════════════════
# TAB 2 — SHIFT ASSIGNMENT
# ═══════════════════════════════════════════════════════════

class BulkAssignIn(BaseModel):
    """Bulk Shift Assignment panel — Select Shift + checkbox list of employees."""
    shift_id:     int
    employee_ids: List[str] = Field(..., min_length=1)
    start_date:   date


class IndividualAssignIn(BaseModel):
    """Individual Assignment panel."""
    shift_id:    int
    employee_id: str
    start_date:  date
    end_date:    Optional[date] = None


class ShiftAssignmentOut(BaseModel):
    id:          int
    employee_id: str
    shift_id:    int
    shift_name:  str = ""
    start_date:  date
    end_date:    Optional[date]
    is_active:   bool
    assigned_at: datetime

    model_config = {"from_attributes": True}


class AssignmentUpdateIn(BaseModel):
    shift_id:  Optional[int]  = None
    end_date:  Optional[date] = None
    is_active: Optional[bool] = None


# ═══════════════════════════════════════════════════════════
# TAB 3 — ROSTERING
# ═══════════════════════════════════════════════════════════

class GenerateRosterIn(BaseModel):
    """
    Generate Roster button payload.
    shift_id + period + start_date → backend generates all days.
    """
    shift_id:         int
    period:           RosterPeriodEnum
    start_date:       date
    rotation_pattern: Optional[RotationPatternEnum] = None  # rotational shifts only
    rotation_shift_ids: List[int] = []  # additional shifts for rotation

class RosterDayOut(BaseModel):
    id:               int
    roster_date:      date
    day_of_week:      str
    shift_id:         Optional[int]
    shift_name:       str = ""
    shift_code:       str = ""
    is_week_off:      bool
    employees:        List[str]
    rotation_sequence:Optional[int]

    model_config = {"from_attributes": True}


class RosterOut(BaseModel):
    id:               int
    name:             str
    shift_id:         int
    shift_name:       str = ""
    period:           RosterPeriodEnum
    start_date:       date
    end_date:         date
    status:           RosterStatusEnum
    is_published:     bool
    published_at:     Optional[datetime]
    rotation_pattern: Optional[RotationPatternEnum]
    days:             List[RosterDayOut] = []
    created_at:       datetime

    model_config = {"from_attributes": True}


class PublishRosterOut(BaseModel):
    message:          str
    roster_id:        int
    notifications_sent: int


# ═══════════════════════════════════════════════════════════
# TAB 4 — SHIFT SWAP
# ═══════════════════════════════════════════════════════════

class SwapRequestIn(BaseModel):
    """New Swap Request modal payload."""
    employee_id:          str
    current_shift_id:     int
    requested_shift_id:   int
    swap_date:            date
    reason:               str = ""
    swap_with_employee_id:Optional[str] = None


class SwapApprovalIn(BaseModel):
    approved:         bool
    rejection_reason: Optional[str] = None


class SwapRequestOut(BaseModel):
    id:                   int
    employee_id:          str
    employee_name:        str = ""
    current_shift_id:     int
    current_shift_name:   str = ""
    requested_shift_id:   int
    requested_shift_name: str = ""
    swap_date:            date
    reason:               str
    status:               SwapStatusEnum
    requested_at:         datetime
    approved_at:          Optional[datetime]
    rejected_at:          Optional[datetime]
    rejection_reason:     Optional[str]

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════
# TAB 5 — FLEXIBLE WORK
# ═══════════════════════════════════════════════════════════

class FlexibleArrangementIn(BaseModel):
    """Flexible Work Arrangement modal payload."""
    employee_id:         str
    arrangement_type:    ArrangementTypeEnum
    core_hours_start:    str = Field("10:00", pattern=r"^\d{2}:\d{2}$")
    core_hours_end:      str = Field("16:00", pattern=r"^\d{2}:\d{2}$")
    flexible_start:      str = Field("08:00", pattern=r"^\d{2}:\d{2}$")
    flexible_end:        str = Field("20:00", pattern=r"^\d{2}:\d{2}$")
    remote_work_days:    List[str] = []
    office_days:         List[str] = []
    remote_days:         List[str] = []
    compressed_enabled:  bool      = False
    compressed_work_days:int       = Field(4, ge=3, le=5)
    compressed_hours_per_day:int   = Field(10, ge=8, le=12)


class FlexibleArrangementOut(BaseModel):
    id:                  int
    employee_id:         str
    employee_name:       str = ""
    arrangement_type:    ArrangementTypeEnum
    core_hours_start:    str
    core_hours_end:      str
    flexible_start:      str
    flexible_end:        str
    remote_work_days:    List[str]
    office_days:         List[str]
    remote_days:         List[str]
    compressed_enabled:  bool
    compressed_work_days:int
    compressed_hours_per_day:int
    is_active:           bool
    created_at:          datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════
# TAB 6 — WORK HOUR RULES
# ═══════════════════════════════════════════════════════════

class WorkHourRulesOut(BaseModel):
    # Late arrival
    late_grace_period_minutes:    int
    late_deduction_type:          str
    late_deduction_amount:        float
    late_enabled:                 bool
    late_max_allowed_per_month:   int
    # Early departure
    early_departure_allowed:      bool
    early_departure_requires_approval: bool
    early_departure_grace_minutes:int
    # Work hours
    min_work_hours:               float
    half_day_hours:               float
    half_day_consider:            bool
    # Short leave
    short_leave_max_duration_hours:float
    short_leave_requires_approval: bool
    # Weekend/Holiday
    weekend_requires_approval:    bool
    weekend_rate:                 float
    holiday_requires_approval:    bool
    holiday_rate:                 float
    holiday_can_take_comp_off:    bool
    # Overtime
    ot_weekday_rate:              float
    ot_weekend_rate:              float
    ot_holiday_rate:              float
    ot_night_shift_bonus:         float
    ot_cap_daily:                 float
    ot_cap_weekly:                float
    ot_cap_monthly:               float
    ot_compensation_type:         str
    # Break
    break_multiple_allowed:       bool
    break_max_duration_minutes:   int
    break_punch_required:         bool
    break_unpaid_threshold_minutes:int
    updated_at:                   datetime

    model_config = {"from_attributes": True}


class WorkHourRulesUpdate(BaseModel):
    # All fields optional — partial update
    late_grace_period_minutes:     Optional[int]   = None
    late_deduction_type:           Optional[str]   = None
    late_deduction_amount:         Optional[float] = None
    late_enabled:                  Optional[bool]  = None
    late_max_allowed_per_month:    Optional[int]   = None
    early_departure_allowed:       Optional[bool]  = None
    early_departure_requires_approval:Optional[bool]=None
    early_departure_grace_minutes: Optional[int]   = None
    min_work_hours:                Optional[float] = None
    half_day_hours:                Optional[float] = None
    half_day_consider:             Optional[bool]  = None
    short_leave_max_duration_hours:Optional[float] = None
    short_leave_requires_approval: Optional[bool]  = None
    weekend_requires_approval:     Optional[bool]  = None
    weekend_rate:                  Optional[float] = None
    holiday_requires_approval:     Optional[bool]  = None
    holiday_rate:                  Optional[float] = None
    holiday_can_take_comp_off:     Optional[bool]  = None
    ot_weekday_rate:               Optional[float] = None
    ot_weekend_rate:               Optional[float] = None
    ot_holiday_rate:               Optional[float] = None
    ot_night_shift_bonus:          Optional[float] = None
    ot_cap_daily:                  Optional[float] = None
    ot_cap_weekly:                 Optional[float] = None
    ot_cap_monthly:                Optional[float] = None
    ot_compensation_type:          Optional[str]   = None
    break_multiple_allowed:        Optional[bool]  = None
    break_max_duration_minutes:    Optional[int]   = None
    break_punch_required:          Optional[bool]  = None
    break_unpaid_threshold_minutes:Optional[int]   = None


# ═══════════════════════════════════════════════════════════
# NOTIFICATIONS  (Bell panel)
# ═══════════════════════════════════════════════════════════

class NotificationOut(BaseModel):
    id:          int
    type:        NotificationTypeEnum
    employee_id: str
    message:     str
    payload:     dict
    is_read:     bool
    created_at:  datetime

    model_config = {"from_attributes": True}


class MarkReadIn(BaseModel):
    notification_ids: Optional[List[int]] = None   # None = mark all


# ═══════════════════════════════════════════════════════════
# GENERIC
# ═══════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    message: str
