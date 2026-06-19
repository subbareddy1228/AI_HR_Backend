from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from typing import List, Optional

from model.HR_Automation.holiday import (
    OptionalHolidayApplication, OptionalAppStatus,
    HolidayCalendar, HolidayCalendarMapping, CalendarStatus,
    HolidaySwapRequest, SwapRequestStatus,
    HolidayCarryForward, CarryForwardStatus,
)
from model.HR_Automation.holiday import Holiday
from schema.HR_Automation.holiday import (
    OptionalHolidayApplicationCreate, OptionalHolidayApplicationUpdate,
    HolidayCalendarCreate, HolidayCalendarUpdate, CalendarHolidayLink,
    HolidaySwapRequestCreate, HolidaySwapRequestUpdate,
    HolidayCarryForwardCreate, ProcessCarryForwardRequest,
    HolidayCalendarTabSummary,
)

# Optional employee lookup (graceful fallback if model differs)
try:
    from model.Employee_Management.employee_master import EmployeeMaster
except ImportError:
    EmployeeMaster = None


def _employee_name(db: Session, employee_id: int) -> Optional[str]:
    if EmployeeMaster is None:
        return None
    emp = db.query(EmployeeMaster).filter(EmployeeMaster.id == employee_id).first()
    if not emp:
        return None
    return getattr(emp, "full_name", getattr(emp, "name", None))



