"""
schemas/daily_attendance.py
Pydantic v2 request / response schemas for Daily Attendance module.
"""

from __future__ import annotations
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from model.HR_Automation.daily_attendance import (
    AttendanceStatusEnum, PunchTypeEnum,
    PunchDirectionEnum, ShiftTypeEnum,
)


# ─────────────────────────────────────────────────────────
# TIMELINE  (the 3-bar shift timeline shown on each card)
# ─────────────────────────────────────────────────────────

class TimelineOut(BaseModel):
    """
    Represents the visual timeline bar shown on each attendance card.
    Green bar  → pre-shift window  (03:00A – 09:00A)
    Blue bar   → scheduled shift   (09:00A – 06:00P)
    Yellow bar → post-shift window (06:00P – 12:00A)
    """
    start:          str   # leftmost label  e.g. "03:00A"
    shift_start:    str   # e.g. "09:00A"
    shift_end:      str   # e.g. "06:00P"
    end:            str   # rightmost label e.g. "12:00A"
    shift_label:    str   # e.g. "General"


# ─────────────────────────────────────────────────────────
# PUNCH ENTRY  (one row in the "…" All Punches modal)
# ─────────────────────────────────────────────────────────

class PunchEntryOut(BaseModel):
    id:         UUID
    punch_time: datetime
    direction:  PunchDirectionEnum    # IN / OUT  → badge colour green/yellow
    punch_type: PunchTypeEnum         # label below time  e.g. "Selfie Punch"
    remarks:    str
    is_manual:  bool

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# ATTENDANCE CARD  (one card per employee shown in the list)
# ─────────────────────────────────────────────────────────

class AttendanceCardOut(BaseModel):
    """
    One card in the Daily Attendance view.

    Card header  → name (code) | location | designation | department
    Card body    → date label | status | note | timeline | in-time | + / … buttons
    """
    id:              int
    employee_id:     str
    employee_name:   str
    employee_code:   str
    designation:     str

    # Card header right side (icons + text)
    location:        str
    department:      str
    business_unit:   str
    cost_center:     str

    # Left info panel
    attendance_date: date
    status:          AttendanceStatusEnum
    note:            str
    shift_type:      ShiftTypeEnum

    # Timeline bar data
    timeline:        TimelineOut

    # Punch in/out shown below timeline bars
    punch_in:        Optional[str]   # formatted "09:17A" or "--"
    punch_out:       Optional[str]   # formatted "06:05P (Selfie)" or "-- (-)"
    punch_type_label:Optional[str]   # "Selfie" / "Manual" / …

    # Right panel
    in_time_display: str             # "8 h 35 m" formatted string

    # Raw punches for the "…" modal
    punches:         List[PunchEntryOut] = []

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# LIST RESPONSE  (the full scrollable card list)
# ─────────────────────────────────────────────────────────

class DailyAttendanceListOut(BaseModel):
    total:           int
    date:            date
    items:           List[AttendanceCardOut]


# ─────────────────────────────────────────────────────────
# FILTER QUERY PARAMS
# ─────────────────────────────────────────────────────────

class DailyAttendanceFilter(BaseModel):
    """
    Maps every filter control in the UI:
    4 dropdowns + 4 radio buttons + date arrow nav + employee search
    """
    attendance_date: date             = Field(default_factory=date.today)
    business_unit:   Optional[str]    = None   # None = "All Units"
    location:        Optional[str]    = None   # None = "All"
    cost_center:     Optional[str]    = None   # None = "All"
    department:      Optional[str]    = None   # None = "All"
    search:          Optional[str]    = None   # name / code / designation
    # Radio: all | late | absent | nopunch
    status_filter:   Optional[str]    = None


# ─────────────────────────────────────────────────────────
# ADD TIME PUNCH  (+ button modal → Insert)
# ─────────────────────────────────────────────────────────

class AddAttendancePunchIn(BaseModel):
    """
    Payload from the Add Time Punch modal.
    Fields: Employee Name (display) | Punch Date | Punch Time HH:MM:SS
            Punch Type (Selfie/Remote/Manual) | Remarks
    """
    employee_id:  str
    punch_date:   date
    punch_time:   str        = Field(..., pattern=r"^\d{2}:\d{2}:\d{2}$",
                                     description="HH:MM:SS from the three-field input")
    direction:    PunchDirectionEnum = PunchDirectionEnum.IN
    punch_type:   PunchTypeEnum      = PunchTypeEnum.manual
    remarks:      str                = ""

    @field_validator("punch_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        h, m, s = (int(x) for x in v.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
            raise ValueError("punch_time out of valid range")
        return v


class AddAttendancePunchOut(BaseModel):
    message:        str
    punch:          PunchEntryOut
    updated_record: AttendanceCardOut


# ─────────────────────────────────────────────────────────
# ALL PUNCHES MODAL  (… button)
# ─────────────────────────────────────────────────────────

class AllPunchesOut(BaseModel):
    employee_id:     str
    employee_name:   str
    employee_code:   str
    attendance_date: date
    punches:         List[PunchEntryOut]


class DeletePunchOut(BaseModel):
    message:         str
    punch_id:        UUID
    updated_record:  AttendanceCardOut


# ─────────────────────────────────────────────────────────
# FILTER OPTIONS  (populate the 4 dropdowns)
# ─────────────────────────────────────────────────────────

class FilterOptionsOut(BaseModel):
    business_units:  List[str]
    locations:       List[str]
    cost_centers:    List[str]
    departments:     List[str]


# ─────────────────────────────────────────────────────────
# IMPORT / EXPORT
# ─────────────────────────────────────────────────────────

class ImportResultOut(BaseModel):
    total_rows:   int
    success_rows: int
    failed_rows:  int
    errors:       List[dict]


# ─────────────────────────────────────────────────────────
# GENERIC
# ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
