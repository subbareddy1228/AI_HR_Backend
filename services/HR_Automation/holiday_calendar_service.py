"""
services/holiday_calendar_service.py
Business logic for Holiday Calendar module — all 5 tabs.
"""

import calendar as cal_lib
import csv, io, logging
from datetime import date, datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, or_, distinct

from model.HR_Automation.holiday_calendar import (
    Holiday, OptionalHolidayApplication, HolidayCalendar,
    HolidaySwapRequest, HolidayCarryForward,
    ApplicationStatusEnum, SwapStatusEnum, CarryForwardStatusEnum,
)

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December",
]

# Default data from component's initialState
DEFAULT_CALENDAR = {
    "name":           "India - National Calendar",
    "location":       "All",
    "employee_groups":["all"],
    "is_default":     True,
    "is_active":      True,
}

DEFAULT_HOLIDAYS = [
    {"name": "Republic Day", "date": date(2024, 1, 26), "category": "National Holiday",
     "holiday_type": "gazetted", "location": "India", "optional": False},
    {"name": "Holi",         "date": date(2024, 3, 25), "category": "Festival",
     "holiday_type": "gazetted", "location": "India", "optional": False},
    {"name": "Independence Day","date": date(2024, 8, 15),"category":"National Holiday",
     "holiday_type": "gazetted", "location": "India", "optional": False},
]


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _resolve_employee(db: Session, employee_id: str) -> str:
    try:
        from model.onboarding.employee import Employee
        emp = db.query(Employee).filter_by(employee_id=employee_id).first()
        if emp:
            return emp.name
    except ImportError:
        pass
    return employee_id


def _build_holiday_out(h: Holiday) -> dict:
    return {
        "id": h.id, "name": h.name, "date": h.date,
        "location": h.location, "category": h.category,
        "holidayType": h.holiday_type,
        "optional": h.optional,
        "advanceBookingDays": h.advance_booking_days,
        "allowCarryForward": h.allow_carry_forward,
        "carryForwardLimit": h.carry_forward_limit,
        "applicableCalendars": h.applicable_calendars or ["all"],
        "applicableGroups": h.applicable_groups or ["all"],
        "typeDisplay": "Optional" if h.optional else "Mandatory",
        "holidayTypeDisplay": h.holiday_type.value if h.holiday_type else "gazetted",
        "created_at": h.created_at,
    }


def _build_app_out(db: Session, app: OptionalHolidayApplication) -> dict:
    return {
        "id": app.id, "holiday_id": app.holiday_id,
        "employee_id": app.employee_id,
        "employeeName": app.employee_name or _resolve_employee(db, app.employee_id),
        "holidayName": app.holiday_name,
        "holidayDate": app.holiday_date,
        "appliedDate": app.applied_date,
        "reason": app.reason, "status": app.status,
        "approvalWorkflow": app.approval_workflow or [],
        "approvedAt": app.approved_at, "approvedBy": app.approved_by,
        "rejectedAt": app.rejected_at, "rejectedBy": app.rejected_by,
        "created_at": app.created_at,
    }


def _build_calendar_out(cal: HolidayCalendar) -> dict:
    groups = cal.employee_groups or ["all"]
    return {
        "id": cal.id, "name": cal.name, "location": cal.location,
        "employeeGroups": groups, "isDefault": cal.is_default,
        "isActive": cal.is_active,
        "groupsDisplay": "All Groups" if "all" in groups else ", ".join(groups),
        "statusDisplay": "Active" if cal.is_active else "Inactive",
        "created_at": cal.created_at,
    }


def _build_swap_out(db: Session, swap: HolidaySwapRequest) -> dict:
    return {
        "id": swap.id, "employee_id": swap.employee_id,
        "employeeName": _resolve_employee(db, swap.employee_id),
        "holidayDate": swap.holiday_date, "workDate": swap.work_date,
        "reason": swap.reason, "status": swap.status,
        "approvalWorkflow": swap.approval_workflow or [],
        "approvedAt": swap.approved_at, "approvedBy": swap.approved_by,
        "rejectedAt": swap.rejected_at, "rejectedBy": swap.rejected_by,
        "submittedAt": swap.submitted_at,
    }


