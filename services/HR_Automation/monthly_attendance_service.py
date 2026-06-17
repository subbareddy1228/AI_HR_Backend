"""
services/monthly_attendance_service.py
Business logic for Monthly Attendance module.
"""

import csv
import io
import calendar
import logging
from datetime import date, datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from model.HR_Automation.monthly_attendance import (
    MonthlyAttendanceCell, MonthlyAttendanceSummary, DayStatusEnum,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# LEGEND  (matches exactly the Icons & Legend section in UI)
# ─────────────────────────────────────────────────────────

LEGEND = [
    {"code": "P",  "label": "LV454 - Present",           "color": "#007b83", "bg": "#d1f5ee"},
    {"code": "A",  "label": "LV455 - Absent",            "color": "#c82333", "bg": "#fcdada"},
    {"code": "H",  "label": "LV456 - Holiday",           "color": "#155724", "bg": "#d4edda"},
    {"code": "W",  "label": "LV457 - Week Off",          "color": "#555555", "bg": "#e0e0e0"},
    {"code": "CO", "label": "LV458 - Comp Off",          "color": "#856404", "bg": "#fff3cd"},
    {"code": "CL", "label": "LV459 - Casual Leave",      "color": "#004085", "bg": "#cce5ff"},
    {"code": "LW", "label": "LV1055 - Leave without Pay","color": "#383d41", "bg": "#e2e3e5"},
    {"code": "SL", "label": "LV2638 - Sick Leave",       "color": "#0c5460", "bg": "#d1ecf1"},
    {"code": "HD", "label": "LV2640 - Half Day",         "color": "#856404", "bg": "#fff3cd"},
    {"code": "L",  "label": "Late",                      "color": "#e67e22", "bg": "#fef9e7"},
]

# Quick lookups
_STATUS_BG   = {item["code"]: item["bg"]    for item in LEGEND}
_STATUS_TEXT = {item["code"]: item["color"] for item in LEGEND}


def _cell_colors(status: Optional[DayStatusEnum]) -> tuple[str, str]:
    if status is None:
        return "#ffffff", "#000000"
    return (
        _STATUS_BG.get(status.value,   "#ffffff"),
        _STATUS_TEXT.get(status.value, "#000000"),
    )


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

MONTH_LABELS = ["JAN","FEB","MAR","APR","MAY","JUN",
                "JUL","AUG","SEP","OCT","NOV","DEC"]


def _month_label(year: int, month: int) -> str:
    return f"{MONTH_LABELS[month - 1]}-{year}"


def _resolve_employee(db: Session, employee_id: str) -> dict:
    """Pull employee profile for the left-panel info card."""
    result = {
        "employee_id":   employee_id,
        "name":          employee_id,
        "code":          employee_id,
        "join_date":     None,
        "exit_date":     None,
        "location":      "",
        "department":    "",
        "designation":   "",
        "default_shift": "General",
    }
    try:
        from model.onboarding.employee import Employee
        emp = db.query(Employee).filter_by(employee_id=employee_id).first()
        if emp:
            result.update({
                "name":          emp.name,
                "code":          emp.employee_id,
                "join_date":     getattr(emp, "date_of_joining", None),
                "exit_date":     getattr(emp, "date_of_exit",    None),
                "location":      getattr(emp, "location",        ""),
                "department":    getattr(emp, "department",       ""),
                "designation":   getattr(emp, "position",         ""),
                "default_shift": getattr(emp, "default_shift",   "General"),
            })
    except ImportError:
        pass
    return result


def _build_calendar_weeks(
    year: int,
    month: int,
    cells_by_day: dict,          # {day_int: MonthlyAttendanceCell}
) -> list:
    """
    Build the 7-column (SUN→SAT) week rows for the calendar grid.
    Padding cells before day-1 and after the last day have day=None.
    """
    _, days_in_month = calendar.monthrange(year, month)
    first_weekday    = date(year, month, 1).weekday()   # Monday=0
    # Convert to Sunday-start (Sun=0 … Sat=6)
    first_col        = (first_weekday + 1) % 7

    all_cells = []

    # Leading empty padding
    for _ in range(first_col):
        all_cells.append({
            "day": None, "date": None, "status": None,
            "has_punch": False, "leave_code": None, "leave_label": None,
            "bg_color": "#ffffff", "text_color": "#000000",
        })

    # Actual days
    for day in range(1, days_in_month + 1):
        cell = cells_by_day.get(day)
        bg, fg = _cell_colors(cell.status if cell else None)
        all_cells.append({
            "day":        day,
            "date":       date(year, month, day),
            "status":     cell.status        if cell else None,
            "has_punch":  cell.has_punch     if cell else False,
            "leave_code": cell.leave_code    if cell else None,
            "leave_label":cell.leave_label   if cell else None,
            "bg_color":   bg,
            "text_color": fg,
        })

    # Trailing padding to complete last week
    remainder = len(all_cells) % 7
    if remainder:
        for _ in range(7 - remainder):
            all_cells.append({
                "day": None, "date": None, "status": None,
                "has_punch": False, "leave_code": None, "leave_label": None,
                "bg_color": "#ffffff", "text_color": "#000000",
            })

    # Chunk into weeks
    weeks = []
    for w_idx, offset in enumerate(range(0, len(all_cells), 7), start=1):
        weeks.append({
            "week_number": w_idx,
            "cells":       all_cells[offset: offset + 7],
        })
    return weeks


def _build_summary_counts(cells: list) -> dict:
    """Aggregate day-status counts from a list of MonthlyAttendanceCell."""
    counts = {
        "present_days": 0, "absent_days": 0, "holiday_days": 0,
        "week_off_days": 0, "comp_off_days": 0, "casual_leave": 0,
        "leave_wo_pay": 0, "sick_leave": 0, "half_days": 0,
        "late_days": 0, "total_worked_minutes": 0,
    }
    for c in cells:
        counts["total_worked_minutes"] += c.worked_minutes or 0
        if c.status == DayStatusEnum.P:  counts["present_days"]  += 1
        elif c.status == DayStatusEnum.A:  counts["absent_days"]   += 1
        elif c.status == DayStatusEnum.H:  counts["holiday_days"]  += 1
        elif c.status == DayStatusEnum.W:  counts["week_off_days"] += 1
        elif c.status == DayStatusEnum.CO: counts["comp_off_days"] += 1
        elif c.status == DayStatusEnum.CL: counts["casual_leave"]  += 1
        elif c.status == DayStatusEnum.LW: counts["leave_wo_pay"]  += 1
        elif c.status == DayStatusEnum.SL: counts["sick_leave"]    += 1
        elif c.status == DayStatusEnum.HD: counts["half_days"]     += 1
        elif c.status == DayStatusEnum.L:  counts["late_days"]     += 1
    return counts


# ═══════════════════════════════════════════════════════════
# FILTER OPTIONS
# ═══════════════════════════════════════════════════════════

class FilterOptionsService:

    @staticmethod
    def get(db: Session) -> dict:
        def _distinct(col):
            return sorted({
                v for (v,) in db.query(distinct(col)).filter(col.isnot(None)).all() if v
            })

        # Pull from employee table for org fields
        try:
            from model.onboarding.employee import Employee
            return {
                "business_units": ["All Units"]      + _distinct(Employee.business_unit),
                "locations":      ["All Locations"]  + _distinct(Employee.location),
                "cost_centers":   ["All Cost Centers"] + _distinct(Employee.cost_center),
                "departments":    ["All Departments"]+ _distinct(Employee.department),
            }
        except ImportError:
            return {
                "business_units": ["All Units"],
                "locations":      ["All Locations"],
                "cost_centers":   ["All Cost Centers"],
                "departments":    ["All Departments"],
            }


# ═══════════════════════════════════════════════════════════
# MAIN CALENDAR SERVICE
# ═══════════════════════════════════════════════════════════

class MonthlyCalendarService:

    @staticmethod
    def get_calendar(db: Session, f) -> dict:
        """
        Main query — powers the full calendar view response.
        Returns employee info + calendar weeks + summary counts + legend.
        """
        # All cells for this employee+month
        cells = (
            db.query(MonthlyAttendanceCell)
            .filter(
                MonthlyAttendanceCell.employee_id == f.employee_id,
                func.extract("year",  MonthlyAttendanceCell.cell_date) == f.year,
                func.extract("month", MonthlyAttendanceCell.cell_date) == f.month,
            )
            .order_by(MonthlyAttendanceCell.cell_date)
            .all()
        )

        cells_by_day = {c.cell_date.day: c for c in cells}

        # Employee profile
        employee = _resolve_employee(db, f.employee_id)

        # Calendar grid
        weeks = _build_calendar_weeks(f.year, f.month, cells_by_day)

        # Summary counts
        raw_counts = _build_summary_counts(cells)
        summary = {
            **{k: v for k, v in raw_counts.items() if k != "total_worked_minutes"},
            "total_worked_hours": round(raw_counts["total_worked_minutes"] / 60, 1),
        }

        return {
            "employee":   employee,
            "year":       f.year,
            "month":      f.month,
            "month_label":_month_label(f.year, f.month),
            "weeks":      weeks,
            "summary":    summary,
            "legend":     LEGEND,
        }


# ═══════════════════════════════════════════════════════════
# RECALCULATE SERVICE  (Recalculate button)
# ═══════════════════════════════════════════════════════════

class RecalculateService:
    """
    Rebuilds MonthlyAttendanceCell rows for employee+month
    from the DailyAttendanceRecord / AttendancePunchEntry tables,
    then refreshes MonthlyAttendanceSummary.
    """

    @staticmethod
    def recalculate(db: Session, employee_id: str, year: int, month: int) -> dict:
        _, days_in_month = calendar.monthrange(year, month)

        # Pull daily records for this month
        try:
            from model.HR_Automation.daily_attendance import DailyAttendanceRecord, AttendanceStatusEnum
            daily_records = (
                db.query(DailyAttendanceRecord)
                .filter(
                    DailyAttendanceRecord.employee_id == employee_id,
                    func.extract("year",  DailyAttendanceRecord.attendance_date) == year,
                    func.extract("month", DailyAttendanceRecord.attendance_date) == month,
                )
                .all()
            )
            daily_by_day = {r.attendance_date.day: r for r in daily_records}
        except ImportError:
            daily_by_day = {}

        # Determine weekends (Sunday = 0 in isoweekday system → weekday() == 6)
        for day in range(1, days_in_month + 1):
            d = date(year, month, day)
            is_weekend = d.weekday() == 6   # Sunday

            daily = daily_by_day.get(day)

            # Map daily status → monthly cell status
            if is_weekend:
                status      = DayStatusEnum.W
                worked_min  = 0
                has_punch   = False
                leave_code  = "LV457"
                leave_label = "Week Off"
            elif daily is None:
                status      = DayStatusEnum.A
                worked_min  = 0
                has_punch   = False
                leave_code  = "LV455"
                leave_label = "Absent"
            else:
                worked_min = getattr(daily, "in_time_minutes", 0) or 0
                has_punch  = bool(getattr(daily, "punch_in_time", None))

                try:
                    da_status = daily.status.value  # e.g. "Present", "Late", "Half Day"
                except Exception:
                    da_status = ""

                if "absent" in da_status.lower():
                    status, leave_code, leave_label = DayStatusEnum.A,  "LV455", "Absent"
                elif "half" in da_status.lower():
                    status, leave_code, leave_label = DayStatusEnum.HD, "LV2640","Half Day"
                elif "late" in da_status.lower():
                    status, leave_code, leave_label = DayStatusEnum.L,  "",      "Late"
                else:
                    status, leave_code, leave_label = DayStatusEnum.P,  "LV454", "Present"

            # Upsert the cell
            cell = db.query(MonthlyAttendanceCell).filter_by(
                employee_id=employee_id, cell_date=d
            ).first()
            if cell is None:
                cell = MonthlyAttendanceCell(employee_id=employee_id, cell_date=d)
                db.add(cell)

            cell.status      = status
            cell.has_punch   = has_punch
            cell.leave_code  = leave_code
            cell.leave_label = leave_label
            cell.worked_minutes = worked_min

        db.flush()

        # Refresh summary
        all_cells = (
            db.query(MonthlyAttendanceCell)
            .filter(
                MonthlyAttendanceCell.employee_id == employee_id,
                func.extract("year",  MonthlyAttendanceCell.cell_date) == year,
                func.extract("month", MonthlyAttendanceCell.cell_date) == month,
            )
            .all()
        )
        raw = _build_summary_counts(all_cells)

        summary_row = db.query(MonthlyAttendanceSummary).filter_by(
            employee_id=employee_id, year=year, month=month
        ).first()
        if summary_row is None:
            summary_row = MonthlyAttendanceSummary(
                employee_id=employee_id, year=year, month=month
            )
            db.add(summary_row)

        summary_row.present_days         = raw["present_days"]
        summary_row.absent_days          = raw["absent_days"]
        summary_row.holiday_days         = raw["holiday_days"]
        summary_row.week_off_days        = raw["week_off_days"]
        summary_row.comp_off_days        = raw["comp_off_days"]
        summary_row.casual_leave         = raw["casual_leave"]
        summary_row.leave_wo_pay         = raw["leave_wo_pay"]
        summary_row.sick_leave           = raw["sick_leave"]
        summary_row.half_days            = raw["half_days"]
        summary_row.late_days            = raw["late_days"]
        summary_row.total_worked_minutes = raw["total_worked_minutes"]
        summary_row.recalculated_at      = datetime.now(timezone.utc)

        db.commit()
        logger.info("Recalculated: %s %d-%02d", employee_id, year, month)

        return {
            **{k: v for k, v in raw.items() if k != "total_worked_minutes"},
            "total_worked_hours": round(raw["total_worked_minutes"] / 60, 1),
        }


# ═══════════════════════════════════════════════════════════
# REPLACE SHIFT SERVICE  (Replace button)
# ═══════════════════════════════════════════════════════════

class ReplaceShiftService:
    """
    Replace button — swaps the employee's default shift for the month.
    Updates the Employee.default_shift field.
    """

    @staticmethod
    def replace(db: Session, employee_id: str, year: int, month: int, new_shift: str) -> dict:
        try:
            from model.onboarding.employee import Employee
            emp = db.query(Employee).filter_by(employee_id=employee_id).first()
            if not emp:
                raise ValueError(f"Employee {employee_id} not found.")
            emp.default_shift = new_shift
            db.commit()
            logger.info("Shift replaced: %s → %s for %d-%02d", employee_id, new_shift, year, month)
        except ImportError:
            raise ValueError("Employee model not available.")

        return {
            "message":    f"Shift replaced to '{new_shift}' for {employee_id}.",
            "employee_id": employee_id,
            "new_shift":   new_shift,
        }


# ═══════════════════════════════════════════════════════════
# EXPORT SERVICE  (Options → Download)
# ═══════════════════════════════════════════════════════════

EXPORT_HEADERS = [
    "employee_code", "year", "month",
    "present", "absent", "holiday", "week_off",
    "comp_off", "casual_leave", "leave_wo_pay",
    "sick_leave", "half_days", "late_days",
    "total_worked_hours",
]


class ExportService:

    @staticmethod
    def export_csv(db: Session, year: int, month: int,
                   employee_ids: Optional[List[str]] = None) -> bytes:
        """
        Options → Download button.
        Exports MonthlyAttendanceSummary rows as CSV.
        If employee_ids is None, exports all employees for the month.
        """
        q = db.query(MonthlyAttendanceSummary).filter_by(year=year, month=month)
        if employee_ids:
            q = q.filter(MonthlyAttendanceSummary.employee_id.in_(employee_ids))
        rows = q.order_by(MonthlyAttendanceSummary.employee_id).all()

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=EXPORT_HEADERS)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "employee_code":     r.employee_id,
                "year":              r.year,
                "month":             r.month,
                "present":           r.present_days,
                "absent":            r.absent_days,
                "holiday":           r.holiday_days,
                "week_off":          r.week_off_days,
                "comp_off":          r.comp_off_days,
                "casual_leave":      r.casual_leave,
                "leave_wo_pay":      r.leave_wo_pay,
                "sick_leave":        r.sick_leave,
                "half_days":         r.half_days,
                "late_days":         r.late_days,
                "total_worked_hours":round(r.total_worked_minutes / 60, 1),
            })
        return output.getvalue().encode("utf-8")
