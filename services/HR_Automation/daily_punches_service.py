from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Tuple
import math

from model.HR_Automation.daily_punches import (
    DailyPunch, DailyPunchSummary,
    PunchSource, PunchProcessStatus, AttendanceMark, PunchType,
)
from schema.HR_Automation.daily_punches import (
    DailyPunchCreate, DailyPunchUpdate,
    DailyPunchesFilter,
    ManualPunchCreate, RegularisePunch,
    DailyPunchSummaryOut, PaginatedDailyPunchesResponse,
    PunchInfo,
)


try:
    from model.Employee_Management.employee_master import EmployeeMaster  # adjust if tablename differs
    _EMPLOYEE_MODEL = EmployeeMaster
except ImportError:
    _EMPLOYEE_MODEL = None




def _format_duration(minutes: int) -> str:
    
    if minutes <= 0:
        return "0:00"
    h, m = divmod(minutes, 60)
    return f"{h}:{m:02d}"


def _time_to_display(t: Optional[time]) -> Optional[str]:
    
    if t is None:
        return None
    return t.strftime("%I:%M:%S%p")


def _get_employee_info(db: Session, employee_id: int) -> Tuple[str, str, str]:
    
    if _EMPLOYEE_MODEL is None:
        return ("", "", "")
    emp = db.query(_EMPLOYEE_MODEL).filter(_EMPLOYEE_MODEL.id == employee_id).first()
    if not emp:
        return ("", "", "")
    name = getattr(emp, "full_name", getattr(emp, "name", ""))
    code = getattr(emp, "employee_code", getattr(emp, "emp_code", ""))
    designation = getattr(emp, "designation", "")
    return (name, code, designation)


def _build_punch_info(t: Optional[time], source: Optional[PunchSource],
                      photo: Optional[str], lat: Optional[float], lon: Optional[float]) -> PunchInfo:
    return PunchInfo(
        time=_time_to_display(t),
        source=source,
        has_photo=bool(photo),
        has_gps=lat is not None,
        photo_url=photo,
        latitude=lat,
        longitude=lon,
    )




def record_punch(db: Session, payload: DailyPunchCreate) -> DailyPunch:
  
    punch = DailyPunch(
        employee_id=payload.employee_id,
        employee_code=payload.employee_code,
        punch_date=payload.punch_date,
        punch_time=payload.punch_time,
        punch_datetime=datetime.combine(payload.punch_date, payload.punch_time),
        punch_type=payload.punch_type.value if hasattr(payload.punch_type, "value") else payload.punch_type,
        source=payload.source,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_tag=payload.location_tag,
        photo_url=payload.photo_url,
        business_unit=payload.business_unit,
        location_name=payload.location_name,
        cost_center=payload.cost_center,
        department=payload.department,
        remarks=payload.remarks,
        process_status=PunchProcessStatus.PENDING,
    )
    db.add(punch)
    db.flush()   

    
    _rebuild_summary(db, payload.employee_id, payload.punch_date)

    db.commit()
    db.refresh(punch)
    return punch


def add_manual_punch(db: Session, payload: ManualPunchCreate) -> DailyPunch:
    
    create_payload = DailyPunchCreate(
        employee_id=payload.employee_id,
        punch_date=payload.punch_date,
        punch_time=payload.punch_time,
        punch_type=payload.punch_type,
        source=PunchSource.MANUAL,
        remarks=payload.remarks,
    )
    return record_punch(db, create_payload)




