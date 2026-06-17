"""
services/daily_attendance_service.py
Business logic for Daily Attendance module.
"""

import csv
import io
import logging
from datetime import date, datetime, timezone, time as dt_time
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_

from model.HR_Automation.daily_attendance import (
    DailyAttendanceRecord, AttendancePunchEntry,
    AttendanceStatusEnum, PunchTypeEnum, PunchDirectionEnum, ShiftTypeEnum,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# FORMATTING HELPERS
# ═══════════════════════════════════════════════════════════

def _fmt_punch_time(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime → '09:17A' as shown below the timeline bars."""
    if dt is None:
        return None
    return dt.strftime("%I:%M%p").lstrip("0").replace(":0", ":")


def _fmt_in_time(minutes: int) -> str:
    """Convert total minutes → '8 h 35 m' shown in right panel."""
    if minutes <= 0:
        return "0 h 00 m"
    h = minutes // 60
    m = minutes % 60
    return f"{h} h {m:02d} m"


def _combine(d: date, time_str: str) -> datetime:
    """'HH:MM:SS' + date → UTC datetime."""
    h, m, s = (int(x) for x in time_str.split(":"))
    return datetime(d.year, d.month, d.day, h, m, s, tzinfo=timezone.utc)


def _build_timeline(record: DailyAttendanceRecord) -> dict:
    """Build the timeline dict for the 3-bar visual."""
    shift_start = record.shift_start.strftime("%I:%M%p").lstrip("0") if record.shift_start else "09:00A"
    shift_end   = record.shift_end.strftime("%I:%M%p").lstrip("0")   if record.shift_end   else "06:00P"
    return {
        "start":       record.timeline_start or "03:00A",
        "shift_start": shift_start,
        "shift_end":   shift_end,
        "end":         record.timeline_end or "12:00A",
        "shift_label": record.shift_type.value if record.shift_type else "General",
    }


def _build_card(db: Session, record: DailyAttendanceRecord) -> dict:
    """Build the full AttendanceCardOut dict from a DB record."""

    # Resolve employee name / designation
    emp_name, emp_code, designation = record.employee_id, record.employee_id, ""
    try:
        from model.onboarding.employee import Employee
        emp = db.query(Employee).filter_by(employee_id=record.employee_id).first()
        if emp:
            emp_name    = emp.name
            emp_code    = emp.employee_id
            designation = getattr(emp, "position", "") or ""
    except ImportError:
        pass

    # Punch in/out display strings
    punch_in_str   = _fmt_punch_time(record.punch_in_time)  or "--"
    punch_type_lbl = record.punch_type.value.capitalize() if record.punch_type else "-"

    if record.punch_out_time:
        punch_out_str = f"{_fmt_punch_time(record.punch_out_time)} ({punch_type_lbl})"
    else:
        punch_out_str = f"-- (-)"

    return {
        "id":               record.id,
        "employee_id":      record.employee_id,
        "employee_name":    emp_name,
        "employee_code":    emp_code,
        "designation":      designation,
        "location":         record.location,
        "department":       record.department,
        "business_unit":    record.business_unit,
        "cost_center":      record.cost_center,
        "attendance_date":  record.attendance_date,
        "status":           record.status,
        "note":             record.note,
        "shift_type":       record.shift_type,
        "timeline":         _build_timeline(record),
        "punch_in":         punch_in_str,
        "punch_out":        punch_out_str,
        "punch_type_label": punch_type_lbl,
        "in_time_display":  _fmt_in_time(record.in_time_minutes),
        "punches":          record.punches,
    }


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

        return {
            "business_units": ["All Units"] + _distinct(DailyAttendanceRecord.business_unit),
            "locations":      ["All"]       + _distinct(DailyAttendanceRecord.location),
            "cost_centers":   ["All"]       + _distinct(DailyAttendanceRecord.cost_center),
            "departments":    ["All"]       + _distinct(DailyAttendanceRecord.department),
        }


# ═══════════════════════════════════════════════════════════
# DAILY ATTENDANCE QUERY SERVICE
# ═══════════════════════════════════════════════════════════

class DailyAttendanceService:

    @staticmethod
    def list_cards(db: Session, f) -> dict:
        """
        Powers the scrollable card list.
        Applies all 7 filter controls.
        Returns structured card dicts ready for serialization.
        """
        q = db.query(DailyAttendanceRecord).filter(
            DailyAttendanceRecord.attendance_date == f.attendance_date
        )

        # Dropdown filters
        if f.business_unit and f.business_unit != "All Units":
            q = q.filter(DailyAttendanceRecord.business_unit == f.business_unit)
        if f.location and f.location != "All":
            q = q.filter(DailyAttendanceRecord.location == f.location)
        if f.cost_center and f.cost_center != "All":
            q = q.filter(DailyAttendanceRecord.cost_center == f.cost_center)
        if f.department and f.department != "All":
            q = q.filter(DailyAttendanceRecord.department == f.department)

        # Radio button filters
        if f.status_filter == "late":
            q = q.filter(DailyAttendanceRecord.status == AttendanceStatusEnum.Late)
        elif f.status_filter == "absent":
            q = q.filter(DailyAttendanceRecord.status == AttendanceStatusEnum.Absent)
        elif f.status_filter == "nopunch":
            q = q.filter(DailyAttendanceRecord.punch_in_time.is_(None))

        # Employee search (name / code / designation)
        if f.search:
            term = f"%{f.search.lower()}%"
            try:
                from model.onboarding.employee import Employee
                q = q.join(Employee,
                            Employee.employee_id == DailyAttendanceRecord.employee_id)
                q = q.filter(or_(
                    func.lower(Employee.name).like(term),
                    func.lower(Employee.employee_id).like(term),
                    func.lower(Employee.position).like(term),
                ))
            except ImportError:
                pass

        total   = q.count()
        records = q.order_by(DailyAttendanceRecord.employee_id).all()
        items   = [_build_card(db, r) for r in records]

        return {"total": total, "date": f.attendance_date, "items": items}

    @staticmethod
    def get_all_punches(db: Session, employee_id: str, attendance_date: date) -> dict:
        """
        Powers the '…' All Punches modal.
        Returns all punch entries for employee + date.
        """
        record = db.query(DailyAttendanceRecord).filter_by(
            employee_id=employee_id, attendance_date=attendance_date
        ).first()

        emp_name, emp_code = employee_id, employee_id
        try:
            from model.onboarding.employee import Employee
            emp = db.query(Employee).filter_by(employee_id=employee_id).first()
            if emp:
                emp_name = emp.name
                emp_code = emp.employee_id
        except ImportError:
            pass

        punches = record.punches if record else []
        return {
            "employee_id":     employee_id,
            "employee_name":   emp_name,
            "employee_code":   emp_code,
            "attendance_date": attendance_date,
            "punches":         punches,
        }


# ═══════════════════════════════════════════════════════════
# PUNCH MANAGEMENT  (Add / Delete from modals)
# ═══════════════════════════════════════════════════════════

class PunchManagementService:

    @staticmethod
    def add_punch(
        db:           Session,
        employee_id:  str,
        punch_date:   date,
        punch_time_str: str,          # "HH:MM:SS"
        direction:    PunchDirectionEnum,
        punch_type:   PunchTypeEnum,
        remarks:      str = "",
        added_by:     Optional[int] = None,
    ) -> tuple[AttendancePunchEntry, DailyAttendanceRecord]:
        """
        Add Time Punch modal → Insert button.
        Creates the punch entry and recalculates the attendance record.
        """
        # Ensure DailyAttendanceRecord exists
        record = db.query(DailyAttendanceRecord).filter_by(
            employee_id=employee_id, attendance_date=punch_date
        ).first()

        if record is None:
            record = DailyAttendanceRecord(
                employee_id=employee_id,
                attendance_date=punch_date,
                status=AttendanceStatusEnum.Absent,
                shift_type=ShiftTypeEnum.general,
                shift_start=dt_time(9, 0),
                shift_end=dt_time(18, 0),
                timeline_start="03:00A",
                timeline_end="12:00A",
            )
            # Pull org fields from Employee
            try:
                from model.onboarding.employee import Employee
                emp = db.query(Employee).filter_by(employee_id=employee_id).first()
                if emp:
                    record.location      = getattr(emp, "location", "")
                    record.business_unit = getattr(emp, "business_unit", "")
                    record.cost_center   = getattr(emp, "cost_center", "")
                    record.department    = getattr(emp, "department", "")
            except ImportError:
                pass
            db.add(record)
            db.flush()

        punch_dt = _combine(punch_date, punch_time_str)
        entry = AttendancePunchEntry(
            daily_record_id=record.id,
            employee_id=employee_id,
            punch_time=punch_dt,
            direction=direction,
            punch_type=punch_type,
            remarks=remarks,
            is_manual=True,
            added_by=added_by,
        )
        db.add(entry)
        db.flush()

        # Recalculate the attendance record
        RecalculationService.recalculate(db, record)
        db.commit()
        db.refresh(record)
        db.refresh(entry)

        logger.info("Punch added: %s %s @ %s", employee_id, direction, punch_time_str)
        return entry, record

    @staticmethod
    def delete_punch(
        db:           Session,
        punch_id:     str,
        deleted_by:   Optional[int] = None,
    ) -> tuple[AttendancePunchEntry, DailyAttendanceRecord]:
        """
        Trash icon in the '…' All Punches modal.
        Deletes the punch entry and recalculates.
        """
        import uuid as _uuid
        entry = db.query(AttendancePunchEntry).filter_by(
            id=_uuid.UUID(str(punch_id))
        ).first()
        if not entry:
            raise ValueError(f"Punch {punch_id} not found.")

        record = db.query(DailyAttendanceRecord).filter_by(
            id=entry.daily_record_id
        ).first()

        db.delete(entry)
        db.flush()

        if record:
            RecalculationService.recalculate(db, record)

        db.commit()
        if record:
            db.refresh(record)

        logger.info("Punch deleted: %s by %s", punch_id, deleted_by)
        return entry, record


# ═══════════════════════════════════════════════════════════
# RECALCULATION SERVICE
# ═══════════════════════════════════════════════════════════

class RecalculationService:
    """
    Recomputes status, punch_in_time, punch_out_time, in_time_minutes,
    is_late, late_minutes from all AttendancePunchEntry rows for the record.
    """

    SHIFT_START_HOUR   = 9
    SHIFT_START_MINUTE = 0
    LATE_GRACE_MINUTES = 15
    HALF_DAY_MINUTES   = 240   # 4 hours
    FULL_DAY_MINUTES   = 480   # 8 hours

    @staticmethod
    def recalculate(db: Session, record: DailyAttendanceRecord) -> None:
        punches = (
            db.query(AttendancePunchEntry)
            .filter_by(daily_record_id=record.id)
            .order_by(AttendancePunchEntry.punch_time)
            .all()
        )

        in_punches  = [p for p in punches if p.direction == PunchDirectionEnum.IN]
        out_punches = [p for p in punches if p.direction == PunchDirectionEnum.OUT]

        first_in  = in_punches[0]  if in_punches  else None
        last_out  = out_punches[-1] if out_punches else None

        record.punch_in_time  = first_in.punch_time  if first_in  else None
        record.punch_out_time = last_out.punch_time  if last_out  else None
        record.punch_type     = first_in.punch_type  if first_in  else None

        # In-time (minutes worked)
        if first_in and last_out:
            delta = (last_out.punch_time - first_in.punch_time).total_seconds() / 60
            record.in_time_minutes = max(0, int(delta))
        else:
            record.in_time_minutes = 0

        # Late check
        if first_in:
            sched = datetime(
                record.attendance_date.year,
                record.attendance_date.month,
                record.attendance_date.day,
                RecalculationService.SHIFT_START_HOUR,
                RecalculationService.SHIFT_START_MINUTE,
                tzinfo=timezone.utc,
            )
            diff_min = (first_in.punch_time - sched).total_seconds() / 60
            record.is_late      = diff_min > RecalculationService.LATE_GRACE_MINUTES
            record.late_minutes = max(0, int(diff_min))
        else:
            record.is_late      = False
            record.late_minutes = 0

        # Status
        mins = record.in_time_minutes
        if not in_punches:
            record.status = AttendanceStatusEnum.Absent
            record.note   = "No punch-in or punch-out found"
        elif record.is_late:
            record.status = AttendanceStatusEnum.Late
            record.note   = "Late punch-in recorded"
        elif mins >= RecalculationService.FULL_DAY_MINUTES:
            record.status = AttendanceStatusEnum.Present
            record.note   = "Employee completed full shift"
        elif mins >= RecalculationService.HALF_DAY_MINUTES:
            record.status = AttendanceStatusEnum.Half_Day
            record.note   = "Employee worked half day"
        else:
            record.status = AttendanceStatusEnum.Present
            record.note   = "Present marked as at least one time-punch was found"


# ═══════════════════════════════════════════════════════════
# CSV IMPORT / EXPORT
# ═══════════════════════════════════════════════════════════

EXPORT_HEADERS = [
    "employee_code", "employee_name", "date", "status",
    "location", "designation", "department",
    "punch_in", "punch_out", "punch_type", "in_time",
]


class ImportExportService:

    @staticmethod
    def export_csv(items: list, attendance_date: date) -> bytes:
        """Options → Download button — exports filtered cards as CSV."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=EXPORT_HEADERS)
        writer.writeheader()
        for row in items:
            writer.writerow({
                "employee_code": row["employee_code"],
                "employee_name": row["employee_name"],
                "date":          str(attendance_date),
                "status":        row["status"],
                "location":      row["location"],
                "designation":   row["designation"],
                "department":    row["department"],
                "punch_in":      row["punch_in"]  or "--",
                "punch_out":     row["punch_out"] or "--",
                "punch_type":    row["punch_type_label"] or "-",
                "in_time":       row["in_time_display"],
            })
        return output.getvalue().encode("utf-8")

    @staticmethod
    def import_csv(
        db:           Session,
        file_content: bytes,
        filename:     str,
        uploaded_by:  Optional[int] = None,
    ) -> dict:
        """
        Options → Upload button.
        Expected CSV columns:
        code · date (YYYY-MM-DD) · punch_in (HH:MM:SS) · punch_out (HH:MM:SS)
        · punch_type (selfie/remote/manual) · status · location · department
        · cost_center · business_unit · note
        """
        reader   = csv.DictReader(io.StringIO(file_content.decode("utf-8-sig")))
        errors   = []
        success  = 0

        for i, row in enumerate(reader, start=2):
            try:
                row = {k.strip().lower(): v.strip() for k, v in row.items()}

                emp_id     = row.get("code", "").strip()
                date_str   = row.get("date", "")
                if not emp_id or not date_str:
                    raise ValueError("Missing required field: code or date")

                att_date   = datetime.strptime(date_str, "%Y-%m-%d").date()

                # Resolve / create record
                record = db.query(DailyAttendanceRecord).filter_by(
                    employee_id=emp_id, attendance_date=att_date
                ).first()

                if record is None:
                    record = DailyAttendanceRecord(
                        employee_id=emp_id,
                        attendance_date=att_date,
                        status=AttendanceStatusEnum.Absent,
                        shift_type=ShiftTypeEnum.general,
                        shift_start=dt_time(9, 0),
                        shift_end=dt_time(18, 0),
                        timeline_start="03:00A",
                        timeline_end="12:00A",
                        location=row.get("location", ""),
                        business_unit=row.get("business_unit", ""),
                        cost_center=row.get("cost_center", ""),
                        department=row.get("department", ""),
                        note=row.get("note", ""),
                    )
                    db.add(record)
                    db.flush()

                # Add IN punch
                if row.get("punch_in"):
                    punch_dt = _combine(att_date, row["punch_in"])
                    try:
                        pt = PunchTypeEnum(row.get("punch_type", "manual").lower())
                    except ValueError:
                        pt = PunchTypeEnum.manual
                    db.add(AttendancePunchEntry(
                        daily_record_id=record.id,
                        employee_id=emp_id,
                        punch_time=punch_dt,
                        direction=PunchDirectionEnum.IN,
                        punch_type=pt,
                        is_manual=True,
                        added_by=uploaded_by,
                    ))

                # Add OUT punch
                if row.get("punch_out"):
                    punch_dt = _combine(att_date, row["punch_out"])
                    db.add(AttendancePunchEntry(
                        daily_record_id=record.id,
                        employee_id=emp_id,
                        punch_time=punch_dt,
                        direction=PunchDirectionEnum.OUT,
                        punch_type=PunchTypeEnum.manual,
                        is_manual=True,
                        added_by=uploaded_by,
                    ))

                db.flush()
                RecalculationService.recalculate(db, record)
                success += 1

            except Exception as exc:
                errors.append({"row": i, "error": str(exc)})

        db.commit()
        return {
            "total_rows":   success + len(errors),
            "success_rows": success,
            "failed_rows":  len(errors),
            "errors":       errors,
        }
