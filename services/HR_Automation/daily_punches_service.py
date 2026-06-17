"""
services/daily_punches_service.py
All business logic for the Daily Punches module.
"""

import csv
import io
import uuid
import logging
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, distinct

from model.HR_Automation.daily_punches import (
    EmployeePunch, DailyPunchSummary, PunchImportBatch,
    PunchSourceEnum, PunchDirectionEnum, PunchStatusEnum, AttendanceStatusEnum,
)

logger = logging.getLogger(__name__)

# ── Assuming Employee is defined in the existing HR backend ──
# from models.employee import Employee


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _fmt_duration(minutes: int) -> str:
    """Convert total minutes → 'H:MM' string shown in Duration column."""
    if minutes <= 0:
        return "0:00"
    h = minutes // 60
    m = minutes % 60
    return f"{h}:{m:02d}"


def _fmt_time(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime → '09:01:49AM' as shown in Start/End columns."""
    if dt is None:
        return None
    return dt.strftime("%I:%M:%S%p").lstrip("0")


def _combine(punch_date: date, time_str: str) -> datetime:
    """Convert 'HH:MM:SS' string + date → timezone-aware datetime."""
    h, m, s = (int(x) for x in time_str.split(":"))
    return datetime(punch_date.year, punch_date.month, punch_date.day, h, m, s,
                    tzinfo=timezone.utc)


# ═══════════════════════════════════════════════════════════
# DAILY PUNCH QUERY SERVICE
# ═══════════════════════════════════════════════════════════

class DailyPunchService:

    @staticmethod
    def get_filter_options(db: Session) -> dict:
        """
        Returns distinct values for all 4 dropdown filters.
        Reads from DailyPunchSummary so values are always consistent with existing data.
        """
        def _distinct(col):
            return sorted(set(
                v for (v,) in db.query(distinct(col)).filter(col.isnot(None)).all() if v
            ))

        return {
            "business_units": ["All Units"] + _distinct(DailyPunchSummary.business_unit),
            "locations":      ["All Locations"] + _distinct(DailyPunchSummary.location),
            "cost_centers":   ["All Cost Centers"] + _distinct(DailyPunchSummary.cost_center),
            "departments":    ["All Departments"] + _distinct(DailyPunchSummary.department),
        }

    @staticmethod
    def list_daily_punches(db: Session, f) -> dict:
        """
        Main query behind the Daily Punches table.
        Applies all 7 filter controls + pagination, returns structured rows.
        """
        from model.HR_Automation.daily_punches import DailyPunchSummary, EmployeePunch

        # ── Base query on summary rows ──
        q = db.query(DailyPunchSummary).filter(
            DailyPunchSummary.punch_date == f.punch_date
        )

        # Dropdown filters
        if f.business_unit and f.business_unit != "All Units":
            q = q.filter(DailyPunchSummary.business_unit == f.business_unit)
        if f.location and f.location != "All Locations":
            q = q.filter(DailyPunchSummary.location == f.location)
        if f.cost_center and f.cost_center != "All Cost Centers":
            q = q.filter(DailyPunchSummary.cost_center == f.cost_center)
        if f.department and f.department != "All Departments":
            q = q.filter(DailyPunchSummary.department == f.department)

        # Radio button filters
        if f.status_filter == "late":
            q = q.filter(DailyPunchSummary.attendance_status == AttendanceStatusEnum.L)
        elif f.status_filter == "absent":
            q = q.filter(DailyPunchSummary.attendance_status == AttendanceStatusEnum.A)
        elif f.status_filter == "nopunch":
            q = q.filter(DailyPunchSummary.first_in_time.is_(None))

        # Employee search (name / code / designation via JOIN)
        if f.search:
            search_term = f"%{f.search.lower()}%"
            # Join Employee table for name/code/designation search
            try:
                from models.employee import Employee
                q = q.join(Employee, Employee.employee_id == DailyPunchSummary.employee_id)
                q = q.filter(or_(
                    func.lower(Employee.name).like(search_term),
                    func.lower(Employee.employee_id).like(search_term),
                    func.lower(Employee.position).like(search_term),
                ))
            except ImportError:
                pass  # Employee model not yet imported — skip search filter

        total = q.count()

        # Pagination
        offset = (f.page - 1) * f.page_size
        summaries = q.order_by(DailyPunchSummary.employee_id).offset(offset).limit(f.page_size).all()

        items = []
        for s in summaries:
            # Fetch employee info
            emp_name, emp_code, designation = s.employee_id, s.employee_id, ""
            try:
                from model.onboarding.employee import Employee
                emp = db.query(Employee).filter_by(employee_id=s.employee_id).first()
                if emp:
                    emp_name    = emp.name
                    emp_code    = emp.employee_id
                    designation = emp.position or ""
            except ImportError:
                pass

            # Fetch raw punches for this employee+date (for '...' modal)
            raw_punches = (
                db.query(EmployeePunch)
                .filter_by(employee_id=s.employee_id, punch_date=f.punch_date)
                .order_by(EmployeePunch.punch_time)
                .all()
            )

            # First IN punch selfie + location
            first_in_punch = next(
                (p for p in raw_punches if p.direction == PunchDirectionEnum.IN), None
            )
            # Last OUT punch selfie + location
            last_out_punch = next(
                (p for p in reversed(raw_punches) if p.direction == PunchDirectionEnum.OUT), None
            )

            items.append({
                "employee_id":        s.employee_id,
                "employee_name":      emp_name,
                "employee_code":      emp_code,
                "designation":        designation,
                "business_unit":      s.business_unit,
                "location":           s.location,
                "cost_center":        s.cost_center,
                "department":         s.department,
                "first_in_time":      _fmt_time(s.first_in_time),
                "first_in_selfie":    first_in_punch.selfie_path if first_in_punch else None,
                "first_in_location":  first_in_punch.location_url if first_in_punch else "",
                "has_start_selfie":   s.has_start_selfie,
                "has_start_location": s.has_start_location,
                "last_out_time":      _fmt_time(s.last_out_time),
                "last_out_selfie":    last_out_punch.selfie_path if last_out_punch else None,
                "last_out_location":  last_out_punch.location_url if last_out_punch else "",
                "has_end_selfie":     s.has_end_selfie,
                "has_end_location":   s.has_end_location,
                "duration":           _fmt_duration(s.duration_minutes),
                "attendance":         s.attendance_status,
                "punches":            raw_punches,
            })

        total_pages = max(1, -(-total // f.page_size))  # ceiling division
        return {
            "total":       total,
            "page":        f.page,
            "page_size":   f.page_size,
            "total_pages": total_pages,
            "date":        f.punch_date,
            "items":       items,
        }

    # ── Selfie modal ──
    @staticmethod
    def get_selfie_data(db: Session, employee_id: str, punch_date: date, direction: str) -> dict:
        punch = (
            db.query(EmployeePunch)
            .filter_by(employee_id=employee_id, punch_date=punch_date,
                       direction=direction.upper())
            .order_by(
                EmployeePunch.punch_time if direction.upper() == "IN"
                else EmployeePunch.punch_time.desc()
            )
            .first()
        )
        emp_name, emp_code = employee_id, employee_id
        try:
            from model.onboarding.employee import Employee
            emp = db.query(Employee).filter_by(employee_id=employee_id).first()
            if emp:
                emp_name = emp.name
                emp_code = emp.employee_id
        except ImportError:
            pass

        return {
            "employee_id":         employee_id,
            "employee_name":       emp_name,
            "employee_code":       emp_code,
            "registered_face_url": punch.registered_face_path if punch else None,
            "punch_image_url":     punch.selfie_path if punch else None,
        }

    # ── Location modal ──
    @staticmethod
    def get_location_data(db: Session, employee_id: str, punch_date: date, direction: str) -> dict:
        punch = (
            db.query(EmployeePunch)
            .filter_by(employee_id=employee_id, punch_date=punch_date,
                       direction=direction.upper())
            .order_by(
                EmployeePunch.punch_time if direction.upper() == "IN"
                else EmployeePunch.punch_time.desc()
            )
            .first()
        )
        emp_name, emp_code = employee_id, employee_id
        try:
            from model.onboarding.employee import Employee
            emp = db.query(Employee).filter_by(employee_id=employee_id).first()
            if emp:
                emp_name = emp.name
                emp_code = emp.employee_id
        except ImportError:
            pass

        return {
            "employee_id":   employee_id,
            "employee_name": emp_name,
            "employee_code": emp_code,
            "latitude":      punch.latitude if punch else None,
            "longitude":     punch.longitude if punch else None,
            "location_url":  punch.location_url if punch else "",
            "location_name": punch.location_name if punch else "",
        }

    # ── All punches modal ──
    @staticmethod
    def get_all_punches(db: Session, employee_id: str, punch_date: date) -> dict:
        punches = (
            db.query(EmployeePunch)
            .filter_by(employee_id=employee_id, punch_date=punch_date)
            .order_by(EmployeePunch.punch_time)
            .all()
        )
        emp_name, emp_code = employee_id, employee_id
        try:
            from model.onboarding.employee import Employee
            emp = db.query(Employee).filter_by(employee_id=employee_id).first()
            if emp:
                emp_name = emp.name
                emp_code = emp.employee_id
        except ImportError:
            pass

        return {
            "employee_id":   employee_id,
            "employee_name": emp_name,
            "employee_code": emp_code,
            "punch_date":    punch_date,
            "punches":       punches,
        }


# ═══════════════════════════════════════════════════════════
# ADD / DELETE PUNCH SERVICE
# ═══════════════════════════════════════════════════════════

class PunchManagementService:

    @staticmethod
    def add_punch(
        db: Session,
        employee_id: str,
        punch_date: date,
        punch_time_str: str,
        direction: PunchDirectionEnum,
        source: PunchSourceEnum,
        remarks: str = "",
        latitude: Optional[Decimal] = None,
        longitude: Optional[Decimal] = None,
        location_url: str = "",
        selfie_path: Optional[str] = None,
        added_by: Optional[int] = None,
    ) -> EmployeePunch:
        """
        Creates one raw punch record (Add Time Punch modal → Insert button).
        Then recalculates the daily summary for that employee + date.
        """
        punch_dt = _combine(punch_date, punch_time_str)

        punch = EmployeePunch(
            employee_id=employee_id,
            punch_date=punch_date,
            punch_time=punch_dt,
            direction=direction,
            source=source,
            status=PunchStatusEnum.pending,
            remarks=remarks,
            latitude=latitude,
            longitude=longitude,
            location_url=location_url,
            selfie_path=selfie_path,
            is_manual=True,
            added_by=added_by,
        )
        db.add(punch)
        db.flush()

        # Recalculate summary
        SummaryService.recalculate(db, employee_id, punch_date)
        db.commit()
        db.refresh(punch)
        logger.info("Punch added: %s %s %s @ %s", employee_id, direction, source, punch_time_str)
        return punch

    @staticmethod
    def delete_punch(db: Session, punch_id: uuid.UUID, deleted_by: Optional[int] = None) -> EmployeePunch:
        """
        Deletes a raw punch (trash icon in the '...' All Punches modal).
        Then recalculates the daily summary.
        """
        punch = db.query(EmployeePunch).filter_by(id=punch_id).first()
        if not punch:
            raise ValueError(f"Punch {punch_id} not found.")

        emp_id     = punch.employee_id
        punch_date = punch.punch_date
        db.delete(punch)
        db.flush()

        SummaryService.recalculate(db, emp_id, punch_date)
        db.commit()
        logger.info("Punch deleted: %s by user %s", punch_id, deleted_by)
        return punch


# ═══════════════════════════════════════════════════════════
# SUMMARY RECALCULATION SERVICE
# ═══════════════════════════════════════════════════════════

class SummaryService:
    """
    Recomputes DailyPunchSummary for one employee+date from raw punches.
    Called after every add / delete / import.
    """

    @staticmethod
    def recalculate(db: Session, employee_id: str, punch_date: date) -> Optional[DailyPunchSummary]:
        from model.HR_Automation.daily_punches import EmployeePunch, DailyPunchSummary

        punches = (
            db.query(EmployeePunch)
            .filter_by(employee_id=employee_id, punch_date=punch_date)
            .order_by(EmployeePunch.punch_time)
            .all()
        )

        summary = db.query(DailyPunchSummary).filter_by(
            employee_id=employee_id, punch_date=punch_date
        ).first()

        if not punches:
            if summary:
                db.delete(summary)
                db.commit()
            return None

        if summary is None:
            summary = DailyPunchSummary(employee_id=employee_id, punch_date=punch_date)
            # Pull org fields from Employee model
            try:
                from model.onboarding.employee import Employee
                emp = db.query(Employee).filter_by(employee_id=employee_id).first()
                if emp:
                    summary.business_unit = getattr(emp, "business_unit", "Default Business Units")
                    summary.location      = getattr(emp, "location", "")
                    summary.cost_center   = getattr(emp, "cost_center", "")
                    summary.department    = getattr(emp, "department", "")
            except ImportError:
                pass
            db.add(summary)

        in_punches  = [p for p in punches if p.direction == PunchDirectionEnum.IN]
        out_punches = [p for p in punches if p.direction == PunchDirectionEnum.OUT]

        first_in  = in_punches[0]  if in_punches  else None
        last_out  = out_punches[-1] if out_punches else None

        summary.first_in_time    = first_in.punch_time  if first_in  else None
        summary.last_out_time    = last_out.punch_time  if last_out  else None
        summary.punch_count      = len(punches)
        summary.has_start_selfie    = bool(first_in and first_in.selfie_path)
        summary.has_start_location  = bool(first_in and first_in.location_url)
        summary.has_end_selfie      = bool(last_out and last_out.selfie_path)
        summary.has_end_location    = bool(last_out and last_out.location_url)

        # Duration
        if first_in and last_out:
            delta = (last_out.punch_time - first_in.punch_time).total_seconds()
            summary.duration_minutes = max(0, int(delta / 60))
        else:
            summary.duration_minutes = 0

        # Attendance status
        work_hours = summary.duration_minutes / 60
        if not in_punches:
            summary.attendance_status = AttendanceStatusEnum.A
        elif work_hours >= 8:
            summary.attendance_status = AttendanceStatusEnum.P
        elif work_hours >= 4:
            summary.attendance_status = AttendanceStatusEnum.HD
        else:
            summary.attendance_status = AttendanceStatusEnum.P

        # Late check (grace 9:00 AM + 15 min)
        if first_in:
            scheduled = datetime(punch_date.year, punch_date.month, punch_date.day,
                                 9, 0, 0, tzinfo=timezone.utc)
            diff_min = (first_in.punch_time - scheduled).total_seconds() / 60
            if diff_min > 15:
                summary.is_late      = True
                summary.late_minutes = int(diff_min)
                summary.attendance_status = AttendanceStatusEnum.L
            else:
                summary.is_late      = False
                summary.late_minutes = 0

        db.commit()
        db.refresh(summary)
        return summary


# ═══════════════════════════════════════════════════════════
# CSV / EXCEL IMPORT SERVICE
# ═══════════════════════════════════════════════════════════

class PunchImportService:
    """
    Handles CSV / Excel import (Options → Upload button).
    Expected CSV columns: name, code, date, time, direction, source, remarks
    """

    REQUIRED_COLS = {"code", "date", "time", "direction"}

    @staticmethod
    def import_csv(
        db: Session,
        file_content: bytes,
        filename: str,
        uploaded_by: Optional[int] = None,
    ) -> PunchImportBatch:
        batch = PunchImportBatch(filename=filename, uploaded_by=uploaded_by)
        db.add(batch)
        db.flush()

        reader    = csv.DictReader(io.StringIO(file_content.decode("utf-8-sig")))
        headers   = set(h.strip().lower() for h in (reader.fieldnames or []))
        missing   = PunchImportService.REQUIRED_COLS - headers
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        errors  = []
        success = 0

        for i, row in enumerate(reader, start=2):  # row 1 = header
            try:
                row = {k.strip().lower(): v.strip() for k, v in row.items()}

                emp_id     = row.get("code", "").strip()
                date_str   = row.get("date", "")
                time_str   = row.get("time", "")
                direction  = row.get("direction", "IN").upper()
                source_raw = row.get("source", "manual").lower().replace(" ", "_")
                remarks    = row.get("remarks", "")

                if not emp_id or not date_str or not time_str:
                    raise ValueError("Empty required field (code / date / time).")

                punch_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                # Validate time
                h, m, s = (int(x) for x in time_str.split(":"))
                punch_dt = datetime(punch_date.year, punch_date.month, punch_date.day,
                                    h, m, s, tzinfo=timezone.utc)

                # Map source
                try:
                    source = PunchSourceEnum(source_raw)
                except ValueError:
                    source = PunchSourceEnum.excel_import

                db.add(EmployeePunch(
                    employee_id=emp_id,
                    punch_date=punch_date,
                    punch_time=punch_dt,
                    direction=PunchDirectionEnum(direction),
                    source=source,
                    status=PunchStatusEnum.pending,
                    remarks=remarks,
                    is_manual=True,
                    added_by=uploaded_by,
                    import_batch_id=batch.id,
                ))

                SummaryService.recalculate(db, emp_id, punch_date)
                success += 1

            except Exception as exc:
                errors.append({"row": i, "error": str(exc)})

        batch.total_rows   = success + len(errors)
        batch.success_rows = success
        batch.failed_rows  = len(errors)
        batch.error_log    = errors

        db.commit()
        db.refresh(batch)
        logger.info("Import complete: %s — %d ok / %d failed", filename, success, len(errors))
        return batch


# ═══════════════════════════════════════════════════════════
# CSV EXPORT SERVICE
# ═══════════════════════════════════════════════════════════

class PunchExportService:
    """
    Generates CSV bytes for Options → Download button.
    Exports the currently filtered result set.
    """

    HEADERS = [
        "sn", "employee_code", "employee_name", "designation",
        "business_unit", "location", "cost_center", "department",
        "date", "start", "end", "duration", "attendance",
    ]

    @staticmethod
    def export_csv(items: list, punch_date: date) -> bytes:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=PunchExportService.HEADERS)
        writer.writeheader()

        for sn, row in enumerate(items, start=1):
            writer.writerow({
                "sn":            sn,
                "employee_code": row["employee_code"],
                "employee_name": row["employee_name"],
                "designation":   row["designation"],
                "business_unit": row["business_unit"],
                "location":      row["location"],
                "cost_center":   row["cost_center"],
                "department":    row["department"],
                "date":          str(punch_date),
                "start":         row["first_in_time"]  or "--",
                "end":           row["last_out_time"]   or "--",
                "duration":      row["duration"],
                "attendance":    row["attendance"],
            })

        return output.getvalue().encode("utf-8")
