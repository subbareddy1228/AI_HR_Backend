import io
import csv
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from model.HR_Automation.daily_attendance import DailyAttendanceRecord
from model.HR_Automation.shift import Shift
from model.onboarding.employee import Employee
from schema.HR_Automation.daily_attendance import (
    DailyAttendanceCreate,
    DailyAttendanceUpdate,
    DailyAttendanceFilter,
    DailyAttendanceOut,
    PaginatedDailyAttendance,
    ShiftTimeline,
    FilterOptions,
    BulkUploadPayload,
)




def _parse_time_to_float(t: Optional[str]) -> float:
    
    if not t:
        return 0.0
    try:
        t = t.strip().upper()
        ampm = t[-1]
        parts = t[:-1].split(":")
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        if ampm == "P" and h != 12:
            h += 12
        if ampm == "A" and h == 12:
            h = 0
        return h + m / 60
    except Exception:
        return 0.0


def _calc_worked_hours(check_in: Optional[str], check_out: Optional[str]) -> float:
    if not check_in or not check_out:
        return 0.0
    diff = _parse_time_to_float(check_out) - _parse_time_to_float(check_in)
    return round(max(diff, 0.0), 2)


def _hours_to_display(hours: float) -> str:
   
    h = int(hours)
    m = int(round((hours - h) * 60))
    return f"{h} h {m} m"


def _infer_status(
    check_in: Optional[str],
    check_out: Optional[str],
    worked_hours: float,
    grace_minutes: int = 10,
    shift_start: str = "09:00A",
) -> tuple[str, bool, bool]:
  
    if not check_in:
        return "Absent", False, False

    is_late = False
    grace_float = grace_minutes / 60
    shift_start_float = _parse_time_to_float(shift_start)
    checkin_float = _parse_time_to_float(check_in)

    if checkin_float > (shift_start_float + grace_float):
        is_late = True

    if worked_hours > 0 and worked_hours < 4:
        return "Half Day", is_late, True

    if is_late:
        return "Late", True, False

    return "Present", False, False


def _get_shift(db: Session, shift_name: Optional[str]) -> Optional[Shift]:
    if not shift_name:
        return db.query(Shift).filter(Shift.is_active == True).first()
    return db.query(Shift).filter(Shift.shift_name == shift_name).first()


def _build_timeline(shift: Optional[Shift]) -> ShiftTimeline:
    
    if not shift:
        return ShiftTimeline()
    start = shift.start_time.strftime("%I:%M%p")[:-1].lstrip("0") or "9:00A"
    end   = shift.end_time.strftime("%I:%M%p")[:-1].lstrip("0") or "6:00P"
    return ShiftTimeline(
        shift_name=shift.shift_name,
        shift_start="03:00A",
        shift_end="12:00A",
        work_start=start,
        work_end=end,
    )


def _to_out(record: DailyAttendanceRecord, emp: Employee, shift: Optional[Shift]) -> DailyAttendanceOut:
    return DailyAttendanceOut(
        id=record.id,
        employee_id=record.employee_id,
        employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
        employee_code=emp.employee_code,
        designation=emp.designation,
        department=emp.department,
        location=emp.location,
        att_date=record.att_date,
        status=record.status,
        remarks=record.remarks,
        shift_name=record.shift_name,
        check_in=record.check_in,
        check_in_source=record.check_in_source,
        check_out=record.check_out,
        check_out_source=record.check_out_source,
        worked_hours=record.worked_hours,
        in_time_display=_hours_to_display(record.worked_hours),
        is_late=record.is_late,
        is_half_day=record.is_half_day,
        timeline=_build_timeline(shift),
    )


def _get_or_404(db: Session, record_id: int) -> DailyAttendanceRecord:
    rec = db.query(DailyAttendanceRecord).filter(DailyAttendanceRecord.id == record_id).first()
    if not rec:
        raise HTTPException(404, "Attendance record not found.")
    return rec




