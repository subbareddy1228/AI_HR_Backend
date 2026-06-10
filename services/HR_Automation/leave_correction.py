"""
services/leave_correction_service.py
Business logic for Leave Correction module.
"""

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from model.HR_Automation.leave_correction import (
    LeaveCorrectionRecord,
    LeaveCorrectionImport,
    ImportStatusEnum,
)
from schema.HR_Automation.leave_correction import (
    LEAVE_TYPE_OPTIONS,
    LEAVE_TYPE_CODES,
    period_label,
    MONTH_LABELS,
)

logger = logging.getLogger(__name__)

EXPORT_HEADERS = [
    "sl_no", "employee_code", "employee_name", "designation",
    "business_unit", "location", "cost_center", "department",
    "period", "leave_type_code", "leave_type_label",
    "opening", "activity", "correction", "closing",
]

IMPORT_REQUIRED_COLS = {"code", "leave_type_code", "period", "correction"}


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _resolve_employee(db: Session, employee_id: str) -> dict:
    result = {
        "name": employee_id, "code": employee_id, "designation": "",
        "business_unit": "", "location": "", "cost_center": "", "department": "",
    }
    try:
        from models.employee import Employee
        emp = db.query(Employee).filter_by(employee_id=employee_id).first()
        if emp:
            result.update({
                "name":          emp.name,
                "code":          emp.employee_id,
                "designation":   getattr(emp, "position",      ""),
                "business_unit": getattr(emp, "business_unit", ""),
                "location":      getattr(emp, "location",      ""),
                "cost_center":   getattr(emp, "cost_center",   ""),
                "department":    getattr(emp, "department",     ""),
            })
    except ImportError:
        pass
    return result


def _leave_type_label(code: str) -> str:
    for opt in LEAVE_TYPE_OPTIONS:
        if opt["code"] == code:
            return opt["label"]
    return code


def _get_or_create_record(
    db:              Session,
    employee_id:     str,
    leave_type_code: str,
    year:            int,
    month:           int,
) -> LeaveCorrectionRecord:
    record = db.query(LeaveCorrectionRecord).filter_by(
        employee_id=employee_id,
        leave_type_code=leave_type_code,
        year=year,
        month=month,
    ).first()

    if not record:
        emp = _resolve_employee(db, employee_id)

        # Pull opening balance from LeaveBalance if available
        opening = 0.0
        try:
            from models.leave_management import LeaveBalance, LeaveType
            lt = db.query(LeaveType).filter_by(code=leave_type_code).first()
            if lt:
                bal = db.query(LeaveBalance).filter_by(
                    employee_id=employee_id,
                    leave_type_id=lt.id,
                    year=year,
                ).first()
                if bal:
                    opening = float(bal.balance)
        except ImportError:
            pass

        # Pull activity from approved leave applications
        activity = 0.0
        try:
            from models.leave_management import LeaveApplication, ApplicationStatusEnum, LeaveType as LT
            lt2 = db.query(LT).filter_by(code=leave_type_code).first()
            if lt2:
                result = db.query(func.sum(LeaveApplication.days)).filter(
                    LeaveApplication.employee_id == employee_id,
                    LeaveApplication.leave_type_id == lt2.id,
                    LeaveApplication.status == ApplicationStatusEnum.approved,
                    func.extract("year",  LeaveApplication.start_date) == year,
                    func.extract("month", LeaveApplication.start_date) == month,
                ).scalar()
                activity = float(result or 0)
        except ImportError:
            pass

        record = LeaveCorrectionRecord(
            employee_id=employee_id,
            leave_type_code=leave_type_code,
            leave_type_label=_leave_type_label(leave_type_code),
            year=year,
            month=month,
            business_unit=emp["business_unit"],
            location=emp["location"],
            cost_center=emp["cost_center"],
            department=emp["department"],
            opening=opening,
            activity=activity,
            correction=0.0,
            closing=opening + activity,
        )
        db.add(record)
        db.flush()

    return record


def _build_row(db: Session, record: LeaveCorrectionRecord) -> dict:
    emp = _resolve_employee(db, record.employee_id)
    return {
        "id":               record.id,
        "employee_id":      record.employee_id,
        "employee_name":    emp["name"],
        "employee_code":    emp["code"],
        "designation":      emp["designation"],
        "business_unit":    record.business_unit or emp["business_unit"],
        "location":         record.location      or emp["location"],
        "cost_center":      record.cost_center   or emp["cost_center"],
        "department":       record.department    or emp["department"],
        "leave_type_code":  record.leave_type_code,
        "leave_type_label": record.leave_type_label,
        "year":             record.year,
        "month":            record.month,
        "period_label":     period_label(record.year, record.month),
        "opening":          record.opening,
        "activity":         record.activity,
        "correction":       record.correction,
        "closing":          record.closing,
        "is_saved":         record.is_saved,
        "saved_at":         record.saved_at,
        "updated_at":       record.updated_at,
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
                "business_units":     ["All Units"]       + _distinct(Employee.business_unit),
                "locations":          ["All Locations"]   + _distinct(Employee.location),
                "cost_centers":       ["All Cost Centers"]+ _distinct(Employee.cost_center),
                "departments":        ["All Locations"]   + _distinct(Employee.department),
                "leave_type_options": LEAVE_TYPE_OPTIONS,
            }
        except ImportError:
            return {
                "business_units":     ["All Units"],
                "locations":          ["All Locations"],
                "cost_centers":       ["All Cost Centers"],
                "departments":        ["All Locations"],
                "leave_type_options": LEAVE_TYPE_OPTIONS,
            }


