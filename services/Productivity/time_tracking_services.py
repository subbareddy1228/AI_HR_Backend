from sqlalchemy.orm import Session
from sqlalchemy import func
from utils.productivity.logger import get_logger
from datetime import datetime, timedelta, timezone
from datetime import date, timedelta

from model.Productivity.attendance import Attendance
from model.Productivity.employee import Employee
from model.Productivity.productivity import Productivity
from model.Productivity.task import Task

logger = get_logger(__name__)

# ---------------- OVERVIEW ----------------
def get_time_tracking_overview(db: Session, user, period: str):
    logger.info(f"Getting time tracking overview for user_id={user.id}, period={period}")
    try:
        today = date.today()

        # Active session (attendance without logout)
        active = (
            db.query(Attendance)
            .filter(
                Attendance.employee_id == user.id,
                Attendance.date == today,
                Attendance.login_time.isnot(None),
                Attendance.logout_time.is_(None),
            )
            .first()
        )

        current_session = None
        if active:
            duration = datetime.utcnow() - active.login_time
            current_session = {
                "employee": f"{user.first_name} {user.last_name or ''}",
                "project": "N/A",
                "task": "Working",
                "startTime": active.login_time.strftime("%I:%M %p"),
                "duration": str(duration).split(".")[0],
                "status": "active",
            }
            logger.debug(f"Found active session: {current_session}")

        # Stats (weekly)
        week_start = today - timedelta(days=today.weekday())

        total_hours = (
            db.query(func.coalesce(func.sum(Productivity.hours_logged), 0))
            .filter(Productivity.date >= week_start)
            .scalar()
        )

        avg_daily = round(total_hours / 5, 1) if total_hours else 0

        avg_productivity = (
            db.query(func.coalesce(func.avg(Productivity.average_score), 0))
            .filter(Productivity.date >= week_start)
            .scalar()
        )

        overtime = max(total_hours - 40, 0)

        overview = {
            "currentSession": current_session,
            "stats": {
                "totalHours": round(total_hours, 1),
                "averageDaily": avg_daily,
                "productivity": int(avg_productivity),
                "overtime": round(overtime, 1),
            },
        }
        logger.info(f"Time tracking overview generated for user_id={user.id}")
        return overview
    except Exception as e:
        logger.error(f"Error in get_time_tracking_overview for user_id={user.id}: {str(e)}", exc_info=True)
        raise



def get_time_entries(db: Session, period: str, project_id: int | None):
    logger.info(f"Getting time entries for period={period}, project_id={project_id}")
    try:
        q = db.query(Attendance).join(Employee)

        today = datetime.now(timezone.utc).date()

        if period == "today":
            q = q.filter(Attendance.date == today)

        elif period == "week":
            q = q.filter(Attendance.date >= today - timedelta(days=6))

        elif period == "month":
            q = q.filter(Attendance.date >= today - timedelta(days=29))

        else:
            # allow exact date: YYYY-MM-DD
            try:
                date_obj = datetime.strptime(period, "%Y-%m-%d").date()
                q = q.filter(Attendance.date == date_obj)
            except ValueError:
                logger.warning(f"Invalid period '{period}', no date filter applied")
                pass  # invalid period → no filter or raise 400

        entries = (
            q.order_by(Attendance.date.desc())
             .limit(50)
             .all()
        )

        logger.debug(f"Found {len(entries)} entries")

        result = []

        for a in entries:
            if not a.login_time:
                continue

            #  TIMEZONE-SAFE
            end_dt = a.logout_time or datetime.now(timezone.utc)
            duration = end_dt - a.login_time

            result.append({
                "id": a.id,
                "employee": f"{a.employee.first_name} {a.employee.last_name or ''}",
                "project": "N/A",
                "task": "Working",
                "date": a.date.isoformat(),
                "startTime": a.login_time.strftime("%I:%M %p"),
                "endTime": (
                    a.logout_time.strftime("%I:%M %p")
                    if a.logout_time
                    else "In Progress"
                ),
                "duration": f"{duration.seconds // 3600}h {(duration.seconds % 3600) // 60}m",
                "breaks": "0m",
                "productivity": int(a.employee.productivity_score),
                "status": "active" if not a.logout_time else "completed",
                "avatar": a.employee.profile_picture,
            })

        logger.info(f"Returning {len(result)} time entries")
        return result
    except Exception as e:
        logger.error(f"Error in get_time_entries period={period}: {str(e)}", exc_info=True)
        raise

