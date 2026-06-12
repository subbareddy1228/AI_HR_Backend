"""
core/startup.py

Startup event registered in main.py.
Seeds default leave types ONCE on application boot —
NOT on every request (that was the wrong approach).

Usage in main.py:
    from core.startup import on_startup
    app = FastAPI(lifespan=lifespan)

    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        on_startup()
        yield

    # OR for older FastAPI versions:
    app.add_event_handler("startup", on_startup)
"""

import logging
from sqlalchemy.orm import Session
from core.database import SessionLocal

logger = logging.getLogger(__name__)


def on_startup():
    """
    Called once when the FastAPI process starts.
    Seeds any missing reference data into the database.
    Safe to call multiple times — guards exist in each seed function.
    """
    db: Session = SessionLocal()
    try:
        _seed_leave_types(db)
    except Exception as exc:
        logger.error("Startup seed failed: %s", exc)
    finally:
        db.close()


def _seed_leave_types(db: Session):
    """
    Insert the 6 default leave types if the table is empty.
    Called at startup — NOT inside list/get/create endpoints.
    """
    from model.HR_Automation.leave_management import LeaveType

    if db.query(LeaveType).count() > 0:
        logger.info("Leave types already seeded — skipping.")
        return

    DEFAULT_LEAVE_TYPES = [
        {
            "name": "Casual Leave",      "code": "CL",
            "description": "Casual leave for personal work",
            "is_paid": True, "accrual_type": "monthly",
            "accrual_amount": 1.5, "max_accrual": 12,
            "carry_forward_enabled": True, "carry_forward_max_days": 3,
            "carry_forward_expiry_months": 3,
            "encashment_enabled": True, "encashment_max_days": 5, "encashment_rate": 1.0,
            "allow_half_day": True, "allow_short_leave": True,
        },
        {
            "name": "Sick Leave",        "code": "SL",
            "description": "Medical leave with certificate requirement",
            "is_paid": True, "accrual_type": "monthly",
            "accrual_amount": 1.0, "max_accrual": 12,
            "carry_forward_enabled": True, "carry_forward_max_days": 5,
            "carry_forward_expiry_months": 6,
            "encashment_enabled": False,
            "allow_half_day": False, "probation_applicable": True, "allow_backdated": True,
        },
        {
            "name": "Earned Leave",      "code": "EL",
            "description": "Earned leave with encashment option",
            "is_paid": True, "accrual_type": "monthly",
            "accrual_amount": 1.25, "max_accrual": 15,
            "carry_forward_enabled": True, "carry_forward_max_days": 10,
            "carry_forward_expiry_months": 12,
            "encashment_enabled": True, "encashment_max_days": 10, "encashment_rate": 1.0,
            "allow_half_day": True,
        },
        {
            "name": "Maternity Leave",   "code": "ML",
            "description": "Maternity leave for female employees",
            "is_paid": True, "accrual_type": "on-joining",
            "accrual_amount": 26.0, "max_accrual": 26,
            "carry_forward_enabled": False, "encashment_enabled": False,
            "allow_half_day": False, "usage_limit": 1,
        },
        {
            "name": "Paternity Leave",   "code": "PL",
            "description": "Paternity leave for male employees",
            "is_paid": True, "accrual_type": "on-joining",
            "accrual_amount": 5.0, "max_accrual": 5,
            "carry_forward_enabled": False, "encashment_enabled": False,
            "allow_half_day": False, "usage_limit": 1,
        },
        {
            "name": "Bereavement Leave", "code": "BL",
            "description": "Leave for family bereavement",
            "is_paid": True, "accrual_type": "annual",
            "accrual_amount": 3.0, "max_accrual": 3,
            "carry_forward_enabled": False, "encashment_enabled": False,
            "allow_half_day": False,
            "probation_applicable": True, "allow_backdated": True,
        },
    ]

    for data in DEFAULT_LEAVE_TYPES:
        db.add(LeaveType(**data))

    db.commit()
    logger.info("Seeded %d default leave types.", len(DEFAULT_LEAVE_TYPES))


def seed_regularization():
    """
    Seeds 2 default auto-reject rules on startup.
    Matches the component's initialSettings.autoRejectRules:
      Missing Punch → 7 days
      Forgot Punch  → 5 days
    Safe to call multiple times — skips if rules already exist.
    """
    db: Session = SessionLocal()
    try:
        from services.HR_Automation.regularization import seed_auto_reject_rules
        seed_auto_reject_rules(db)
    except Exception as exc:
        logger.error("Regularization seed failed: %s", exc)
    finally:
        db.close()


def seed_holiday_calendar():
    db: Session = SessionLocal()
    try:
        from services.HR_Automation.holiday_calendar_service import seed_holiday_defaults
        seed_holiday_defaults(db)
    except Exception as exc:
        logger.error("Holiday calendar seed failed: %s", exc)
    finally:
        db.close()


def seed_attendance_reports():
    db: Session = SessionLocal()
    try:
        from services.HR_Automation.attendance_reports_service import seed_reports_defaults
        seed_reports_defaults(db)
    except Exception as exc:
        logger.error("Attendance reports seed failed: %s", exc)
    finally:
        db.close()