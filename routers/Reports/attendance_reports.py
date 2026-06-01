from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from core.database import get_db
from typing import Optional
from datetime import date, timedelta

try:
    from model.models import AttendanceRecord
except ImportError:
    AttendanceRecord = None

try:
    from model.onboarding.employee import Employee
except ImportError:
    Employee = None

router = APIRouter(prefix="/attendance", tags=["Reports"])


@router.get("/daily-summary")
def daily_summary(
    report_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
):
    if AttendanceRecord is None:
        return {
            "report_date": str(report_date),
            "total_present": 0,
            "total_absent": 0,
            "total_late": 0,
            "total_half_day": 0,
            "message": "AttendanceRecord model not available",
        }

    rows = db.execute(
        select(AttendanceRecord.status, func.count(AttendanceRecord.id).label("count"))
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

    query = select(
        AttendanceRecord.employee_id if hasattr(AttendanceRecord, "employee_id") else AttendanceRecord.id,
        AttendanceRecord.status,
        func.count(AttendanceRecord.id).label("count"),
    ).where(
        func.extract("month", AttendanceRecord.date) == month,
        func.extract("year", AttendanceRecord.date) == year,
    )

    # If AttendanceRecord has employee_id, group by it
    try:
        query = (
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
        )

        rows = db.execute(query).all()
    except Exception:
        return {"data": [], "message": "Unable to query attendance records"}

    # Aggregate per employee
    per_employee: dict = {}
    for row in rows:
        emp_id = row.employee_id
        if emp_id not in per_employee:
            per_employee[emp_id] = {
                "employee_id": emp_id,
                "days_present": 0,
                "days_absent": 0,
                "days_late": 0,
                "days_half": 0,
            }
        status_map = {
            "Present": "days_present",
            "Absent": "days_absent",
            "Late": "days_late",
            "Half Day": "days_half",
        }
        key = status_map.get(row.status)
        if key:
            per_employee[emp_id][key] = row.count

    return {
        "month": month,
        "year": year,
        "data": list(per_employee.values()),
        "total_employees": len(per_employee),
    }


@router.get("/absenteeism-trend")
def absenteeism_trend(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
):
    if AttendanceRecord is None:
        return {"data": [], "message": "AttendanceRecord model not available"}

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

    data = [{"date": str(row.date), "absent_count": row.absent_count} for row in rows]
    return {"start_date": str(start_date), "end_date": str(end_date), "data": data}
