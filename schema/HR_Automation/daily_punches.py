"""
schemas/daily_punches.py
Pydantic v2 request / response schemas for Daily Punches module.
"""

from __future__ import annotations
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from model.HR_Automation.daily_punches import (
    PunchSourceEnum, PunchDirectionEnum,
    PunchStatusEnum, AttendanceStatusEnum,
)


# ─────────────────────────────────────────────────────────
# INDIVIDUAL PUNCH
# ─────────────────────────────────────────────────────────

class PunchOut(BaseModel):
    id:                  UUID
    employee_id:         str
    punch_date:          date
    punch_time:          datetime
    direction:           PunchDirectionEnum
    source:              PunchSourceEnum
    status:              PunchStatusEnum
    latitude:            Optional[Decimal]
    longitude:           Optional[Decimal]
    location_url:        str
    location_name:       str
    selfie_path:         Optional[str]
    registered_face_path:Optional[str]
    remarks:             str
    is_manual:           bool
    created_at:          datetime

    model_config = {"from_attributes": True}


class AddPunchIn(BaseModel):
    """
    Payload for the 'Add Time Punch' modal (+ button on each row).
    Fields: Employee, Punch Date, Punch Time (HH MM SS), Punch Type, Remarks
    """
    employee_id:  str
    punch_date:   date
    punch_time:   str  = Field(..., pattern=r"^\d{2}:\d{2}:\d{2}$",
                               description="HH:MM:SS — from the three-field time input")
    direction:    PunchDirectionEnum = PunchDirectionEnum.IN
    source:       PunchSourceEnum    = PunchSourceEnum.manual
    remarks:      str                = ""
    latitude:     Optional[Decimal]  = None
    longitude:    Optional[Decimal]  = None
    location_url: str                = ""

    @field_validator("punch_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        h, m, s = (int(x) for x in v.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
            raise ValueError("punch_time out of range — must be HH:MM:SS")
        return v


class DeletePunchResponse(BaseModel):
    message:    str
    punch_id:   UUID


# ─────────────────────────────────────────────────────────
# DAILY PUNCH SUMMARY ROW  (one row in the main table)
# ─────────────────────────────────────────────────────────

class DailyPunchRowOut(BaseModel):
    """
    Represents one employee row in the Daily Punches table.
    Matches: SN | Employee | Designation | Start | End | Duration | Attendance | Actions
    """
    employee_id:         str
    employee_name:       str
    employee_code:       str
    designation:         str
    business_unit:       str
    location:            str
    cost_center:         str
    department:          str

    # Start column (first IN punch)
    first_in_time:       Optional[str]   = None   # formatted HH:MM:SS AM/PM
    first_in_selfie:     Optional[str]   = None   # URL for camera icon modal
    first_in_location:   Optional[str]   = None   # Google Maps embed URL
    has_start_selfie:    bool            = False
    has_start_location:  bool            = False

    # End column (last OUT punch)
    last_out_time:       Optional[str]   = None
    last_out_selfie:     Optional[str]   = None
    last_out_location:   Optional[str]   = None
    has_end_selfie:      bool            = False
    has_end_location:    bool            = False

    # Duration column  e.g. "8:58"
    duration:            str             = "0:00"

    # Attendance badge: P / A / L / HD / WO / H / OD
    attendance:          AttendanceStatusEnum

    # All raw punches for the "..." modal
    punches:             List[PunchOut]  = []

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# FILTER QUERY PARAMS
# ─────────────────────────────────────────────────────────

class DailyPunchFilter(BaseModel):
    """
    Maps to every filter control visible in the UI:
    Business Unit · Location · Cost Center · Departments
    Show All / Late Coming Only / Absent Only / No Punches
    Date picker · Employee search
    """
    punch_date:     date              = Field(default_factory=date.today)
    business_unit:  Optional[str]     = None   # None = "All Units"
    location:       Optional[str]     = None   # None = "All Locations"
    cost_center:    Optional[str]     = None   # None = "All Cost Centers"
    department:     Optional[str]     = None   # None = "All Departments"
    search:         Optional[str]     = None   # Employee name / code / designation
    status_filter:  Optional[str]     = None   # "late" | "absent" | "nopunch" | None = all
    page:           int               = Field(1, ge=1)
    page_size:      int               = Field(10, ge=1, le=200)


# ─────────────────────────────────────────────────────────
# PAGINATED RESPONSE
# ─────────────────────────────────────────────────────────

class DailyPunchListOut(BaseModel):
    total:      int
    page:       int
    page_size:  int
    total_pages:int
    date:       date
    items:      List[DailyPunchRowOut]


# ─────────────────────────────────────────────────────────
# SELFIE MODAL
# ─────────────────────────────────────────────────────────

class SelfieModalOut(BaseModel):
    """Response for clicking the camera icon on Start or End."""
    employee_id:          str
    employee_name:        str
    employee_code:        str
    registered_face_url:  Optional[str]
    punch_image_url:      Optional[str]


# ─────────────────────────────────────────────────────────
# LOCATION MODAL
# ─────────────────────────────────────────────────────────

class LocationModalOut(BaseModel):
    """Response for clicking the GPS pin icon on Start or End."""
    employee_id:    str
    employee_name:  str
    employee_code:  str
    latitude:       Optional[Decimal]
    longitude:      Optional[Decimal]
    location_url:   str   # Google Maps embed URL for the iframe
    location_name:  str


# ─────────────────────────────────────────────────────────
# ALL PUNCHES MODAL  (... button)
# ─────────────────────────────────────────────────────────

class AllPunchesOut(BaseModel):
    """Response for the '...' button → shows all raw punches for employee + date."""
    employee_id:    str
    employee_name:  str
    employee_code:  str
    punch_date:     date
    punches:        List[PunchOut]


# ─────────────────────────────────────────────────────────
# CSV / EXCEL IMPORT
# ─────────────────────────────────────────────────────────

class ImportResultOut(BaseModel):
    batch_id:       UUID
    filename:       str
    total_rows:     int
    success_rows:   int
    failed_rows:    int
    errors:         List[dict]   # [{row: int, error: str}]


# ─────────────────────────────────────────────────────────
# FILTER OPTIONS  (populate the 4 dropdowns)
# ─────────────────────────────────────────────────────────

class FilterOptionsOut(BaseModel):
    business_units: List[str]
    locations:      List[str]
    cost_centers:   List[str]
    departments:    List[str]


# ─────────────────────────────────────────────────────────
# GENERIC
# ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