# ═══════════════════════════════════════════════════════════
# LIST SERVICE  (paginated correction table)
# ═══════════════════════════════════════════════════════════

class LeaveCorrectionListService:

    @staticmethod
    def list_records(
        db:              Session,
        year:            int,
        month:           int,
        leave_type_code: str = "LV458",
        business_unit:   Optional[str] = None,
        location:        Optional[str] = None,
        cost_center:     Optional[str] = None,
        department:      Optional[str] = None,
        search:          Optional[str] = None,
        page:            int = 1,
        page_size:       int = 10,
    ) -> dict:
        """
        Powers the Leave Correction table.
        Returns one row per active employee for the selected month + leave type.
        Employees without an existing record get auto-initialized rows
        with opening/activity pulled from LeaveBalance + LeaveApplication.
        """
        # 1. Pull employees matching org filters
        try:
            from models.employee import Employee
            q = db.query(Employee).filter_by(status="Active")
            if business_unit and business_unit != "All Units":
                q = q.filter_by(business_unit=business_unit)
            if location and location not in ("All Locations", "All"):
                q = q.filter_by(location=location)
            if cost_center and cost_center != "All Cost Centers":
                q = q.filter_by(cost_center=cost_center)
            if department and department not in ("All Locations", "All"):
                q = q.filter_by(department=department)
            if search:
                term = f"%{search.lower()}%"
                q = q.filter(
                    func.lower(Employee.name).like(term) |
                    func.lower(Employee.employee_id).like(term)
                )
            employees = q.order_by(Employee.name).all()
        except ImportError:
            employees = []

        total  = len(employees)
        offset = (page - 1) * page_size
        paged  = employees[offset: offset + page_size]

        # 2. Fetch existing records for this page in one query
        emp_ids  = [e.employee_id for e in paged]
        existing = {
            r.employee_id: r
            for r in db.query(LeaveCorrectionRecord).filter(
                LeaveCorrectionRecord.employee_id.in_(emp_ids),
                LeaveCorrectionRecord.leave_type_code == leave_type_code,
                LeaveCorrectionRecord.year  == year,
                LeaveCorrectionRecord.month == month,
            ).all()
        }

        # 3. Build rows — auto-create missing records with live opening/activity
        items = []
        for emp in paged:
            if emp.employee_id in existing:
                items.append(_build_row(db, existing[emp.employee_id]))
            else:
                record = _get_or_create_record(
                    db, emp.employee_id, leave_type_code, year, month
                )
                db.commit()
                items.append(_build_row(db, record))

        total_pages = max(1, -(-total // page_size))
        return {
            "total":            total,
            "page":             page,
            "page_size":        page_size,
            "total_pages":      total_pages,
            "period_label":     period_label(year, month),
            "year":             year,
            "month":            month,
            "leave_type_code":  leave_type_code,
            "leave_type_label": _leave_type_label(leave_type_code),
            "items":            items,
            "note":             "Corrections are added at the beginning of the period.",
        }


# ═══════════════════════════════════════════════════════════
# SAVE SERVICE  (green circle button)
# ═══════════════════════════════════════════════════════════

class LeaveCorrectionSaveService:

    @staticmethod
    def save_row(
        db:              Session,
        employee_id:     str,
        leave_type_code: str,
        year:            int,
        month:           int,
        correction:      float,
        saved_by:        Optional[int] = None,
    ) -> dict:
        """
        Green circle button on each row.
        Updates `correction`, recomputes `closing`, sets is_saved=True.
        Also updates LeaveBalance.balance with the correction delta.
        """
        record = _get_or_create_record(db, employee_id, leave_type_code, year, month)
        old_correction = record.correction

        record.correction = correction
        record.closing    = record.opening + record.activity + correction
        record.is_saved   = True
        record.saved_by   = saved_by
        record.saved_at   = datetime.now(timezone.utc)

        # Apply delta to LeaveBalance
        delta = correction - old_correction
        if delta != 0:
            try:
                from models.leave_management import LeaveBalance, LeaveType
                lt = db.query(LeaveType).filter_by(code=leave_type_code).first()
                if lt:
                    bal = db.query(LeaveBalance).filter_by(
                        employee_id=employee_id,
                        leave_type_id=lt.id,
                        year=year,
                    ).first()
                    if bal:
                        bal.balance += delta
            except ImportError:
                pass

        db.commit()
        db.refresh(record)
        logger.info(
            "Leave correction saved: %s %s %s-%02d correction=%s",
            employee_id, leave_type_code, year, month, correction,
        )
        return _build_row(db, record)

    @staticmethod
    def bulk_save(
        db:       Session,
        rows:     list,
        saved_by: Optional[int] = None,
    ) -> dict:
        saved, failed = 0, []
        for row in rows:
            try:
                LeaveCorrectionSaveService.save_row(
                    db=db,
                    employee_id=row.employee_id,
                    leave_type_code=row.leave_type_code,
                    year=row.year,
                    month=row.month,
                    correction=row.correction,
                    saved_by=saved_by,
                )
                saved += 1
            except Exception as exc:
                failed.append({"employee_id": row.employee_id, "error": str(exc)})
        return {
            "saved":   saved,
            "failed":  failed,
            "message": f"Bulk save complete — {saved} saved, {len(failed)} failed.",
        }


# ═══════════════════════════════════════════════════════════
# EXPORT SERVICE  (Options → Download)
# ═══════════════════════════════════════════════════════════

class LeaveCorrectionExportService:

    @staticmethod
    def export_csv(
        db:              Session,
        year:            int,
        month:           int,
        leave_type_code: Optional[str] = None,
        location:        Optional[str] = None,
        cost_center:     Optional[str] = None,
        department:      Optional[str] = None,
    ) -> bytes:
        """
        Options → Download → Download button.
        Exports all saved correction records as CSV.
        """
        q = db.query(LeaveCorrectionRecord).filter_by(year=year, month=month)
        if leave_type_code:
            q = q.filter_by(leave_type_code=leave_type_code)
        if location:
            q = q.filter_by(location=location)
        if cost_center:
            q = q.filter_by(cost_center=cost_center)
        if department:
            q = q.filter_by(department=department)

        records = q.order_by(LeaveCorrectionRecord.employee_id).all()
        output  = io.StringIO()
        writer  = csv.DictWriter(output, fieldnames=EXPORT_HEADERS)
        writer.writeheader()

        for sn, r in enumerate(records, start=1):
            emp = _resolve_employee(db, r.employee_id)
            writer.writerow({
                "sl_no":           sn,
                "employee_code":   r.employee_id,
                "employee_name":   emp["name"],
                "designation":     emp["designation"],
                "business_unit":   r.business_unit,
                "location":        r.location,
                "cost_center":     r.cost_center,
                "department":      r.department,
                "period":          period_label(r.year, r.month),
                "leave_type_code": r.leave_type_code,
                "leave_type_label":r.leave_type_label,
                "opening":         r.opening,
                "activity":        r.activity,
                "correction":      r.correction,
                "closing":         r.closing,
            })

        return output.getvalue().encode("utf-8")


# ═══════════════════════════════════════════════════════════
# IMPORT SERVICE  (Options → Upload)
# ═══════════════════════════════════════════════════════════

class LeaveCorrectionImportService:

    @staticmethod
    def import_csv(
        db:              Session,
        file_content:    bytes,
        filename:        str,
        year:            int,
        month:           int,
        leave_type_code: Optional[str],
        uploaded_by:     Optional[int] = None,
    ) -> LeaveCorrectionImport:
        """
        Options → Upload → Upload button.
        Accepts CSV with columns:
          code · leave_type_code · period (MMM-YYYY) · correction
        Optional: opening · activity
        """
        reader  = csv.DictReader(io.StringIO(file_content.decode("utf-8-sig")))
        headers = {h.strip().lower() for h in (reader.fieldnames or [])}
        missing = {c.lower() for c in IMPORT_REQUIRED_COLS} - headers

        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        errors, success = [], 0

        for i, row in enumerate(reader, start=2):
            try:
                row = {k.strip().lower(): v.strip() for k, v in row.items()}
                emp_id   = row.get("code", "").strip()
                lt_code  = (row.get("leave_type_code") or leave_type_code or "").strip().upper()
                corr_val = float(row.get("correction", 0))

                if not emp_id:
                    raise ValueError("Missing employee code.")
                if lt_code not in LEAVE_TYPE_CODES:
                    raise ValueError(f"Unknown leave_type_code '{lt_code}'.")

                LeaveCorrectionSaveService.save_row(
                    db=db,
                    employee_id=emp_id,
                    leave_type_code=lt_code,
                    year=year,
                    month=month,
                    correction=corr_val,
                    saved_by=uploaded_by,
                )
                success += 1

            except Exception as exc:
                errors.append({
                    "row":         i,
                    "employee_id": row.get("code", "?"),
                    "error":       str(exc),
                })

        if success == 0:
            batch_status = ImportStatusEnum.failed
        elif errors:
            batch_status = ImportStatusEnum.partial
        else:
            batch_status = ImportStatusEnum.success

        batch = LeaveCorrectionImport(
            filename=filename,
            period_year=year,
            period_month=month,
            leave_type_code=leave_type_code,
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
            "Leave correction import: %s — %d ok / %d failed",
            filename, success, len(errors),
        )
        return batch
