from sqlalchemy.orm import Session
from sqlalchemy import func
from utils.productivity.logger import get_logger
from datetime import datetime, timedelta, timezone
from datetime import date, timedelta

from model.models import AttendanceRecord as Attendance
from model.onboarding.employee import Employee
from model.Productivity.productivity import Productivity
from model.Productivity.task import ProductivityTask

logger = get_logger(__name__)


def _combine(day: date, h: int, m: int) -> datetime:
    return datetime(day.year, day.month, day.day, h, m, tzinfo=timezone.utc)


def _parse_check_time(day: date, time_str: str | None):
    """
    AttendanceRecord.check_in/check_out are free-text "HH:MM" strings (same
    convention used in routers/HR_Automation/attendance/routers/attendance_reports.py's
    _time_to_min helper) — not datetimes. This combines one with a date to
    get a real datetime for duration math, returning None if it can't be
    parsed instead of raising.
    """
    if not time_str:
        return None
    try:
        h, m = map(int, time_str.strip().split(":")[:2])
        return _combine(day, h, m)
    except Exception:
        return None


def _format_duration(delta: timedelta) -> str:
    total_seconds = max(int(delta.total_seconds()), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{hours}h {minutes}m"


def _latest_score(db: Session, employee_id: int) -> float:
    row = (
        db.query(Productivity)
        .filter(Productivity.employee_id == employee_id)
        .order_by(Productivity.date.desc())
        .first()
    )
    return float(row.score) if row and row.score is not None else 0.0


def get_time_tracking_overview(db: Session, user, period: str):
    logger.info(f"Getting time tracking overview for user_id={user.id}, period={period}")
    try:
        today = date.today()

        active = (
            db.query(Attendance)
            .filter(
                Attendance.employee_id == user.id,
                Attendance.date == today,
                Attendance.check_in.isnot(None),
                Attendance.check_out.is_(None),
            )
            .first()
        )

        current_session = None
        if active:
            check_in_dt = _parse_check_time(today, active.check_in)
            duration_str = "0h 0m"
            start_time_str = active.check_in or "--"
            if check_in_dt:
                duration_str = _format_duration(datetime.now(timezone.utc) - check_in_dt)
                start_time_str = check_in_dt.strftime("%I:%M %p")
            current_session = {
                "employee": f"{user.first_name} {user.last_name or ''}",
                "project": "N/A",
                "ProductivityTask": "Working",
                "startTime": start_time_str,
                "duration": duration_str,
                "status": "active",
            }
            logger.debug(f"Found active session: {current_session}")

        week_start = today - timedelta(days=today.weekday())

        # Productivity table has no "hours logged" field — total hours are
        # derived from Attendance check_in/check_out pairs for the week
        # instead (the original query pulled from a Productivity.hours_logged
        # column that doesn't exist on the model).
        week_records = (
            db.query(Attendance)
            .filter(Attendance.date >= week_start, Attendance.date <= today)
            .all()
        )

        total_seconds = 0
        for rec in week_records:
            start_dt = _parse_check_time(rec.date, rec.check_in)
            end_dt = _parse_check_time(rec.date, rec.check_out)
            if start_dt and end_dt and end_dt > start_dt:
                total_seconds += (end_dt - start_dt).total_seconds()

        total_hours = round(total_seconds / 3600, 1)
        avg_daily = round(total_hours / 5, 1) if total_hours else 0

        # Productivity.average_score doesn't exist either — the column is
        # just "score".
        avg_productivity = (
            db.query(func.coalesce(func.avg(Productivity.score), 0))
            .filter(Productivity.date >= week_start)
            .scalar()
        )

        overtime = max(total_hours - 40, 0)

        overview = {
            "currentSession": current_session,
            "stats": {
                "totalHours": total_hours,
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
            try:
                date_obj = datetime.strptime(period, "%Y-%m-%d").date()
                q = q.filter(Attendance.date == date_obj)
            except ValueError:
                logger.warning(f"Invalid period '{period}', no date filter applied")
                pass

        entries = (
            q.order_by(Attendance.date.desc())
             .limit(50)
             .all()
        )

        logger.debug(f"Found {len(entries)} entries")

        result = []

        for a in entries:
            if not a.check_in:
                continue

            start_dt = _parse_check_time(a.date, a.check_in)
            end_dt = _parse_check_time(a.date, a.check_out) or datetime.now(timezone.utc)
            duration_str = "N/A"
            if start_dt:
                duration_str = _format_duration(end_dt - start_dt)

            result.append({
                "id": a.id,
                "employee": f"{a.employee.first_name} {a.employee.last_name or ''}",
                "project": "N/A",
                "ProductivityTask": "Working",
                "date": a.date.isoformat(),
                "startTime": a.check_in,
                "endTime": a.check_out or "In Progress",
                "duration": duration_str,
                "breaks": "0m",
                # Employee has no productivity_score field — pull the most
                # recent Productivity.score row for this employee instead.
                "productivity": int(_latest_score(db, a.employee_id)),
                "status": "active" if not a.check_out else "completed",
                # Employee has no profile_picture field yet.
                "avatar": None,
            })

        logger.info(f"Returning {len(result)} time entries")
        return result
    except Exception as e:
        logger.error(f"Error in get_time_entries period={period}: {str(e)}", exc_info=True)
        raise