def _rebuild_summary(db: Session, employee_id: int, punch_date: date):
   
    punches = (
        db.query(DailyPunch)
        .filter(
            DailyPunch.employee_id == employee_id,
            DailyPunch.punch_date == punch_date,
        )
        .order_by(DailyPunch.punch_datetime)
        .all()
    )

    
    name, code, designation = _get_employee_info(db, employee_id)

    
    ins  = [p for p in punches if p.punch_type == "IN"]
    outs = [p for p in punches if p.punch_type == "OUT"]

    first_in  = ins[0]  if ins  else None
    last_out  = outs[-1] if outs else None

    
    duration_minutes = 0
    duration_display = "0:00"
    if first_in and last_out:
        ci = datetime.combine(punch_date, first_in.punch_time)
        co = datetime.combine(punch_date, last_out.punch_time)
        diff = int((co - ci).total_seconds() / 60)
        duration_minutes = max(diff, 0)
        duration_display = _format_duration(duration_minutes)

    has_no_punch = not bool(punches)

    
    try:
        from model.HR_Automation.attendance_capture import AttendanceSettings
        settings = db.query(AttendanceSettings).first()
    except Exception:
        settings = None

    late_threshold = settings.late_arrival_threshold_minutes if settings else 15
    work_start     = settings.work_start_time if settings else None

    is_late = False
    if first_in and work_start:
        start_dt  = datetime.combine(punch_date, work_start)
        actual_dt = datetime.combine(punch_date, first_in.punch_time)
        diff_min  = (actual_dt - start_dt).total_seconds() / 60
        if diff_min > late_threshold:
            is_late = True

    if has_no_punch:
        mark = AttendanceMark.ABSENT
    elif is_late:
        mark = AttendanceMark.LATE
    elif settings and duration_minutes < (settings.half_day_leave_hours or 4) * 60:
        mark = AttendanceMark.HALF_DAY
    else:
        mark = AttendanceMark.PRESENT

    
    first_punch = punches[0] if punches else None
    org = {
        "business_unit": first_punch.business_unit if first_punch else None,
        "location_name": first_punch.location_name if first_punch else None,
        "cost_center":   first_punch.cost_center   if first_punch else None,
        "department":    first_punch.department     if first_punch else None,
    }

   
    summary = (
        db.query(DailyPunchSummary)
        .filter(
            DailyPunchSummary.employee_id  == employee_id,
            DailyPunchSummary.summary_date == punch_date,
        )
        .first()
    )

    if not summary:
        summary = DailyPunchSummary(
            employee_id=employee_id,
            summary_date=punch_date,
        )
        db.add(summary)

    summary.employee_code   = code
    summary.designation     = designation
    summary.first_in_time   = first_in.punch_time   if first_in  else None
    summary.last_out_time   = last_out.punch_time    if last_out  else None
    summary.first_in_source = first_in.source        if first_in  else None
    summary.last_out_source = last_out.source         if last_out  else None
    summary.first_in_photo  = first_in.photo_url     if first_in  else None
    summary.last_out_photo  = last_out.photo_url      if last_out  else None
    summary.first_in_lat    = first_in.latitude       if first_in  else None
    summary.first_in_lon    = first_in.longitude      if first_in  else None
    summary.last_out_lat    = last_out.latitude        if last_out  else None
    summary.last_out_lon    = last_out.longitude       if last_out  else None
    summary.duration_minutes = duration_minutes
    summary.duration_display = duration_display
    summary.attendance_mark  = mark
    summary.is_late          = is_late
    summary.has_no_punch     = has_no_punch
    summary.process_status   = PunchProcessStatus.PENDING
    summary.updated_at       = datetime.utcnow()
    summary.business_unit    = org["business_unit"]
    summary.location_name    = org["location_name"]
    summary.cost_center      = org["cost_center"]
    summary.department       = org["department"]



