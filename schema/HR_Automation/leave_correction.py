"""
schemas/leave_correction.py
Pydantic v2 schemas for Leave Correction module.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────
# LEAVE TYPE OPTION  (dropdown values)
# All 9 types from the component's leaveTypes array
# ─────────────────────────────────────────────────────────

LEAVE_TYPE_OPTIONS = [
    {"code": "LV458",  "label": "LV458 - Comp Off"},
    {"code": "LV454",  "label": "LV454 - Present"},
    {"code": "LV455",  "label": "LV455 - Absent"},
    {"code": "LV456",  "label": "LV456 - Holiday"},
    {"code": "LV457",  "label": "LV457 - Week Off"},
    {"code": "LV459",  "label": "LV459 - Casual Leave"},
    {"code": "LV1055", "label": "LV1055 - Leave without Pay"},
    {"code": "LV2638", "label": "LV2638 - Sick Leave"},
    {"code": "LV2640", "label": "LV2640 - Half Day"},
]

LEAVE_TYPE_CODES = {opt["code"] for opt in LEAVE_TYPE_OPTIONS}


# ─────────────────────────────────────────────────────────
# PERIOD HELPERS
# ─────────────────────────────────────────────────────────

MONTH_LABELS = [
    "JAN","FEB","MAR","APR","MAY","JUN",
    "JUL","AUG","SEP","OCT","NOV","DEC",
]


def period_label(year: int, month: int) -> str:
    return f"{MONTH_LABELS[month - 1]}-{year}"


def parse_period(label: str) -> tuple[int, int]:
    parts = label.upper().split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid period '{label}'. Expected MMM-YYYY e.g. 'SEP-2025'.")
    month = MONTH_LABELS.index(parts[0]) + 1
    year  = int(parts[1])
    return year, month


# ─────────────────────────────────────────────────────────
# LEDGER ROW  (one row in the correction table)
# ─────────────────────────────────────────────────────────

class LeaveCorrectionRowOut(BaseModel):
    """
    One row in the Leave Correction table.
    Columns: EMPLOYEE (name + code) | DESIGNATION | OPENING | ACTIVITY | CORRECTION | CLOSING | save btn
    """
    id:               int
    employee_id:      str
    employee_name:    str
    employee_code:    str
    designation:      str
    business_unit:    str
    location:         str
    cost_center:      str
    department:       str

    leave_type_code:  str
    leave_type_label: str

    year:             int
    month:            int
    period_label:     str        # "SEP-2025"

    opening:          float      # read-only
    activity:         float      # read-only (ℹ tooltip: approved leaves used)
    correction:       float      # editable number input
    closing:          float      # read-only: opening + activity + correction

    is_saved:         bool
    saved_at:         Optional[datetime]
    updated_at:       Optional[datetime]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# LIST RESPONSE  (paginated)
# ─────────────────────────────────────────────────────────

class LeaveCorrectionListOut(BaseModel):
    total:            int
    page:             int
    page_size:        int
    total_pages:      int
    period_label:     str
    year:             int
    month:            int
    leave_type_code:  str
    leave_type_label: str
    items:            List[LeaveCorrectionRowOut]
    note:             str = "Corrections are added at the beginning of the period."


# ─────────────────────────────────────────────────────────
# SAVE ONE ROW  (green circle button)
# ─────────────────────────────────────────────────────────

class SaveCorrectionIn(BaseModel):
    """
    Payload for green circle save button on one row.
    HR edits only the `correction` field; all others are computed.
    """
    employee_id:     str
    leave_type_code: str
    year:            int  = Field(..., ge=2000, le=2100)
    month:           int  = Field(..., ge=1,    le=12)
    correction:      float = Field(..., description="Can be negative (debit) or positive (credit)")


# ─────────────────────────────────────────────────────────
# BULK SAVE  (save all visible rows)
# ─────────────────────────────────────────────────────────

class BulkSaveCorrectionIn(BaseModel):
    rows: List[SaveCorrectionIn]


# ─────────────────────────────────────────────────────────
# FILTER OPTIONS  (4 dropdowns)
# ─────────────────────────────────────────────────────────

class FilterOptionsOut(BaseModel):
    business_units:   List[str]
    locations:        List[str]
    cost_centers:     List[str]
    departments:      List[str]
    leave_type_options: List[dict]   # [{code, label}] for the leave type dropdown


# ─────────────────────────────────────────────────────────
# IMPORT RESULT  (Options → Upload)
# ─────────────────────────────────────────────────────────

class ImportResultOut(BaseModel):
    batch_id:         UUID
    filename:         str
    period_label:     str
    leave_type_code:  str
    total_rows:       int
    success_rows:     int
    failed_rows:      int
    errors:           List[dict]


# ─────────────────────────────────────────────────────────
# GENERIC
# ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
