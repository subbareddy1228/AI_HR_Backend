from datetime import datetime, date
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import or_

from model.HR_Automation.daily_punches import DailyPunchSummary
from model.HR_Automation.attendance_capture import BiometricPunch, GPSAttendance, WebPortalAttendance
from model.onboarding.employee import Employee
from schema.HR_Automation.daily_punches import (
    DailyPunchCreate, DailyPunchUpdate,
    ManualPunchCreate, RegularisePunch,
    DailyPunchesFilter,
    DailyPunchOut, PaginatedDailyPunchesResponse,
    PunchTime, AttendanceMark, ProcessStatus,
)


def _format_duration(in_t: Optional[str], out_t: Optional[str]) -> str:
    if not in_t or not out_t:
        return "0h 0m"
    try:
        fmt = "%I:%M %p"
        diff = datetime.strptime(out_t, fmt) - datetime.strptime(in_t, fmt)
        total_min = int(diff.total_seconds() // 60)
        if total_min < 0:
            return "0h 0m"
        return f"{total_min // 60}h {total_min % 60}m"
    except Exception:
        return "0h 0m"


def _to_punch_out(row: DailyPunchSummary, emp: Employee, sn: int) -> DailyPunchOut:
    return DailyPunchOut(
        id=row.id,
        sn=sn,
        employee_id=row.employee_id,
        employee_name=f"{emp.first_name} {emp.last_name or ''}".strip() if emp else "",
        employee_code=emp.employee_code if emp else None,
        designation=emp.designation if emp else None,
        department=emp.department if emp else None,
        business_unit=emp.business_unit if emp else None,
        location_name=emp.location if emp else None,
        cost_center=emp.cost_center if emp else None,
        summary_date=row.summary_date,
        start=PunchTime(time=row.in_time),
        end=PunchTime(time=row.out_time),
        duration=row.duration,
        attendance_mark=AttendanceMark(row.attendance_mark) if row.attendance_mark in AttendanceMark._value2member_map_ else AttendanceMark.absent,
        is_late=row.is_late,
        process_status=ProcessStatus(row.process_status) if row.process_status in ProcessStatus._value2member_map_ else ProcessStatus.pending,
    )


class DailyPunchesService:

    def get_daily_punches(self, db: Session, filters: DailyPunchesFilter) -> PaginatedDailyPunchesResponse:
        q = (
            db.query(DailyPunchSummary, Employee)
            .join(Employee, Employee.id == DailyPunchSummary.employee_id)
            .filter(DailyPunchSummary.summary_date == filters.punch_date)
        )

        if filters.employee_id:
            q = q.filter(DailyPunchSummary.employee_id == filters.employee_id)
        if filters.business_unit:
            q = q.filter(Employee.business_unit == filters.business_unit)
        if filters.location:
            q = q.filter(Employee.location == filters.location)
        if filters.cost_center:
            q = q.filter(Employee.cost_center == filters.cost_center)
        if filters.department:
            q = q.filter(Employee.department == filters.department)
        if filters.late_only:
            q = q.filter(DailyPunchSummary.is_late == True)
        if filters.absent_only:
            q = q.filter(DailyPunchSummary.attendance_mark == "Absent")
        if filters.no_punches:
            q = q.filter(DailyPunchSummary.in_time == None)

        total = q.count()
        rows  = q.offset((filters.page - 1) * filters.page_size).limit(filters.page_size).all()

        items = [_to_punch_out(row, emp, idx + 1 + (filters.page - 1) * filters.page_size)
                 for idx, (row, emp) in enumerate(rows)]

        return PaginatedDailyPunchesResponse(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            items=items,
        )

    def get_filter_options(self, db: Session) -> dict:
        employees = db.query(Employee).filter(Employee.is_active == True).all()
        departments   = sorted({e.department   for e in employees if e.department})
        business_units = sorted({e.business_unit for e in employees if e.business_unit})
        locations     = sorted({e.location      for e in employees if e.location})
        cost_centers  = sorted({e.cost_center   for e in employees if e.cost_center})
        return {
            "departments":    departments,
            "business_units": business_units,
            "locations":      locations,
            "cost_centers":   cost_centers,
        }

    def get_employee_punches(self, db: Session, employee_id: int, punch_date: date) -> List[DailyPunchSummary]:
        return db.query(DailyPunchSummary).filter(
            DailyPunchSummary.employee_id  == employee_id,
            DailyPunchSummary.summary_date == punch_date,
        ).all()

    def record_punch(self, db: Session, payload: DailyPunchCreate) -> DailyPunchSummary:
        summary = db.query(DailyPunchSummary).filter(
            DailyPunchSummary.employee_id  == payload.employee_id,
            DailyPunchSummary.summary_date == payload.punch_date,
        ).first()

        t = payload.punch_time.strftime("%I:%M %p")

        if not summary:
            summary = DailyPunchSummary(
                employee_id=payload.employee_id,
                summary_date=payload.punch_date,
                attendance_mark="Present",
            )
            db.add(summary)

        if payload.punch_type == "IN":
            summary.in_time = t
        else:
            summary.out_time = t

        summary.duration   = _format_duration(summary.in_time, summary.out_time)
        summary.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(summary)
        return summary

    def add_manual_punch(self, db: Session, payload: ManualPunchCreate) -> DailyPunchSummary:
        summary = db.query(DailyPunchSummary).filter(
            DailyPunchSummary.employee_id  == payload.employee_id,
            DailyPunchSummary.summary_date == payload.punch_date,
        ).first()

        if not summary:
            summary = DailyPunchSummary(
                employee_id=payload.employee_id,
                summary_date=payload.punch_date,
            )
            db.add(summary)

        if payload.in_time:
            summary.in_time = payload.in_time
        if payload.out_time:
            summary.out_time = payload.out_time

        summary.attendance_mark   = "Present"
        summary.duration          = _format_duration(summary.in_time, summary.out_time)
        summary.regularised       = True
        summary.regularise_reason = payload.reason
        summary.updated_at        = datetime.utcnow()
        db.commit()
        db.refresh(summary)
        return summary

    def update_punch(self, db: Session, punch_id: int, payload: DailyPunchUpdate) -> DailyPunchSummary:
        summary = db.query(DailyPunchSummary).filter(DailyPunchSummary.id == punch_id).first()
        if not summary:
            raise ValueError("Punch record not found")
        if payload.punch_time:
            t = payload.punch_time.strftime("%I:%M %p")
            if payload.punch_type == "OUT":
                summary.out_time = t
            else:
                summary.in_time = t
        summary.duration   = _format_duration(summary.in_time, summary.out_time)
        summary.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(summary)
        return summary

    def delete_punch(self, db: Session, punch_id: int) -> bool:
        summary = db.query(DailyPunchSummary).filter(DailyPunchSummary.id == punch_id).first()
        if not summary:
            return False
        db.delete(summary)
        db.commit()
        return True

    def regularise_punch(self, db: Session, payload: RegularisePunch) -> DailyPunchSummary:
        summary = db.query(DailyPunchSummary).filter(
            DailyPunchSummary.employee_id  == payload.employee_id,
            DailyPunchSummary.summary_date == payload.punch_date,
        ).first()
        if not summary:
            raise ValueError("No punch record found for this employee on this date")
        if payload.in_time:
            summary.in_time = payload.in_time
        if payload.out_time:
            summary.out_time = payload.out_time
        summary.regularised       = True
        summary.regularise_reason = payload.reason
        summary.attendance_mark   = "Present"
        summary.duration          = _format_duration(summary.in_time, summary.out_time)
        summary.updated_at        = datetime.utcnow()
        db.commit()
        db.refresh(summary)
        return summary

    def mark_processed(self, db: Session, summary_ids: List[int]) -> int:
        count = 0
        for sid in summary_ids:
            row = db.query(DailyPunchSummary).filter(DailyPunchSummary.id == sid).first()
            if row:
                row.process_status = "Processed"
                row.updated_at     = datetime.utcnow()
                count += 1
        db.commit()
        return count



daily_punches_service = DailyPunchesService()