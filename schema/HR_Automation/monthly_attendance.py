"""
schemas/monthly_attendance.py
Pydantic v2 request / response schemas for Monthly Attendance module.
"""

from __future__ import annotations
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field

from model.HR_Automation.monthly_attendance import DayStatusEnum


# ─────────────────────────────────────────────────────────
# EMPLOYEE INFO CARD  (left panel)
# ─────────────────────────────────────────────────────────

class EmployeeInfoOut(BaseModel):
    """
    Left-panel employee profile card.
    Fields: Name (Code) | Date of Joining | Date of Exit
            Location | Department | Designation | Default Shift
    + Replace button + Recalculate button
    """
    employee_id:   str
    name:          str
    code:          str
    join_date:     Optional[date]
    exit_date:     Optional[date]
    location:      str
    department:    str
    designation:   str
    default_shift: str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# CALENDAR CELL  (one coloured box in the grid)
# ─────────────────────────────────────────────────────────

class CalendarCellOut(BaseModel):
    """
    One cell in the 7-column calendar table.
    Empty cells (before day 1 or after last day) have day=None.
    """
    day:        Optional[int]           # 1-31 or None for padding cells
    date:       Optional[date]          # full date or None
    status:     Optional[DayStatusEnum] # P / A / H / W / CO / CL / LW / SL / HD
    has_punch:  bool = False            # clock icon shown top-right
    leave_code: Optional[str] = None    # e.g. "LV454"
    leave_label:Optional[str] = None    # e.g. "Present"
    # UI display colours (sent so frontend doesn't need a lookup table)
    bg_color:   str = "#ffffff"
    text_color: str = "#000000"


# ─────────────────────────────────────────────────────────
# CALENDAR WEEK  (one <tr> row in the table)
# ─────────────────────────────────────────────────────────

class CalendarWeekOut(BaseModel):
    week_number: int              # 1-based week index in the month
    cells:       List[CalendarCellOut]   # always 7 items (SUN→SAT)


# ─────────────────────────────────────────────────────────
# MONTHLY SUMMARY COUNTS
# ─────────────────────────────────────────────────────────

class MonthlySummaryOut(BaseModel):
    present_days:        int
    absent_days:         int
    holiday_days:        int
    week_off_days:       int
    comp_off_days:       int
    casual_leave:        int
    leave_wo_pay:        int
    sick_leave:          int
    half_days:           int
    late_days:           int
    total_worked_hours:  float   # total_worked_minutes / 60


# ─────────────────────────────────────────────────────────
# FULL CALENDAR RESPONSE
# ─────────────────────────────────────────────────────────

class MonthlyCalendarOut(BaseModel):
    """
    Complete response for GET /api/attendance/monthly.
    Drives both the left employee panel and the right calendar grid.
    """
    employee:   EmployeeInfoOut
    year:       int
    month:      int                    # 1–12
    month_label:str                    # "DEC-2025"
    weeks:      List[CalendarWeekOut]  # rows of the calendar table
    summary:    MonthlySummaryOut
    legend:     List[dict]             # the Icons & Legend section


# ─────────────────────────────────────────────────────────
# FILTER PARAMS
# ─────────────────────────────────────────────────────────

class MonthlyAttendanceFilter(BaseModel):
    year:          int             = Field(..., ge=2000, le=2100)
    month:         int             = Field(..., ge=1, le=12)
    employee_id:   str
    business_unit: Optional[str]  = None
    location:      Optional[str]  = None
    cost_center:   Optional[str]  = None
    department:    Optional[str]  = None


# ─────────────────────────────────────────────────────────
# REPLACE SHIFT REQUEST  (Replace button)
# ─────────────────────────────────────────────────────────

class ReplaceShiftIn(BaseModel):
    """
    Replace button → swap the employee's shift for the month.
    """
    employee_id: str
    year:        int
    month:       int
    new_shift:   str   # e.g. "Morning" / "General" / "Night"


class ReplaceShiftOut(BaseModel):
    message:    str
    employee_id:str
    new_shift:  str


# ─────────────────────────────────────────────────────────
# RECALCULATE REQUEST  (Recalculate button)
# ─────────────────────────────────────────────────────────

class RecalculateIn(BaseModel):
    employee_id: str
    year:        int
    month:       int


class RecalculateOut(BaseModel):
    message:    str
    employee_id:str
    year:       int
    month:      int
    summary:    MonthlySummaryOut


# ─────────────────────────────────────────────────────────
# FILTER OPTIONS  (4 dropdowns)
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
