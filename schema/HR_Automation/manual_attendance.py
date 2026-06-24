"""
schemas/manual_attendance.py
Pydantic v2 schemas for Manual Attendance module.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from model.HR_Automation.leave_correction import ImportStatusEnum

# ─────────────────────────────────────────────────────────
# PERIOD HELPER
# ─────────────────────────────────────────────────────────

MONTH_LABELS = [
    "JAN","FEB","MAR","APR","MAY","JUN",
    "JUL","AUG","SEP","OCT","NOV","DEC",
]

def period_label(year: int, month: int) -> str:
    """e.g. 2025, 9 → 'SEP-2025'"""
    return f"{MONTH_LABELS[month - 1]}-{year}"

def parse_period(label: str) -> tuple[int, int]:
    """'SEP-2025' → (2025, 9)"""
    parts = label.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid period '{label}'. Expected MMM-YYYY e.g. 'SEP-2025'.")
    month = MONTH_LABELS.index(parts[0].upper()) + 1
    year  = int(parts[1])
    return year, month


# ─────────────────────────────────────────────────────────
# DAY-COUNT ROW (one employee's editable row in the table)
# ─────────────────────────────────────────────────────────

class AttendanceDayCounts(BaseModel):
    """
    The 7 editable number inputs per employee row.
    Matches exactly: P · A · H · W · CO · CL · LW
    All values ≥ 0.
    """
    P:  int = Field(0, ge=0, description="Present days")
    A:  int = Field(0, ge=0, description="Absent days")
    H:  int = Field(0, ge=0, description="Holiday days")
    W:  int = Field(0, ge=0, description="Week Off days")
    CO: int = Field(0, ge=0, description="Comp Off days")
    CL: int = Field(0, ge=0, description="Casual Leave days")
    LW: int = Field(0, ge=0, description="Leave Without Pay days")


# ─────────────────────────────────────────────────────────
# TABLE ROW  (one row in the attendance table)
# ─────────────────────────────────────────────────────────

class ManualAttendanceRowOut(BaseModel):
    """
    One row in the Manual Attendance table.
    Sl.No | Employee (name + code) | P | A | H | W | CO | CL | LW | Action (save toggle)
    """
    id:            int
    employee_id:   str
    employee_name: str
    employee_code: str
    business_unit: str
    location:      str
    cost_center:   str
    department:    str
    year:          int
    month:         int
    period_label:  str                # "SEP-2025"
    counts:        AttendanceDayCounts
    is_saved:      bool
    updated_at:    Optional[datetime]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# LIST RESPONSE  (paginated table)
# ─────────────────────────────────────────────────────────

class ManualAttendanceListOut(BaseModel):
    total:        int
    page:         int
    page_size:    int
    total_pages:  int
    period_label: str           # "SEP-2025"
    year:         int
    month:        int
    items:        List[ManualAttendanceRowOut]


# ─────────────────────────────────────────────────────────
# SAVE ONE ROW  (green toggle / save button per row)
# ─────────────────────────────────────────────────────────

class SaveAttendanceRowIn(BaseModel):
    """
    Payload sent when HR clicks the green save toggle on one row.
    employee_id + period + updated day-count values.
    """
    employee_id: str
    year:        int   = Field(..., ge=2000, le=2100)
    month:       int   = Field(..., ge=1,    le=12)
    counts:      AttendanceDayCounts

    @model_validator(mode="after")
    def total_days_sanity(self):
        total = (self.counts.P + self.counts.A + self.counts.H +
                 self.counts.W + self.counts.CO + self.counts.CL +
                 self.counts.LW)
        import calendar
        _, days_in_month = calendar.monthrange(self.year, self.month)
        if total > days_in_month:
            raise ValueError(
                f"Total days ({total}) exceeds days in month ({days_in_month})."
            )
        return self


# ─────────────────────────────────────────────────────────
# BULK SAVE  (future: save all rows at once)
# ─────────────────────────────────────────────────────────

class BulkSaveIn(BaseModel):
    year:  int
    month: int
    rows:  List[SaveAttendanceRowIn]


# ─────────────────────────────────────────────────────────
# FILTER OPTIONS  (populate 4 dropdowns)
# ─────────────────────────────────────────────────────────

class FilterOptionsOut(BaseModel):
    business_units: List[str]
    locations:      List[str]
    cost_centers:   List[str]
    departments:    List[str]


# ─────────────────────────────────────────────────────────
# DOWNLOAD MODAL  (Options → Download Attendance)
# Period is already known from the page; modal adds 3 filter dropdowns.
# ─────────────────────────────────────────────────────────

class DownloadAttendanceIn(BaseModel):
    year:        int
    month:       int
    location:    Optional[str] = None
    cost_center: Optional[str] = None
    department:  Optional[str] = None


# ─────────────────────────────────────────────────────────
# IMPORT RESULT  (Options → Upload Attendance)
# ─────────────────────────────────────────────────────────

class ImportResultOut(BaseModel):
    batch_id:     UUID
    filename:     str
    period_label: str
    total_rows:   int
    success_rows: int
    failed_rows:  int
    errors:       List[dict]   # [{row, employee_id, error}]


# ─────────────────────────────────────────────────────────
# GENERIC
# ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
