from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date

from utils.productivity.logger import get_logger
logger = get_logger(__name__)

from model.onboarding.employee import Employee
# from model.models import AttendanceRecord as Attendance
from model.HR_Automation.attendance_capture import AttendanceRecord as Attendance
from model.Employee_Management.org_hierarchy import Department
from model.Productivity.productivity import Productivity


def get_dashboard_data(db: Session):
    logger.info("Generating dashboard data")
    today = date.today()

    

    

    total_employees = (
        db.query(func.count(Employee.id))
        .filter(Employee.is_active == True)
        .scalar()
    )
    logger.info(f"Dashboard metrics: total_employees={total_employees}")

    active_now = (
        db.query(func.count(Attendance.id))
        .filter(
            Attendance.date == today,
            Attendance.login_time.isnot(None),
            Attendance.logout_time.is_(None),
        )
        .scalar()
    )

    avg_productivity = (
        db.query(func.coalesce(func.avg(Productivity.average_score), 0))
        .filter(Productivity.date == today)
        .scalar()
    )

    total_hours_today = (
        db.query(func.coalesce(func.sum(Productivity.hours_logged), 0))
        .filter(Productivity.date == today)
        .scalar()
    )

    
 
    

    dept_counts = (
        db.query(
            Department.name,
            func.count(Employee.id)
        )
        .join(Employee, Employee.department_id == Department.id)
        .group_by(Department.name)
        .all()
    )

    total_dept_employees = sum(count for _, count in dept_counts) or 1

    department_data = [
        {
            "name": name,
            "value": round((count / total_dept_employees) * 100),
        }
        for name, count in dept_counts
    ]

    

    

    productivity_week = (
        db.query(
            Productivity.date,
            func.avg(Productivity.average_score)
        )
        .group_by(Productivity.date)
        .order_by(Productivity.date.desc())
        .limit(7)
        .all()
    )

    productivity_data = [
        {
            "day": p_date.strftime("%a"),
            "productivity": int(score or 0),
        }
        for p_date, score in reversed(productivity_week)
    ]

    

    

    recent_attendance = (
        db.query(Attendance)
        .join(Employee)
        .order_by(
            func.coalesce(Attendance.updated_at, Attendance.created_at).desc()
        )
        .limit(5)
        .all()
    )

    recent_activity = []

    for a in recent_attendance:
        ts = a.logout_time or a.login_time or a.updated_at or a.created_at

        recent_activity.append({
            "user": f"{a.employee.first_name} {a.employee.last_name or ''}",
            "action": "Logged In" if a.login_time and not a.logout_time else "Logged Out",
            "time": ts.strftime("%H:%M"),
            "status": "online" if a.logout_time is None else "offline",
        })

    
 
    

    top_performers = (
        db.query(Employee)
        .order_by(Employee.productivity_score.desc())
        .limit(5)
        .all()
    )

    top_performer_data = [
        {
            "name": f"{e.first_name} {e.last_name or ''}",
            "score": int(e.productivity_score),
            "department": e.department.name if e.department else "N/A",
            "avatar": e.profile_picture,
        }
        for e in top_performers
    ]

    
 
    

    return {
        "metrics": [
            {
                "title": "Total Employees",
                "value": str(total_employees),
                "change": "",
                "changeType": "increase",
                "color": "primary",
            },
            {
                "title": "Active Now",
                "value": str(active_now),
                "change": "",
                "changeType": "increase",
                "color": "success",
            },
            {
                "title": "Avg Productivity",
                "value": f"{int(avg_productivity)}%",
                "change": "",
                "changeType": "increase",
                "color": "secondary",
            },
            {
                "title": "Hours Logged Today",
                "value": f"{round(total_hours_today, 1)}h",
                "change": "",
                "changeType": "increase",
                "color": "accent",
            },
        ],
        "departmentData": department_data,
        "productivityData": productivity_data,
        "recentActivity": recent_activity,
        "topPerformers": top_performer_data,
    }
