"""
services/manual_attendance_service.py
Business logic for Manual Attendance module.
"""

import calendar
import csv
import io
import logging
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from model.HR_Automation.manual_attendance import (
    ManualAttendanceRecord,
    ManualAttendanceImport,
    ImportStatusEnum,
)

logger = logging.getLogger(__name__)

MONTH_LABELS = [
    "JAN","FEB","MAR","APR","MAY","JUN",
    "JUL","AUG","SEP","OCT","NOV","DEC",
]

CSV_EXPORT_HEADERS = [
    "sl_no","employee_code","employee_name",
    "business_unit","location","cost_center","department",
    "period","P","A","H","W","CO","CL","LW",
]

CSV_IMPORT_REQUIRED = {"code","period","P","A","H","W","CO","CL","LW"}


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _period_label(year: int, month: int) -> str:
    return f"{MONTH_LABELS[month - 1]}-{year}"


def _resolve_employee(db: Session, employee_id: str) -> dict:
    result = {
        "name": employee_id, "code": employee_id,
        "business_unit": "", "location": "",
        "cost_center": "", "department": "",
    }
    try:
        from models.employee import Employee
        emp = db.query(Employee).filter_by(employee_id=employee_id).first()
        if emp:
            result.update({
                "name":          emp.name,
                "code":          emp.employee_id,
                "business_unit": getattr(emp, "business_unit", ""),
                "location":      getattr(emp, "location",      ""),
                "cost_center":   getattr(emp, "cost_center",   ""),
                "department":    getattr(emp, "department",     ""),
            })
    except ImportError:
        pass
    return result


def _get_or_create_record(
    db: Session,
    employee_id: str,
    year: int,
    month: int,
) -> ManualAttendanceRecord:
    record = db.query(ManualAttendanceRecord).filter_by(
        employee_id=employee_id, year=year, month=month
    ).first()
    if not record:
        emp = _resolve_employee(db, employee_id)
        record = ManualAttendanceRecord(
            employee_id=employee_id,
            year=year,
            month=month,
            business_unit=emp["business_unit"],
            location=emp["location"],
            cost_center=emp["cost_center"],
            department=emp["department"],
        )
        db.add(record)
        db.flush()
    return record


def _build_row(db: Session, record: ManualAttendanceRecord) -> dict:
    """Build the full row dict for API response."""
    emp = _resolve_employee(db, record.employee_id)
    return {
        "id":            record.id,
        "employee_id":   record.employee_id,
        "employee_name": emp["name"],
        "employee_code": emp["code"],
        "business_unit": record.business_unit or emp["business_unit"],
        "location":      record.location      or emp["location"],
        "cost_center":   record.cost_center   or emp["cost_center"],
        "department":    record.department    or emp["department"],
        "year":          record.year,
        "month":         record.month,
        "period_label":  _period_label(record.year, record.month),
        "counts": {
            "P":  record.present_days,
            "A":  record.absent_days,
            "H":  record.holiday_days,
            "W":  record.week_off_days,
            "CO": record.comp_off_days,
            "CL": record.casual_leave,
            "LW": record.leave_wo_pay,
        },
        "is_saved":   record.is_saved,
        "updated_at": record.updated_at,
    }


# ═══════════════════════════════════════════════════════════
# FILTER OPTIONS
# ═══════════════════════════════════════════════════════════

class FilterOptionsService:

    @staticmethod
    def get(db: Session) -> dict:
        def _distinct(col):
            return sorted({
                v for (v,) in db.query(distinct(col))
                              .filter(col.isnot(None)).all()
                if v
            })

        try:
            from models.employee import Employee
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
# LIST SERVICE  (main paginated table)
# ═══════════════════════════════════════════════════════════