def _build_cf_out(db: Session, cf: HolidayCarryForward) -> dict:
    return {
        "id": cf.id, "employee_id": cf.employee_id,
        "employeeName": _resolve_employee(db, cf.employee_id),
        "fromYear": cf.from_year, "toYear": cf.to_year,
        "holidays": cf.holidays or [],
        "holidayCount": cf.holiday_count,
        "status": cf.status,
        "processedAt": cf.processed_at,
        "processedByName": cf.processed_by_name,
    }


# ═══════════════════════════════════════════════════════════
# STARTUP SEED
# ═══════════════════════════════════════════════════════════

def seed_holiday_defaults(db: Session):
    """Called once at startup — seeds default calendar + 3 national holidays."""
    if db.query(HolidayCalendar).count() == 0:
        db.add(HolidayCalendar(**DEFAULT_CALENDAR))
        db.commit()
        logger.info("Seeded default holiday calendar.")

    if db.query(Holiday).count() == 0:
        for data in DEFAULT_HOLIDAYS:
            db.add(Holiday(**data))
        db.commit()
        logger.info("Seeded %d default holidays.", len(DEFAULT_HOLIDAYS))


# ═══════════════════════════════════════════════════════════
# TAB 1 — HOLIDAY MASTER SERVICE
# ═══════════════════════════════════════════════════════════

class HolidayMasterService:

    @staticmethod
    def list(
        db: Session,
        search: Optional[str]        = None,
        category: Optional[str]      = None,
        type_filter: Optional[str]   = None,   # "mandatory" | "optional"
        year: Optional[int]          = None,
    ) -> List[dict]:
        q = db.query(Holiday)
        if search:
            term = f"%{search.lower()}%"
            q = q.filter(
                or_(func.lower(Holiday.name).like(term),
                    func.lower(Holiday.category).like(term))
            )
        if category and category != "All":
            q = q.filter_by(category=category)
        if type_filter == "mandatory":
            q = q.filter_by(optional=False)
        elif type_filter == "optional":
            q = q.filter_by(optional=True)
        if year:
            q = q.filter(func.extract("year", Holiday.date) == year)
        return [_build_holiday_out(h) for h in q.order_by(Holiday.date).all()]

    @staticmethod
    def get(db: Session, holiday_id: int) -> Holiday:
        h = db.query(Holiday).filter_by(id=holiday_id).first()
        if not h:
            raise ValueError(f"Holiday {holiday_id} not found.")
        return h

    @staticmethod
    def create(db: Session, payload, created_by: Optional[int] = None) -> dict:
        h = Holiday(
            name=payload.name, date=payload.date, location=payload.location,
            category=payload.category, holiday_type=payload.holidayType,
            optional=payload.optional,
            advance_booking_days=payload.advanceBookingDays,
            allow_carry_forward=payload.allowCarryForward,
            carry_forward_limit=payload.carryForwardLimit,
            applicable_calendars=payload.applicableCalendars,
            applicable_groups=payload.applicableGroups,
            created_by=created_by,
        )
        db.add(h)
        db.commit()
        db.refresh(h)
        logger.info("Holiday created: %s %s", h.name, h.date)
        return _build_holiday_out(h)

    @staticmethod
    def update(db: Session, holiday_id: int, payload, updated_by: Optional[int] = None) -> dict:
        h = HolidayMasterService.get(db, holiday_id)
        field_map = {
            "name": "name", "date": "date", "location": "location",
            "category": "category", "holidayType": "holiday_type",
            "optional": "optional", "advanceBookingDays": "advance_booking_days",
            "allowCarryForward": "allow_carry_forward",
            "carryForwardLimit": "carry_forward_limit",
            "applicableCalendars": "applicable_calendars",
            "applicableGroups": "applicable_groups",
        }
        for py_name, db_name in field_map.items():
            val = getattr(payload, py_name, None)
            if val is not None:
                setattr(h, db_name, val)
        db.commit()
        db.refresh(h)
        return _build_holiday_out(h)

    @staticmethod
    def delete(db: Session, holiday_id: int) -> None:
        h = HolidayMasterService.get(db, holiday_id)
        db.delete(h)
        db.commit()

    @staticmethod
    def get_stats(db: Session) -> dict:
        total      = db.query(Holiday).count()
        optional   = db.query(Holiday).filter_by(optional=True).count()
        total_apps = db.query(OptionalHolidayApplication).count()
        pending    = db.query(OptionalHolidayApplication).filter_by(
            status=ApplicationStatusEnum.Pending).count()
        approved   = db.query(OptionalHolidayApplication).filter_by(
            status=ApplicationStatusEnum.Approved).count()
        rejected   = db.query(OptionalHolidayApplication).filter_by(
            status=ApplicationStatusEnum.Rejected).count()
        return {
            "totalHolidays": total, "optionalHolidays": optional,
            "totalApplications": total_apps, "pendingApplications": pending,
            "approvedApplications": approved, "rejectedApplications": rejected,
        }

    @staticmethod
    def export_csv(db: Session, search=None, category=None, type_filter=None) -> bytes:
        items = HolidayMasterService.list(db, search, category, type_filter)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Holiday Name","Date","Category","Type","Location"])
        for h in items:
            writer.writerow([
                h["name"], h["date"], h["category"],
                h["typeDisplay"], h["location"],
            ])
        return output.getvalue().encode("utf-8")