class DailyAttendanceService:

    

    def get_filter_options(self, db: Session) -> FilterOptions:
        emps = db.query(Employee).filter(Employee.is_active == True).all()
        return FilterOptions(
            business_units=sorted({e.business_unit for e in emps if e.business_unit}),
            locations=sorted({e.location for e in emps if e.location}),
            cost_centers=sorted({e.cost_center for e in emps if e.cost_center}),
            departments=sorted({e.department for e in emps if e.department}),
        )

  

    def list_attendance(
        self, db: Session, filters: DailyAttendanceFilter
    ) -> PaginatedDailyAttendance:
        
        q = (
            db.query(DailyAttendanceRecord, Employee)
            .join(Employee, Employee.id == DailyAttendanceRecord.employee_id)
            .filter(DailyAttendanceRecord.att_date == filters.att_date)
        )

        if filters.business_unit and filters.business_unit not in ("All Units", "All", ""):
            q = q.filter(Employee.business_unit == filters.business_unit)
        if filters.location and filters.location not in ("All", ""):
            q = q.filter(Employee.location == filters.location)
        if filters.cost_center and filters.cost_center not in ("All", ""):
            q = q.filter(Employee.cost_center == filters.cost_center)
        if filters.department and filters.department not in ("All", ""):
            q = q.filter(Employee.department == filters.department)
        if filters.employee_id:
            q = q.filter(DailyAttendanceRecord.employee_id == filters.employee_id)

        
        if filters.late_only:
            q = q.filter(DailyAttendanceRecord.is_late == True)
        if filters.absent_only:
            q = q.filter(DailyAttendanceRecord.status == "Absent")
        if filters.no_punches:
            q = q.filter(DailyAttendanceRecord.check_in == None)

        total = q.count()
        rows  = (
            q.order_by(Employee.first_name)
             .offset((filters.page - 1) * filters.page_size)
             .limit(filters.page_size)
             .all()
        )

        items = []
        for record, emp in rows:
            shift = _get_shift(db, record.shift_name)
            items.append(_to_out(record, emp, shift))

        return PaginatedDailyAttendance(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            items=items,
        )

    

    def get_record(self, db: Session, record_id: int) -> DailyAttendanceOut:
        rec = _get_or_404(db, record_id)
        emp = db.query(Employee).filter(Employee.id == rec.employee_id).first()
        shift = _get_shift(db, rec.shift_name)
        return _to_out(rec, emp, shift)

    

    def create_record(self, db: Session, payload: DailyAttendanceCreate) -> DailyAttendanceOut:
        
        existing = db.query(DailyAttendanceRecord).filter(
            DailyAttendanceRecord.employee_id == payload.employee_id,
            DailyAttendanceRecord.att_date    == payload.att_date,
        ).first()
        if existing:
            raise HTTPException(409, "Attendance record already exists for this employee on this date.")

        worked = _calc_worked_hours(payload.check_in, payload.check_out)
        status, is_late, is_half = _infer_status(payload.check_in, payload.check_out, worked)

        
        final_status  = payload.status or status
        final_is_late = payload.is_late or is_late
        final_is_half = payload.is_half_day or is_half

        rec = DailyAttendanceRecord(
            employee_id=payload.employee_id,
            att_date=payload.att_date,
            status=final_status,
            remarks=payload.remarks,
            shift_name=payload.shift_name,
            check_in=payload.check_in,
            check_in_source=payload.check_in_source,
            check_out=payload.check_out,
            check_out_source=payload.check_out_source,
            worked_hours=worked,
            is_late=final_is_late,
            is_half_day=final_is_half,
            is_manual=True,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

        emp   = db.query(Employee).filter(Employee.id == rec.employee_id).first()
        shift = _get_shift(db, rec.shift_name)
        return _to_out(rec, emp, shift)

   

    def update_record(
        self, db: Session, record_id: int, payload: DailyAttendanceUpdate
    ) -> DailyAttendanceOut:
        rec = _get_or_404(db, record_id)

        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(rec, k, v)

        
        if payload.check_in is not None or payload.check_out is not None:
            rec.worked_hours = _calc_worked_hours(rec.check_in, rec.check_out)
            status, is_late, is_half = _infer_status(rec.check_in, rec.check_out, rec.worked_hours)
            if payload.status is None:
                rec.status = status
            rec.is_late     = is_late
            rec.is_half_day = is_half

        rec.is_manual  = True
        rec.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rec)

        emp   = db.query(Employee).filter(Employee.id == rec.employee_id).first()
        shift = _get_shift(db, rec.shift_name)
        return _to_out(rec, emp, shift)

    

    def delete_record(self, db: Session, record_id: int) -> dict:
        rec = _get_or_404(db, record_id)
        db.delete(rec)
        db.commit()
        return {"message": "Attendance record deleted.", "deleted_id": record_id}



    def bulk_upload(self, db: Session, payload: BulkUploadPayload) -> dict:
        
        created, updated, errors = 0, 0, []

        for row in payload.rows:
            emp = db.query(Employee).filter(
                Employee.employee_code == row.employee_code
            ).first()
            if not emp:
                errors.append(f"Employee code '{row.employee_code}' not found.")
                continue

            worked = _calc_worked_hours(row.check_in, row.check_out)
            status, is_late, is_half = _infer_status(row.check_in, row.check_out, worked)

            existing = db.query(DailyAttendanceRecord).filter(
                DailyAttendanceRecord.employee_id == emp.id,
                DailyAttendanceRecord.att_date    == row.att_date,
            ).first()

            if existing:
                existing.check_in         = row.check_in or existing.check_in
                existing.check_in_source  = row.check_in_source or existing.check_in_source
                existing.check_out        = row.check_out or existing.check_out
                existing.check_out_source = row.check_out_source or existing.check_out_source
                existing.worked_hours     = _calc_worked_hours(existing.check_in, existing.check_out)
                s, l, h = _infer_status(existing.check_in, existing.check_out, existing.worked_hours)
                existing.status     = s
                existing.is_late    = l
                existing.is_half_day = h
                existing.is_uploaded = True
                existing.updated_at  = datetime.utcnow()
                updated += 1
            else:
                db.add(DailyAttendanceRecord(
                    employee_id=emp.id,
                    att_date=row.att_date,
                    check_in=row.check_in,
                    check_in_source=row.check_in_source,
                    check_out=row.check_out,
                    check_out_source=row.check_out_source,
                    worked_hours=worked,
                    status=status,
                    is_late=is_late,
                    is_half_day=is_half,
                    is_uploaded=True,
                ))
                created += 1

        db.commit()
        return {"created": created, "updated": updated, "errors": errors}

    

    def download_csv(self, db: Session, att_date: date) -> str:
       
        records = (
            db.query(DailyAttendanceRecord, Employee)
            .join(Employee, Employee.id == DailyAttendanceRecord.employee_id)
            .filter(DailyAttendanceRecord.att_date == att_date)
            .order_by(Employee.first_name)
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Employee Code", "Employee Name", "Designation", "Department",
            "Location", "Date", "Status", "Check In", "Check In Source",
            "Check Out", "Check Out Source", "Worked Hours", "Is Late",
        ])
        for rec, emp in records:
            writer.writerow([
                emp.employee_code,
                f"{emp.first_name} {emp.last_name or ''}".strip(),
                emp.designation or "",
                emp.department or "",
                emp.location or "",
                str(rec.att_date),
                rec.status,
                rec.check_in or "--",
                rec.check_in_source or "",
                rec.check_out or "--",
                rec.check_out_source or "",
                rec.worked_hours,
                "Yes" if rec.is_late else "No",
            ])

        return output.getvalue()



daily_attendance_service = DailyAttendanceService()