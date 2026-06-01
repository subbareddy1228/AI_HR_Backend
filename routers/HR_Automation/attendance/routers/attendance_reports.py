from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date

from core.database import get_db

try:
    from model.models import AttendanceRecord
except ImportError:
    AttendanceRecord = None

router = APIRouter(prefix="/attendance-reports", tags=["Attendance Reports"])


@router.get("/daily-summary")
def daily_summary(
    report_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
):
    if AttendanceRecord is None:
        return {"report_date": str(report_date), "message": "AttendanceRecord model not available"}

    rows = db.execute(
        __import__("sqlalchemy").select(
            AttendanceRecord.status,
            func.count(AttendanceRecord.id).label("count")
        )
        .where(AttendanceRecord.date == report_date)
        .group_by(AttendanceRecord.status)
    ).all()

    summary = {"Present": 0, "Absent": 0, "Late": 0, "Half Day": 0}
    for row in rows:
        if row.status in summary:
            summary[row.status] = row.count

    return {
        "report_date": str(report_date),
        "total_present": summary["Present"],
        "total_absent": summary["Absent"],
        "total_late": summary["Late"],
        "total_half_day": summary["Half Day"],
    }


@router.get("/monthly-summary")
def monthly_summary(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if AttendanceRecord is None:
        return {"data": [], "message": "AttendanceRecord model not available"}

    from sqlalchemy import select
    try:
        rows = db.execute(
            select(
                AttendanceRecord.employee_id,
                AttendanceRecord.status,
                func.count(AttendanceRecord.id).label("count"),
            )
            .where(
                func.extract("month", AttendanceRecord.date) == month,
                func.extract("year", AttendanceRecord.date) == year,
            )
            .group_by(AttendanceRecord.employee_id, AttendanceRecord.status)
        ).all()
    except Exception:
        return {"data": [], "message": "Unable to query attendance records"}

    per_employee: dict = {}
    for row in rows:
        eid = row.employee_id
        if eid not in per_employee:
            per_employee[eid] = {"employee_id": eid, "present": 0, "absent": 0, "late": 0, "half_day": 0}
        mapping = {"Present": "present", "Absent": "absent", "Late": "late", "Half Day": "half_day"}
        key = mapping.get(row.status)
        if key:
            per_employee[eid][key] = row.count

    return {"month": month, "year": year, "data": list(per_employee.values()), "total_employees": len(per_employee)}


@router.get("/absenteeism-trend")
def absenteeism_trend(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
):
    if AttendanceRecord is None:
        return {"data": [], "message": "AttendanceRecord model not available"}

    from sqlalchemy import select
    rows = db.execute(
        select(AttendanceRecord.date, func.count(AttendanceRecord.id).label("absent_count"))
        .where(
            AttendanceRecord.status == "Absent",
            AttendanceRecord.date >= start_date,
            AttendanceRecord.date <= end_date,
        )
        .group_by(AttendanceRecord.date)
        .order_by(AttendanceRecord.date)
    ).all()

    return {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "data": [{"date": str(row.date), "absent_count": row.absent_count} for row in rows],
    }


@router.get("/employee-summary/{employee_id}")
def employee_attendance_summary(
    employee_id: int,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    if AttendanceRecord is None:
        return {"employee_id": employee_id, "message": "AttendanceRecord model not available"}

    from sqlalchemy import select
    rows = db.execute(
        select(AttendanceRecord.status, func.count(AttendanceRecord.id).label("count"))
        .where(
            AttendanceRecord.employee_id == employee_id,
            func.extract("month", AttendanceRecord.date) == month,
            func.extract("year", AttendanceRecord.date) == year,
        )
        .group_by(AttendanceRecord.status)
    ).all()

    summary = {"Present": 0, "Absent": 0, "Late": 0, "Half Day": 0}
    for row in rows:
        if row.status in summary:
            summary[row.status] = row.count

    return {
        "employee_id": employee_id,
        "month": month,
        "year": year,
        "days_present": summary["Present"],
        "days_absent": summary["Absent"],
        "days_late": summary["Late"],
        "days_half_day": summary["Half Day"],
    }