# ═══════════════════════════════════════════════════════════
# TAB 2 — OPTIONAL APPLICATIONS SERVICE
# ═══════════════════════════════════════════════════════════

class OptionalApplicationService:

    @staticmethod
    def list(
        db: Session,
        search: Optional[str]   = None,
        status: Optional[ApplicationStatusEnum] = None,
        employee_id: Optional[str] = None,
    ) -> List[dict]:
        q = db.query(OptionalHolidayApplication)
        if employee_id: q = q.filter_by(employee_id=employee_id)
        if status:      q = q.filter_by(status=status)
        if search:
            term = f"%{search.lower()}%"
            q = q.filter(
                or_(func.lower(OptionalHolidayApplication.holiday_name).like(term),
                    func.lower(OptionalHolidayApplication.employee_name).like(term))
            )
        return [_build_app_out(db, a) for a in
                q.order_by(OptionalHolidayApplication.created_at.desc()).all()]

    @staticmethod
    def apply(db: Session, payload, applied_by: Optional[int] = None) -> dict:
        holiday = db.query(Holiday).filter_by(id=payload.holidayId).first()
        if not holiday:
            raise ValueError(f"Holiday {payload.holidayId} not found.")
        if not holiday.optional:
            raise ValueError(f"'{holiday.name}' is not an optional holiday.")

        # Check advance booking
        today     = date.today()
        days_diff = (holiday.date - today).days
        if holiday.advance_booking_days > 0 and days_diff < holiday.advance_booking_days:
            raise ValueError(
                f"This holiday requires {holiday.advance_booking_days} days advance booking. "
                f"Only {days_diff} days remaining."
            )

        emp_name = _resolve_employee(db, payload.employeeId)

        app = OptionalHolidayApplication(
            holiday_id=payload.holidayId,
            employee_id=payload.employeeId,
            employee_name=emp_name,
            holiday_name=holiday.name,
            holiday_date=holiday.date,
            applied_date=today,
            reason=payload.reason,
            status=ApplicationStatusEnum.Pending,
            approval_workflow=[
                {"level": 1, "approver": "Manager", "status": "pending", "required": True},
                {"level": 2, "approver": "HR",       "status": "pending", "required": True},
            ],
        )
        db.add(app)
        db.commit()
        db.refresh(app)
        logger.info("Optional holiday applied: %s → %s", payload.employeeId, holiday.name)
        return _build_app_out(db, app)

    @staticmethod
    def update_status(
        db: Session, app_id: int,
        new_status: ApplicationStatusEnum,
        decided_by: str = "Manager",
    ) -> dict:
        app = db.query(OptionalHolidayApplication).filter_by(id=app_id).first()
        if not app:
            raise ValueError(f"Application {app_id} not found.")

        now = datetime.now(timezone.utc)
        app.status = new_status
        if new_status == ApplicationStatusEnum.Approved:
            app.approved_at = now
            app.approved_by = decided_by
        elif new_status == ApplicationStatusEnum.Rejected:
            app.rejected_at = now
            app.rejected_by = decided_by

        db.commit()
        db.refresh(app)
        return _build_app_out(db, app)

    @staticmethod
    def delete(db: Session, app_id: int) -> None:
        app = db.query(OptionalHolidayApplication).filter_by(id=app_id).first()
        if not app:
            raise ValueError(f"Application {app_id} not found.")
        db.delete(app)
        db.commit()

    @staticmethod
    def export_csv(db: Session, status=None) -> bytes:
        items = OptionalApplicationService.list(db, status=status)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Holiday","Date","Applied On","Status","Reason","Employee"])
        for a in items:
            writer.writerow([
                a["holidayName"], a["holidayDate"],
                a["appliedDate"], a["status"],
                a["reason"], a["employeeName"],
            ])
        return output.getvalue().encode("utf-8")


