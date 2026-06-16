"""
routers/monthly_attendance.py
FastAPI router — Monthly Attendance module.
Prefix : /api/attendance/monthly
Auth   : JWT via existing get_current_user / require_hr_admin helpers
"""

import io
from typing import Optional, List
from datetime import date

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    Query, Path,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user

from schema.HR_Automation.monthly_attendance import (
    MonthlyAttendanceFilter, MonthlyCalendarOut,
    FilterOptionsOut, ReplaceShiftIn, ReplaceShiftOut,
    RecalculateIn, RecalculateOut, MessageResponse,
)
from services.HR_Automation.monthly_attendance_service import (
    FilterOptionsService, MonthlyCalendarService,
    RecalculateService, ReplaceShiftService, ExportService,
    LEGEND,
)

router = APIRouter(
    prefix="/api/attendance/monthly",
    tags=["Monthly Attendance"],
)


# ─────────────────────────────────────────────────────────
# FILTER OPTIONS  (populate 4 dropdowns on page load)
# GET /api/attendance/monthly/filter-options
# ─────────────────────────────────────────────────────────

@router.get("/filter-options", response_model=FilterOptionsOut)
def get_filter_options(
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    """
    Returns distinct values for Business Unit · Location · Cost Center · Department.
    Called once on page load to hydrate the 4 dropdowns.
    """
    return FilterOptionsService.get(db)


# ─────────────────────────────────────────────────────────
# LEGEND  (static — Icons & Legend section at bottom)
# GET /api/attendance/monthly/legend
# ─────────────────────────────────────────────────────────

# @router.get("/legend")
# def get_legend():
#     """
#     Returns the full Icons & Legend list shown below the calendar:
#     P · A · H · W · CO · CL · LW · SL · HD
#     with leave codes (LV454 … LV2640), labels, bg and text colours.
#     """
#     return {"legend": LEGEND}


# ─────────────────────────────────────────────────────────
# MAIN CALENDAR VIEW
# GET /api/attendance/monthly
# ─────────────────────────────────────────────────────────

@router.get("", response_model=MonthlyCalendarOut)
def get_monthly_calendar(
    # ── Month arrow navigation ──
    year:          int            = Query(..., ge=2000, le=2100,
                                          description="e.g. 2025"),
    month:         int            = Query(..., ge=1, le=12,
                                          description="1-12 — displayed as DEC-2025 in UI"),
    # ── Employee search box + View button ──
    employee_id:   str            = Query(...,
                                          description="Employee code e.g. LEV029"),
    # ── 4 dropdown filters ──
    business_unit: Optional[str]  = Query(None),
    location:      Optional[str]  = Query(None),
    cost_center:   Optional[str]  = Query(None),
    department:    Optional[str]  = Query(None),
    db:            Session        = Depends(get_db),
    current_user                  = Depends(get_current_user),
):
    """
    Main endpoint — powers the entire Monthly Attendance page.

    Returns:
    - Left panel : employee info card
                   (name, code, join date, exit date, location,
                    department, designation, default shift)
    - Right panel: 7-column calendar grid (SUN→SAT)
                   Each cell: day number | status badge (P/A/H/W/…)
                              | clock icon if has_punch
                              | bg_color + text_color for styling
    - Summary     : present/absent/holiday/week-off/leave counts
    - Legend      : full Icons & Legend list
    """
    f = MonthlyAttendanceFilter(
        year=year,
        month=month,
        employee_id=employee_id,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
    )
    return MonthlyCalendarService.get_calendar(db, f)


# ─────────────────────────────────────────────────────────
# RECALCULATE  (Recalculate button on left panel)
# POST /api/attendance/monthly/recalculate
# ─────────────────────────────────────────────────────────

@router.post("/recalculate", response_model=RecalculateOut)
def recalculate(
    payload:     RecalculateIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Recalculate button — rebuilds all MonthlyAttendanceCell rows for
    the employee+month from DailyAttendanceRecord, then refreshes the
    MonthlyAttendanceSummary counts.

    Use after:
    - Manual punch edits
    - Leave corrections
    - Regularization approvals
    """
    try:
        summary = RecalculateService.recalculate(
            db=db,
            employee_id=payload.employee_id,
            year=payload.year,
            month=payload.month,
        )
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    return {
        "message":    f"Recalculated attendance for {payload.employee_id} "
                      f"— {payload.year}-{payload.month:02d}.",
        "employee_id": payload.employee_id,
        "year":        payload.year,
        "month":       payload.month,
        "summary":     summary,
    }


# ─────────────────────────────────────────────────────────
# REPLACE SHIFT  (Replace button on left panel)
# POST /api/attendance/monthly/replace-shift
# ─────────────────────────────────────────────────────────

@router.post("/replace-shift", response_model=ReplaceShiftOut)
def replace_shift(
    payload:     ReplaceShiftIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Replace button — swaps the employee's default shift for the month.
    Updates Employee.default_shift, then triggers a recalculation so the
    calendar reflects the new shift timings immediately.
    Requires HR Admin role.
    """
    try:
        result = ReplaceShiftService.replace(
            db=db,
            employee_id=payload.employee_id,
            year=payload.year,
            month=payload.month,
            new_shift=payload.new_shift,
        )
        # Auto-recalculate after shift replacement
        RecalculateService.recalculate(
            db=db,
            employee_id=payload.employee_id,
            year=payload.year,
            month=payload.month,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    return result


# ─────────────────────────────────────────────────────────
# EXPORT CSV  (Options → Download)
# GET /api/attendance/monthly/export
# ─────────────────────────────────────────────────────────

@router.get("/export")
def export_csv(
    year:         int              = Query(..., ge=2000, le=2100),
    month:        int              = Query(..., ge=1, le=12),
    employee_ids: Optional[str]   = Query(None,
                                          description="Comma-separated employee codes. "
                                                      "Omit to export all employees."),
    db:           Session          = Depends(get_db),
    current_user                   = Depends(get_current_user),
):
    """
    Options → Download button.
    Exports the monthly attendance summary for one or all employees as CSV.

    Columns:
    employee_code · year · month · present · absent · holiday · week_off
    comp_off · casual_leave · leave_wo_pay · sick_leave · half_days
    late_days · total_worked_hours

    Filename: monthly_attendance_YYYY_MM.csv
    """
    emp_list = [e.strip() for e in employee_ids.split(",")] if employee_ids else None
    csv_bytes = ExportService.export_csv(db, year, month, emp_list)
    filename  = f"monthly_attendance_{year}_{month:02d}.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─────────────────────────────────────────────────────────
# SUMMARY  (aggregated counts for one employee+month)
# GET /api/attendance/monthly/{employee_id}/summary
# ─────────────────────────────────────────────────────────

# @router.get("/{employee_id}/summary")
# def get_summary(
#     employee_id: str     = Path(...),
#     year:        int     = Query(..., ge=2000, le=2100),
#     month:       int     = Query(..., ge=1, le=12),
#     db:          Session = Depends(get_db),
#     current_user         = Depends(get_current_user),
# ):
#     """
#     Returns the MonthlyAttendanceSummary counts for a single employee+month.
#     Used to show totals below the calendar (present/absent/leave counts).
#     """
#     from models.monthly_attendance import MonthlyAttendanceSummary
#     row = db.query(MonthlyAttendanceSummary).filter_by(
#         employee_id=employee_id, year=year, month=month
#     ).first()
#     if not row:
#         raise HTTPException(
#             status.HTTP_404_NOT_FOUND,
#             f"No summary found for {employee_id} — {year}-{month:02d}. "
#             f"Try hitting the Recalculate button first."
#         )
#     return {
#         "employee_id":       row.employee_id,
#         "year":              row.year,
#         "month":             row.month,
#         "present_days":      row.present_days,
#         "absent_days":       row.absent_days,
#         "holiday_days":      row.holiday_days,
#         "week_off_days":     row.week_off_days,
#         "comp_off_days":     row.comp_off_days,
#         "casual_leave":      row.casual_leave,
#         "leave_wo_pay":      row.leave_wo_pay,
#         "sick_leave":        row.sick_leave,
#         "half_days":         row.half_days,
#         "late_days":         row.late_days,
#         "total_worked_hours":round(row.total_worked_minutes / 60, 1),
#         "recalculated_at":   row.recalculated_at,
#     }
