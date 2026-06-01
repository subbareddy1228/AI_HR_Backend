from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, distinct
from core.database import get_db
from datetime import date, timedelta

try:
    from model.onboarding.employee import Employee
except ImportError:
    Employee = None

try:
    from model.HR_Operations.exit_management import ExitManagement
except ImportError:
    ExitManagement = None

try:
    from model.models import AttendanceRecord
except ImportError:
    AttendanceRecord = None

router = APIRouter(prefix="/dashboard", tags=["Reports"])


@router.get("/overview")
def dashboard_overview(db: Session = Depends(get_db)):
    today = date.today()
    first_of_month = today.replace(day=1)
    result: dict = {}

    # Total active employees
    try:
        result["total_employees"] = db.execute(
            select(func.count(Employee.id)).where(Employee.is_active == True)
        ).scalar() or 0
    except Exception:
        result["total_employees"] = 0

    # Distinct departments
    try:
        result["departments_count"] = db.execute(
            select(func.count(distinct(Employee.department)))
        ).scalar() or 0
    except Exception:
        result["departments_count"] = 0

    # New joiners this month
    try:
        result["new_joiners_this_month"] = db.execute(
            select(func.count(Employee.id)).where(Employee.joining_date >= first_of_month)
        ).scalar() or 0
    except Exception:
        result["new_joiners_this_month"] = 0

    # Exits this month
    try:
        if ExitManagement is not None:
            result["exits_this_month"] = db.execute(
                select(func.count(ExitManagement.id)).where(
                    ExitManagement.last_working_date >= first_of_month
                )
            ).scalar() or 0
        else:
            result["exits_this_month"] = 0
    except Exception:
        result["exits_this_month"] = 0

    # Pending leave approvals
    try:
        from model.models import LeaveRequest
        result["pending_approvals"] = db.execute(
            select(func.count(LeaveRequest.id)).where(LeaveRequest.status == "Pending")
        ).scalar() or 0
    except Exception:
        result["pending_approvals"] = 0

    # Attendance today
    try:
        if AttendanceRecord is not None:
            result["attendance_today"] = db.execute(
                select(func.count(AttendanceRecord.id)).where(
                    AttendanceRecord.date == today,
                    AttendanceRecord.status == "Present",
                )
            ).scalar() or 0
        else:
            result["attendance_today"] = 0
    except Exception:
        result["attendance_today"] = 0

    return result


@router.get("/headcount-trend")
def headcount_trend(
    months: int = Query(default=6, ge=1, le=24),
    db: Session = Depends(get_db),
):
    if Employee is None:
        return {"data": [], "message": "Employee model not available"}

    today = date.today()
    trend = []

    for i in range(months - 1, -1, -1):
        # Calculate the first day of each month going back
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        snapshot_date = date(year, month, 1)
        label = snapshot_date.strftime("%b %Y")

        try:
            # Employees who joined on or before this month's first day and are active
            count = db.execute(
                select(func.count(Employee.id)).where(
                    Employee.joining_date <= snapshot_date,
                    Employee.is_active == True,
                )
            ).scalar() or 0
        except Exception:
            count = 0

        trend.append({"month": label, "active_employees": count})

    return {"months_back": months, "data": trend}