# ═══════════════════════════════════════════════════════════
# TAB 3 — CALENDARS SERVICE
# ═══════════════════════════════════════════════════════════

class HolidayCalendarService:

    @staticmethod
    def list(db: Session) -> List[dict]:
        cals = db.query(HolidayCalendar).order_by(
            HolidayCalendar.is_default.desc(), HolidayCalendar.name
        ).all()
        return [_build_calendar_out(c) for c in cals]

    @staticmethod
    def get(db: Session, calendar_id: int) -> HolidayCalendar:
        c = db.query(HolidayCalendar).filter_by(id=calendar_id).first()
        if not c:
            raise ValueError(f"Calendar {calendar_id} not found.")
        return c

    @staticmethod
    def create(db: Session, payload, created_by: Optional[int] = None) -> dict:
        # If setting as default, unset others
        if payload.isDefault:
            db.query(HolidayCalendar).update({"is_default": False})

        cal = HolidayCalendar(
            name=payload.name, location=payload.location,
            employee_groups=payload.employeeGroups,
            is_default=payload.isDefault, is_active=True,
            created_by=created_by,
        )
        db.add(cal)
        db.commit()
        db.refresh(cal)
        return _build_calendar_out(cal)

    @staticmethod
    def update(db: Session, calendar_id: int, payload, updated_by: Optional[int] = None) -> dict:
        cal = HolidayCalendarService.get(db, calendar_id)

        if getattr(payload, "isDefault", None) is True:
            db.query(HolidayCalendar).filter(
                HolidayCalendar.id != calendar_id
            ).update({"is_default": False})

        if payload.name             is not None: cal.name           = payload.name
        if payload.location         is not None: cal.location       = payload.location
        if payload.employeeGroups   is not None: cal.employee_groups = payload.employeeGroups
        if payload.isDefault        is not None: cal.is_default     = payload.isDefault
        if payload.isActive         is not None: cal.is_active      = payload.isActive

        db.commit()
        db.refresh(cal)
        return _build_calendar_out(cal)

    @staticmethod
    def delete(db: Session, calendar_id: int) -> None:
        cal = HolidayCalendarService.get(db, calendar_id)
        if cal.is_default:
            raise ValueError("Cannot delete the default calendar.")
        db.delete(cal)
        db.commit()


# ═══════════════════════════════════════════════════════════
# TAB 4 — HOLIDAY SWAP SERVICE
# ═══════════════════════════════════════════════════════════

class HolidaySwapService:

    @staticmethod
    def list(db: Session, employee_id: Optional[str] = None,
             status: Optional[SwapStatusEnum] = None) -> List[dict]:
        q = db.query(HolidaySwapRequest)
        if employee_id: q = q.filter_by(employee_id=employee_id)
        if status:      q = q.filter_by(status=status)
        return [_build_swap_out(db, s) for s in
                q.order_by(HolidaySwapRequest.submitted_at.desc()).all()]

    @staticmethod
    def create(db: Session, payload, created_by: Optional[int] = None) -> dict:
        swap = HolidaySwapRequest(
            employee_id=payload.employeeId,
            holiday_date=payload.holidayDate,
            work_date=payload.workDate,
            reason=payload.reason,
            status=SwapStatusEnum.pending,
            approval_workflow=[
                {"level": 1, "approver": "Manager", "status": "pending", "required": True},
                {"level": 2, "approver": "HR",       "status": "pending", "required": True},
            ],
        )
        db.add(swap)
        db.commit()
        db.refresh(swap)
        return _build_swap_out(db, swap)

    @staticmethod
    def decide(
        db: Session, swap_id: int, approved: bool,
        decided_by: str = "Manager",
    ) -> dict:
        swap = db.query(HolidaySwapRequest).filter_by(id=swap_id).first()
        if not swap:
            raise ValueError(f"Swap request {swap_id} not found.")
        if swap.status != SwapStatusEnum.pending:
            raise ValueError("Only pending swap requests can be decided.")

        now = datetime.now(timezone.utc)
        if approved:
            swap.status      = SwapStatusEnum.approved
            swap.approved_at = now
            swap.approved_by = decided_by
        else:
            swap.status      = SwapStatusEnum.rejected
            swap.rejected_at = now
            swap.rejected_by = decided_by

        db.commit()
        db.refresh(swap)
        return _build_swap_out(db, swap)


