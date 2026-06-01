from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
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
    from model.HR_Operations.promotion import EmployeePromotion
except ImportError:
    EmployeePromotion = None

try:
    from model.models import AttendanceRecord
except ImportError:
    AttendanceRecord = None

router = APIRouter(prefix="/ai-insights", tags=["Reports"])


@router.get("/attrition-risk")
def attrition_risk(db: Session = Depends(get_db)):
    """
    Rule-based attrition risk: flag employees with tenure > 2 years and no promotion on record.
    """
    if Employee is None:
        return {"data": [], "count": 0, "message": "Employee model not available"}

    today = date.today()
    two_years_ago = today.replace(year=today.year - 2)

    try:
        long_tenure = db.execute(
            select(Employee).where(
                Employee.is_active == True,
                Employee.joining_date <= two_years_ago,
            )
        ).scalars().all()
    except Exception:
        return {"data": [], "count": 0, "message": "Error querying employees"}

    # Collect promoted employee IDs if available
    promoted_ids: set = set()
    if EmployeePromotion is not None:
        try:
            promotions = db.execute(select(EmployeePromotion.employee_id)).scalars().all()
            promoted_ids = set(promotions)
        except Exception:
            promoted_ids = set()

    at_risk = []
    for emp in long_tenure:
        if emp.id not in promoted_ids:
            tenure_years = (today - emp.joining_date).days // 365 if emp.joining_date else 0
            at_risk.append(
                {
                    "employee_id": emp.id,
                    "employee_code": emp.employee_code,
                    "name": f"{emp.first_name} {emp.last_name}",
                    "department": emp.department,
                    "designation": emp.designation,
                    "tenure_years": tenure_years,
                    "reason": "Tenure > 2 years with no promotion on record",
                    "risk_level": "High" if tenure_years >= 4 else "Medium",
                }
            )

    return {"data": at_risk, "count": len(at_risk)}


@router.get("/attendance-anomalies")
def attendance_anomalies(db: Session = Depends(get_db)):
    """
    Flag employees with more than 5 absences in the last 30 days.
    """
    if AttendanceRecord is None:
        return {"data": [], "count": 0, "message": "AttendanceRecord model not available"}

    since = date.today() - timedelta(days=30)

    try:
        rows = db.execute(
            select(
                AttendanceRecord.employee_id,
                func.count(AttendanceRecord.id).label("absence_count"),
            )
            .where(
                AttendanceRecord.status == "Absent",
                AttendanceRecord.date >= since,
            )
            .group_by(AttendanceRecord.employee_id)
            .having(func.count(AttendanceRecord.id) > 5)
            .order_by(func.count(AttendanceRecord.id).desc())
        ).all()
    except Exception:
        return {"data": [], "count": 0, "message": "Error querying attendance records"}

    data = []
    for row in rows:
        absence_count = row.absence_count
        risk_level = "High" if absence_count > 10 else "Medium"
        data.append(
            {
                "employee_id": row.employee_id,
                "absence_count": absence_count,
                "risk_level": risk_level,
                "period": "Last 30 days",
            }
        )

    return {"data": data, "count": len(data), "period_start": str(since), "period_end": str(date.today())}


@router.get("/department-health")
def department_health(db: Session = Depends(get_db)):
    """
    Per-department summary combining headcount, avg attendance, and risk indicators.
    """
    if Employee is None:
        return {"data": [], "message": "Employee model not available"}

    # Headcount per department
    dept_headcount: dict = {}
    try:
        rows = db.execute(
            select(Employee.department, func.count(Employee.id).label("count"))
            .where(Employee.is_active == True)
            .group_by(Employee.department)
        ).all()
        for row in rows:
            dept_headcount[row.department or "Unknown"] = row.count
    except Exception:
        pass

    # Avg present days per department (last 30 days)
    dept_attendance: dict = {}
    if AttendanceRecord is not None:
        since = date.today() - timedelta(days=30)
        try:
            # We'll get present count per dept by joining with employees
            att_rows = db.execute(
                select(
                    Employee.department,
                    func.count(AttendanceRecord.id).label("present_count"),
                )
                .join(Employee, Employee.id == AttendanceRecord.employee_id)
                .where(
                    AttendanceRecord.status == "Present",
                    AttendanceRecord.date >= since,
                )
                .group_by(Employee.department)
            ).all()
            for row in att_rows:
                dept_attendance[row.department or "Unknown"] = row.present_count
        except Exception:
            pass

    # Attrition this year per department
    dept_exits: dict = {}
    if ExitManagement is not None:
        try:
            exit_rows = db.execute(
                select(
                    Employee.department,
                    func.count(ExitManagement.id).label("exit_count"),
                )
                .join(Employee, Employee.id == ExitManagement.employee_id)
                .where(
                    func.extract("year", ExitManagement.last_working_date) == date.today().year
                )
                .group_by(Employee.department)
            ).all()
            for row in exit_rows:
                dept_exits[row.department or "Unknown"] = row.exit_count
        except Exception:
            pass

    # Combine into health summary
    all_depts = set(dept_headcount) | set(dept_attendance) | set(dept_exits)
    data = []
    for dept in sorted(all_depts):
        headcount = dept_headcount.get(dept, 0)
        present_count = dept_attendance.get(dept, 0)
        exits = dept_exits.get(dept, 0)
        avg_attendance_pct = round((present_count / (headcount * 30)) * 100, 1) if headcount else 0

        # Simple health score (0-100): higher attendance + lower attrition = healthier
        attrition_penalty = min(exits * 5, 40)  # cap penalty at 40
        health_score = max(0, min(100, avg_attendance_pct - attrition_penalty))

        data.append(
            {
                "department": dept,
                "headcount": headcount,
                "attendance_rate_30d": avg_attendance_pct,
                "exits_this_year": exits,
                "health_score": round(health_score, 1),
                "health_status": (
                    "Healthy" if health_score >= 70 else
                    "At Risk" if health_score >= 40 else
                    "Critical"
                ),
            }
        )

    return {"data": data, "generated_at": str(date.today())}