def get_daily_punches(
    db: Session,
    filters: DailyPunchesFilter,
) -> PaginatedDailyPunchesResponse:
    
    q = db.query(DailyPunchSummary).filter(
        DailyPunchSummary.summary_date == filters.punch_date
    )

    if filters.business_unit:
        q = q.filter(DailyPunchSummary.business_unit == filters.business_unit)
    if filters.location:
        q = q.filter(DailyPunchSummary.location_name == filters.location)
    if filters.cost_center:
        q = q.filter(DailyPunchSummary.cost_center == filters.cost_center)
    if filters.department:
        q = q.filter(DailyPunchSummary.department == filters.department)

    if filters.employee_id:
        q = q.filter(DailyPunchSummary.employee_id == filters.employee_id)

    
    if filters.late_only:
        q = q.filter(DailyPunchSummary.is_late == True)
    elif filters.absent_only:
        q = q.filter(DailyPunchSummary.attendance_mark == AttendanceMark.ABSENT)
    elif filters.no_punches:
        q = q.filter(DailyPunchSummary.has_no_punch == True)
   

    total = q.count()
    pages = math.ceil(total / filters.page_size) if filters.page_size else 1
    offset = (filters.page - 1) * filters.page_size

    rows = q.order_by(DailyPunchSummary.employee_id).offset(offset).limit(filters.page_size).all()

   
    items: List[DailyPunchSummaryOut] = []
    for sn, row in enumerate(rows, start=offset + 1):
        name, _, _ = _get_employee_info(db, row.employee_id)

        start_info = _build_punch_info(
            row.first_in_time, row.first_in_source,
            row.first_in_photo, row.first_in_lat, row.first_in_lon,
        )
        end_info = _build_punch_info(
            row.last_out_time, row.last_out_source,
            row.last_out_photo, row.last_out_lat, row.last_out_lon,
        )

        items.append(DailyPunchSummaryOut(
            sn=sn,
            employee_id=row.employee_id,
            employee_name=name,
            employee_code=row.employee_code,
            designation=row.designation,
            summary_date=row.summary_date,
            start=start_info,
            end=end_info,
            duration=row.duration_display or "0:00",
            duration_minutes=row.duration_minutes or 0,
            attendance_mark=row.attendance_mark,
            is_late=row.is_late,
            has_no_punch=row.has_no_punch,
            process_status=row.process_status,
            department=row.department,
            business_unit=row.business_unit,
            location_name=row.location_name,
            cost_center=row.cost_center,
        ))

    return PaginatedDailyPunchesResponse(
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        pages=pages,
        items=items,
    )



def get_employee_punches(db: Session, employee_id: int, punch_date: date) -> List[DailyPunch]:
    
    return (
        db.query(DailyPunch)
        .filter(
            DailyPunch.employee_id == employee_id,
            DailyPunch.punch_date  == punch_date,
        )
        .order_by(DailyPunch.punch_datetime)
        .all()
    )




def update_punch(db: Session, punch_id: int, payload: DailyPunchUpdate) -> DailyPunch:
    punch = db.query(DailyPunch).filter(DailyPunch.id == punch_id).first()
    if not punch:
        raise ValueError(f"Punch {punch_id} not found")

    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(punch, field, val)

    if payload.punch_time:
        punch.punch_datetime = datetime.combine(punch.punch_date, payload.punch_time)

    punch.updated_at = datetime.utcnow()
    db.flush()

    _rebuild_summary(db, punch.employee_id, punch.punch_date)
    db.commit()
    db.refresh(punch)
    return punch


def regularise_punch(db: Session, payload: RegularisePunch) -> DailyPunch:
  
    update_payload = DailyPunchUpdate(
        punch_time=payload.new_time,
        is_regularized=True,
        process_status=PunchProcessStatus.PROCESSED,
        remarks=f"Regularised: {payload.reason}",
    )
    return update_punch(db, payload.punch_id, update_payload)


def delete_punch(db: Session, punch_id: int) -> bool:
    punch = db.query(DailyPunch).filter(DailyPunch.id == punch_id).first()
    if not punch:
        return False
    emp_id, p_date = punch.employee_id, punch.punch_date
    db.delete(punch)
    db.flush()
    _rebuild_summary(db, emp_id, p_date)
    db.commit()
    return True




def mark_processed(db: Session, summary_ids: List[int]) -> int:
    
    count = (
        db.query(DailyPunchSummary)
        .filter(DailyPunchSummary.id.in_(summary_ids))
        .update(
            {
                DailyPunchSummary.process_status: PunchProcessStatus.PROCESSED,
                DailyPunchSummary.updated_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return count




def get_filter_options(db: Session) -> dict:
    
    def _distinct(col):
        return [r[0] for r in db.query(col).distinct().filter(col.isnot(None)).all()]

    return {
        "business_units": _distinct(DailyPunchSummary.business_unit),
        "locations":      _distinct(DailyPunchSummary.location_name),
        "cost_centers":   _distinct(DailyPunchSummary.cost_center),
        "departments":    _distinct(DailyPunchSummary.department),
    }