# ═══════════════════════════════════════════════════════════
# TAB 5 — CARRY FORWARD SERVICE
# ═══════════════════════════════════════════════════════════

class CarryForwardService:

    @staticmethod
    def list(db: Session, employee_id: Optional[str] = None) -> List[dict]:
        q = db.query(HolidayCarryForward)
        if employee_id:
            q = q.filter_by(employee_id=employee_id)
        return [_build_cf_out(db, cf) for cf in
                q.order_by(HolidayCarryForward.processed_at.desc()).all()]

    @staticmethod
    def available_holidays(db: Session) -> List[dict]:
        """Returns optional holidays with allowCarryForward=True for the modal checkbox list."""
        holidays = db.query(Holiday).filter_by(
            optional=True, allow_carry_forward=True
        ).order_by(Holiday.date).all()
        return [_build_holiday_out(h) for h in holidays]

    @staticmethod
    def process(
        db: Session, payload,
        processed_by: Optional[int] = None,
        processed_by_name: str = "HR Admin",
    ) -> dict:
        # Validate holiday IDs exist and are carry-forwardable
        valid_holidays = db.query(Holiday).filter(
            Holiday.id.in_(payload.holidays),
            Holiday.optional == True,
            Holiday.allow_carry_forward == True,
        ).all()

        if len(valid_holidays) != len(payload.holidays):
            raise ValueError(
                "Some selected holidays are not optional or don't allow carry forward."
            )

        cf = HolidayCarryForward(
            employee_id=payload.employeeId,
            from_year=payload.fromYear,
            to_year=payload.toYear,
            holidays=payload.holidays,
            holiday_count=len(payload.holidays),
            status=CarryForwardStatusEnum.processed,
            processed_by=processed_by,
            processed_by_name=processed_by_name,
        )
        db.add(cf)
        db.commit()
        db.refresh(cf)
        logger.info(
            "Carry forward: %s %d→%d (%d holidays)",
            payload.employeeId, payload.fromYear, payload.toYear, len(payload.holidays)
        )
        return _build_cf_out(db, cf)


# ═══════════════════════════════════════════════════════════
# CALENDAR GRID SERVICE
# ═══════════════════════════════════════════════════════════

class CalendarGridService:

    @staticmethod
    def get_month(db: Session, year: int, month: int) -> dict:
        """
        Builds the 7-column (Sun→Sat) calendar grid.
        Marks holiday dates in red (isHoliday=True).
        Highlights today (isToday=True).
        """
        _, days_in_month = cal_lib.monthrange(year, month)
        today = date.today()

        # Holiday map for quick lookup
        holidays = db.query(Holiday).filter(
            func.extract("year",  Holiday.date) == year,
            func.extract("month", Holiday.date) == month,
        ).all()
        holiday_map = {h.date.day: _build_holiday_out(h) for h in holidays}

        # First weekday (Sunday-based: Sun=0 … Sat=6)
        first_weekday = date(year, month, 1).weekday()
        first_col     = (first_weekday + 1) % 7  # convert Mon-based to Sun-based

        all_cells = []
        # Leading padding
        for _ in range(first_col):
            all_cells.append(None)
        # Actual days
        for d in range(1, days_in_month + 1):
            all_cells.append(d)
        # Trailing padding to complete last week
        remainder = len(all_cells) % 7
        if remainder:
            all_cells += [None] * (7 - remainder)

        # Build 6 weeks × 7 days
        weeks = []
        for w_start in range(0, len(all_cells), 7):
            week = []
            for cell in all_cells[w_start: w_start + 7]:
                if cell is None:
                    week.append({
                        "day": None, "date": None, "isToday": False,
                        "holiday": None, "isHoliday": False,
                    })
                else:
                    cell_date = date(year, month, cell)
                    week.append({
                        "day":       cell,
                        "date":      cell_date,
                        "isToday":   cell_date == today,
                        "holiday":   holiday_map.get(cell),
                        "isHoliday": cell in holiday_map,
                    })
            weeks.append(week)

        return {
            "year":      year,
            "month":     month,
            "monthName": f"{MONTH_NAMES[month - 1]} {year}",
            "weeks":     weeks,
        }