def apply_optional_holiday(db: Session, payload: OptionalHolidayApplicationCreate) -> OptionalHolidayApplication:
    
    holiday = db.query(holiday).filter(holiday.id == payload.holiday_id).first()
    if not holiday:
        raise ValueError("Holiday not found")

    
    existing = db.query(OptionalHolidayApplication).filter(
        OptionalHolidayApplication.employee_id == payload.employee_id,
        OptionalHolidayApplication.holiday_id == payload.holiday_id,
    ).first()
    if existing:
        raise ValueError("You have already applied for this optional holiday")

    application = OptionalHolidayApplication(
        employee_id=payload.employee_id,
        holiday_id=payload.holiday_id,
        holiday_name=holiday.holiday_name,
        holiday_date=holiday.holiday_date,
        reason=payload.reason,
        status=OptionalAppStatus.PENDING,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def list_optional_applications(
    db: Session,
    employee_id: Optional[int] = None,
    status: Optional[OptionalAppStatus] = None,
) -> List[OptionalHolidayApplication]:
    q = db.query(OptionalHolidayApplication)
    if employee_id:
        q = q.filter(OptionalHolidayApplication.employee_id == employee_id)
    if status:
        q = q.filter(OptionalHolidayApplication.status == status)
    return q.order_by(OptionalHolidayApplication.applied_on.desc()).all()


def update_optional_application(
    db: Session, application_id: int, payload: OptionalHolidayApplicationUpdate
) -> OptionalHolidayApplication:
    
    app = db.query(OptionalHolidayApplication).filter(
        OptionalHolidayApplication.id == application_id
    ).first()
    if not app:
        raise ValueError("Application not found")

    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(app, field, val)

    if payload.status in (OptionalAppStatus.APPROVED, OptionalAppStatus.REJECTED):
        app.approved_on = datetime.utcnow()

    app.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(app)
    return app


def delete_optional_application(db: Session, application_id: int) -> bool:
    app = db.query(OptionalHolidayApplication).filter(
        OptionalHolidayApplication.id == application_id
    ).first()
    if not app:
        return False
    db.delete(app)
    db.commit()
    return True



def add_calendar(db: Session, payload: HolidayCalendarCreate) -> HolidayCalendar:
    
    if payload.is_default:
        # Only one calendar can be default at a time
        db.query(HolidayCalendar).filter(HolidayCalendar.is_default == True).update(
            {HolidayCalendar.is_default: False}
        )

    calendar = HolidayCalendar(
        calendar_name=payload.calendar_name,
        location=payload.location,
        employee_groups=payload.employee_groups,
        is_default=payload.is_default,
        description=payload.description,
        status=CalendarStatus.ACTIVE,
    )
    db.add(calendar)
    db.flush()

    if payload.holiday_ids:
        for hid in payload.holiday_ids:
            db.add(HolidayCalendarMapping(calendar_id=calendar.id, holiday_id=hid))

    db.commit()
    db.refresh(calendar)
    return calendar


def list_calendars(db: Session) -> List[dict]:
    
    calendars = db.query(HolidayCalendar).order_by(HolidayCalendar.created_at).all()
    results = []
    for cal in calendars:
        count = db.query(func.count(HolidayCalendarMapping.id)).filter(
            HolidayCalendarMapping.calendar_id == cal.id
        ).scalar()
        results.append({
            "id": cal.id,
            "calendar_name": cal.calendar_name,
            "location": cal.location,
            "employee_groups": cal.employee_groups,
            "status": cal.status,
            "is_default": cal.is_default,
            "description": cal.description,
            "holiday_count": count or 0,
            "created_at": cal.created_at,
        })
    return results


def update_calendar(db: Session, calendar_id: int, payload: HolidayCalendarUpdate) -> HolidayCalendar:
    
    calendar = db.query(HolidayCalendar).filter(HolidayCalendar.id == calendar_id).first()
    if not calendar:
        raise ValueError("Calendar not found")

    if payload.is_default:
        db.query(HolidayCalendar).filter(HolidayCalendar.id != calendar_id).update(
            {HolidayCalendar.is_default: False}
        )

    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(calendar, field, val)

    calendar.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(calendar)
    return calendar


def delete_calendar(db: Session, calendar_id: int) -> bool:
     
    calendar = db.query(HolidayCalendar).filter(HolidayCalendar.id == calendar_id).first()
    if not calendar:
        return False
    db.delete(calendar)
    db.commit()
    return True


def link_holiday_to_calendar(db: Session, payload: CalendarHolidayLink) -> HolidayCalendarMapping:
    existing = db.query(HolidayCalendarMapping).filter(
        HolidayCalendarMapping.calendar_id == payload.calendar_id,
        HolidayCalendarMapping.holiday_id == payload.holiday_id,
    ).first()
    if existing:
        return existing
    mapping = HolidayCalendarMapping(calendar_id=payload.calendar_id, holiday_id=payload.holiday_id)
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def unlink_holiday_from_calendar(db: Session, calendar_id: int, holiday_id: int) -> bool:
    mapping = db.query(HolidayCalendarMapping).filter(
        HolidayCalendarMapping.calendar_id == calendar_id,
        HolidayCalendarMapping.holiday_id == holiday_id,
    ).first()
    if not mapping:
        return False
    db.delete(mapping)
    db.commit()
    return True


def get_calendar_holidays(db: Session, calendar_id: int) -> List[Holiday]:
    return (
        db.query(Holiday)
        .join(HolidayCalendarMapping, HolidayCalendarMapping.holiday_id == Holiday.id)
        .filter(HolidayCalendarMapping.calendar_id == calendar_id)
        .order_by(Holiday.holiday_date)
        .all()
    )



def create_swap_request(db: Session, payload: HolidaySwapRequestCreate) -> HolidaySwapRequest:
    
    if payload.work_date == payload.holiday_date:
        raise ValueError("Work date must be different from the holiday date")

    swap = HolidaySwapRequest(
        employee_id=payload.employee_id,
        holiday_id=payload.holiday_id,
        holiday_date=payload.holiday_date,
        work_date=payload.work_date,
        reason=payload.reason,
        status=SwapRequestStatus.PENDING,
    )
    db.add(swap)
    db.commit()
    db.refresh(swap)
    return swap


def list_swap_requests(
    db: Session,
    employee_id: Optional[int] = None,
    status: Optional[SwapRequestStatus] = None,
) -> List[dict]:
    q = db.query(HolidaySwapRequest)
    if employee_id:
        q = q.filter(HolidaySwapRequest.employee_id == employee_id)
    if status:
        q = q.filter(HolidaySwapRequest.status == status)

    rows = q.order_by(HolidaySwapRequest.created_at.desc()).all()
    results = []
    for r in rows:
        results.append({
            "id": r.id,
            "employee_id": r.employee_id,
            "employee_name": _employee_name(db, r.employee_id),
            "holiday_id": r.holiday_id,
            "holiday_date": r.holiday_date,
            "work_date": r.work_date,
            "reason": r.reason,
            "status": r.status,
            "approved_by": r.approved_by,
            "approved_on": r.approved_on,
            "rejection_reason": r.rejection_reason,
            "created_at": r.created_at,
        })
    return results


def update_swap_request(
    db: Session, swap_id: int, payload: HolidaySwapRequestUpdate
) -> HolidaySwapRequest:
    
    swap = db.query(HolidaySwapRequest).filter(HolidaySwapRequest.id == swap_id).first()
    if not swap:
        raise ValueError("Swap request not found")

    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(swap, field, val)

    if payload.status in (SwapRequestStatus.APPROVED, SwapRequestStatus.REJECTED):
        swap.approved_on = datetime.utcnow()

    swap.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(swap)
    return swap


def cancel_swap_request(db: Session, swap_id: int) -> HolidaySwapRequest:
    swap = db.query(HolidaySwapRequest).filter(HolidaySwapRequest.id == swap_id).first()
    if not swap:
        raise ValueError("Swap request not found")
    swap.status = SwapRequestStatus.CANCELLED
    swap.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(swap)
    return swap



def process_carry_forward(db: Session, payload: ProcessCarryForwardRequest) -> List[HolidayCarryForward]:
    
    employee_ids = payload.employee_ids
    if not employee_ids:
        if EmployeeMaster is None:
            raise ValueError("Employee list required (employee_master model unavailable)")
        employee_ids = [e.id for e in db.query(EmployeeMaster.id).all()]

    created_records = []
    for emp_id in employee_ids:
        # Count approved optional holiday applications used in from_year
        from sqlalchemy import extract
        used_count = db.query(func.count(OptionalHolidayApplication.id)).filter(
            OptionalHolidayApplication.employee_id == emp_id,
            OptionalHolidayApplication.status == OptionalAppStatus.APPROVED,
            extract("year", OptionalHolidayApplication.holiday_date) == payload.from_year,
        ).scalar() or 0

        # Total optional holidays available in from_year
        total_optional = db.query(func.count(Holiday.id)).filter(
            extract("year", Holiday.holiday_date) == payload.from_year,
            Holiday.holiday_type.in_(["OPTIONAL", "RESTRICTED"]),
        ).scalar() or 0

        unused = max(total_optional - used_count, 0)
        if payload.max_carry_forward is not None:
            unused = min(unused, payload.max_carry_forward)

        # Avoid duplicate processing
        existing = db.query(HolidayCarryForward).filter(
            HolidayCarryForward.employee_id == emp_id,
            HolidayCarryForward.from_year == payload.from_year,
            HolidayCarryForward.to_year == payload.to_year,
        ).first()
        if existing:
            continue

        record = HolidayCarryForward(
            employee_id=emp_id,
            from_year=payload.from_year,
            to_year=payload.to_year,
            holidays_count=unused,
            status=CarryForwardStatus.PROCESSED if unused >= 0 else CarryForwardStatus.FAILED,
            processed_on=datetime.utcnow(),
        )
        db.add(record)
        created_records.append(record)

    db.commit()
    for r in created_records:
        db.refresh(r)
    return created_records


def list_carry_forward_records(
    db: Session,
    employee_id: Optional[int] = None,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
) -> List[dict]:
    q = db.query(HolidayCarryForward)
    if employee_id:
        q = q.filter(HolidayCarryForward.employee_id == employee_id)
    if from_year:
        q = q.filter(HolidayCarryForward.from_year == from_year)
    if to_year:
        q = q.filter(HolidayCarryForward.to_year == to_year)

    rows = q.order_by(HolidayCarryForward.created_at.desc()).all()
    results = []
    for r in rows:
        results.append({
            "id": r.id,
            "employee_id": r.employee_id,
            "employee_name": _employee_name(db, r.employee_id),
            "from_year": r.from_year,
            "to_year": r.to_year,
            "holidays_count": r.holidays_count,
            "status": r.status,
            "processed_by": r.processed_by,
            "processed_on": r.processed_on,
            "remarks": r.remarks,
            "created_at": r.created_at,
        })
    return results



def get_tab_summary(db: Session) -> HolidayCalendarTabSummary:
    
    holiday_master_count = db.query(func.count(Holiday.id)).filter(Holiday.is_active == True).scalar() or 0
    optional_apps_count  = db.query(func.count(OptionalHolidayApplication.id)).scalar() or 0
    calendars_count       = db.query(func.count(HolidayCalendar.id)).scalar() or 0
    holiday_swap_count    = db.query(func.count(HolidaySwapRequest.id)).filter(
        HolidaySwapRequest.status == SwapRequestStatus.PENDING
    ).scalar() or 0
    carry_forward_count   = db.query(func.count(HolidayCarryForward.id)).scalar() or 0

    return HolidayCalendarTabSummary(
        holiday_master_count=holiday_master_count,
        optional_apps_count=optional_apps_count,
        calendars_count=calendars_count,
        holiday_swap_count=holiday_swap_count,
        carry_forward_count=carry_forward_count,
    )