class ManualAttendanceListService:

    @staticmethod
    def list_records(
        db: Session,
        year: int,
        month: int,
        business_unit: Optional[str] = None,
        location:      Optional[str] = None,
        cost_center:   Optional[str] = None,
        department:    Optional[str] = None,
        search:        Optional[str] = None,
        page:          int = 1,
        page_size:     int = 10,
    ) -> dict:
        """
        Powers the attendance table for selected month.
        For employees WITHOUT a record, returns empty zeros
        so HR can fill in the values.
        """

        # 1. Pull all active employees matching org filters
        try:
            from models.employee import Employee
            q = db.query(Employee).filter_by(status="Active")
            if business_unit and business_unit != "All Units":
                q = q.filter_by(business_unit=business_unit)
            if location and location != "All Locations":
                q = q.filter_by(location=location)
            if cost_center and cost_center != "All Cost Centers":
                q = q.filter_by(cost_center=cost_center)
            if department and department != "All Departments":
                q = q.filter_by(department=department)
            if search:
                term = f"%{search.lower()}%"
                q = q.filter(
                    func.lower(Employee.name).like(term) |
                    func.lower(Employee.employee_id).like(term)
                )
            employees = q.order_by(Employee.name).all()
        except ImportError:
            # Fallback: return existing records only
            employees = []

        total = len(employees)
        offset = (page - 1) * page_size
        paged_employees = employees[offset: offset + page_size]

        # 2. Fetch existing records for this month in one query
        emp_ids = [e.employee_id for e in paged_employees]
        existing = {
            r.employee_id: r
            for r in db.query(ManualAttendanceRecord).filter(
                ManualAttendanceRecord.employee_id.in_(emp_ids),
                ManualAttendanceRecord.year  == year,
                ManualAttendanceRecord.month == month,
            ).all()
        }

        # 3. Build rows — use existing record or zero defaults
        items = []
        for emp in paged_employees:
            record = existing.get(emp.employee_id)
            if record:
                items.append(_build_row(db, record))
            else:
                # Return an unsaved row with zeros for HR to fill in
                items.append({
                    "id":            None,
                    "employee_id":   emp.employee_id,
                    "employee_name": emp.name,
                    "employee_code": emp.employee_id,
                    "business_unit": getattr(emp, "business_unit", ""),
                    "location":      getattr(emp, "location",      ""),
                    "cost_center":   getattr(emp, "cost_center",   ""),
                    "department":    getattr(emp, "department",     ""),
                    "year":          year,
                    "month":         month,
                    "period_label":  _period_label(year, month),
                    "counts":        {"P":0,"A":0,"H":0,"W":0,"CO":0,"CL":0,"LW":0},
                    "is_saved":      False,
                    "updated_at":    None,
                })

        total_pages = max(1, -(-total // page_size))
        return {
            "total":        total,
            "page":         page,
            "page_size":    page_size,
            "total_pages":  total_pages,
            "period_label": _period_label(year, month),
            "year":         year,
            "month":        month,
            "items":        items,
        }


# ═══════════════════════════════════════════════════════════
# SAVE SERVICE  (green toggle / save button per row)
# ═══════════════════════════════════════════════════════════

class ManualAttendanceSaveService:

    @staticmethod
    def save_row(
        db:          Session,
        employee_id: str,
        year:        int,
        month:       int,
        counts:      dict,
        saved_by:    Optional[int] = None,
    ) -> dict:
        """
        Save button on one row.
        Upserts the ManualAttendanceRecord and sets is_saved=True.
        """
        record = _get_or_create_record(db, employee_id, year, month)

        record.present_days  = counts.get("P",  0)
        record.absent_days   = counts.get("A",  0)
        record.holiday_days  = counts.get("H",  0)
        record.week_off_days = counts.get("W",  0)
        record.comp_off_days = counts.get("CO", 0)
        record.casual_leave  = counts.get("CL", 0)
        record.leave_wo_pay  = counts.get("LW", 0)
        record.is_saved      = True
        record.saved_by      = saved_by

        db.commit()
        db.refresh(record)
        logger.info("Manual attendance saved: %s %s-%02d", employee_id, year, month)
        return _build_row(db, record)

    @staticmethod
    def bulk_save(
        db:       Session,
        year:     int,
        month:    int,
        rows:     list,
        saved_by: Optional[int] = None,
    ) -> dict:
        """
        Optional bulk save — saves all rows at once.
        """
        saved, failed = 0, []
        for row in rows:
            try:
                ManualAttendanceSaveService.save_row(
                    db=db,
                    employee_id=row.employee_id,
                    year=row.year,
                    month=row.month,
                    counts=row.counts.model_dump(),
                    saved_by=saved_by,
                )
                saved += 1
            except Exception as exc:
                failed.append({"employee_id": row.employee_id, "error": str(exc)})

        return {
            "saved":  saved,
            "failed": failed,
            "message": f"Bulk save complete — {saved} saved, {len(failed)} failed.",
        }


# ═══════════════════════════════════════════════════════════
# EXPORT SERVICE  (Options → Download Attendance)
# ═══════════════════════════════════════════════════════════

class ManualAttendanceExportService:

    @staticmethod
    def export_csv(
        db:          Session,
        year:        int,
        month:       int,
        location:    Optional[str] = None,
        cost_center: Optional[str] = None,
        department:  Optional[str] = None,
    ) -> bytes:
        """
        Download Attendance modal → Download button.
        Exports existing saved records for the month.
        Filename: manual_attendance_SEP-2025.csv
        """
        q = db.query(ManualAttendanceRecord).filter_by(year=year, month=month)
        if location:
            q = q.filter_by(location=location)
        if cost_center:
            q = q.filter_by(cost_center=cost_center)
        if department:
            q = q.filter_by(department=department)

        records = q.order_by(ManualAttendanceRecord.employee_id).all()

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=CSV_EXPORT_HEADERS)
        writer.writeheader()

        for sn, r in enumerate(records, start=1):
            emp = _resolve_employee(db, r.employee_id)
            writer.writerow({
                "sl_no":         sn,
                "employee_code": r.employee_id,
                "employee_name": emp["name"],
                "business_unit": r.business_unit,
                "location":      r.location,
                "cost_center":   r.cost_center,
                "department":    r.department,
                "period":        _period_label(r.year, r.month),
                "P":             r.present_days,
                "A":             r.absent_days,
                "H":             r.holiday_days,
                "W":             r.week_off_days,
                "CO":            r.comp_off_days,
                "CL":            r.casual_leave,
                "LW":            r.leave_wo_pay,
            })

        return output.getvalue().encode("utf-8")


# ═══════════════════════════════════════════════════════════
# IMPORT SERVICE  (Options → Upload Attendance)
# ═══════════════════════════════════════════════════════════

class ManualAttendanceImportService:

    @staticmethod
    def import_csv(
        db:           Session,
        file_content: bytes,
        filename:     str,
        year:         int,
        month:        int,
        uploaded_by:  Optional[int] = None,
    ) -> ManualAttendanceImport:
        """
        Upload Attendance modal → Upload button.
        Expected CSV columns:
          code · period (MMM-YYYY) · P · A · H · W · CO · CL · LW
        Optional: employee_name · business_unit · location · cost_center · department

        Upserts ManualAttendanceRecord for each valid row.
        """
        reader  = csv.DictReader(io.StringIO(file_content.decode("utf-8-sig")))
        headers = set(h.strip().lower() for h in (reader.fieldnames or []))
        missing = {c.lower() for c in CSV_IMPORT_REQUIRED} - headers

        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        errors,  success = [], 0

        for i, row in enumerate(reader, start=2):
            try:
                row = {k.strip().lower(): v.strip() for k, v in row.items()}

                emp_id = row.get("code", "").strip()
                if not emp_id:
                    raise ValueError("Missing employee code.")

                # Validate totals
                counts = {
                    "P":  int(row.get("p",  0)),
                    "A":  int(row.get("a",  0)),
                    "H":  int(row.get("h",  0)),
                    "W":  int(row.get("w",  0)),
                    "CO": int(row.get("co", 0)),
                    "CL": int(row.get("cl", 0)),
                    "LW": int(row.get("lw", 0)),
                }
                total = sum(counts.values())
                _, days_in_month = calendar.monthrange(year, month)
                if total > days_in_month:
                    raise ValueError(
                        f"Total days {total} > days in month {days_in_month}."
                    )

                record = _get_or_create_record(db, emp_id, year, month)
                record.present_days  = counts["P"]
                record.absent_days   = counts["A"]
                record.holiday_days  = counts["H"]
                record.week_off_days = counts["W"]
                record.comp_off_days = counts["CO"]
                record.casual_leave  = counts["CL"]
                record.leave_wo_pay  = counts["LW"]
                record.is_saved      = True
                record.saved_by      = uploaded_by
                success += 1

            except Exception as exc:
                errors.append({
                    "row":         i,
                    "employee_id": row.get("code", "?"),
                    "error":       str(exc),
                })

        # Determine batch status
        if success == 0:
            batch_status = ImportStatusEnum.failed
        elif errors:
            batch_status = ImportStatusEnum.partial
        else:
            batch_status = ImportStatusEnum.success

        batch = ManualAttendanceImport(
            filename=filename,
            period_year=year,
            period_month=month,
            total_rows=success + len(errors),
            success_rows=success,
            failed_rows=len(errors),
            error_log=errors,
            status=batch_status,
            uploaded_by=uploaded_by,
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        logger.info(
            "Manual attendance import: %s — %d ok / %d failed",
            filename, success, len(errors),
        )
        return batch
