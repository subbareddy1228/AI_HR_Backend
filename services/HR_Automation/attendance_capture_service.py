from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import List, Optional
import math

from model.HR_Automation.attendance_capture import (
    BiometricDevice, BiometricPunch, DeviceSyncLog,
    GeoFenceLocation, GPSAttendance,
    IPWhitelist, WebPortalAttendance,
    DailyAttendance, AttendanceSettings,
    DeviceStatus, PunchType, AttendanceStatus, AttendanceMethod,
)
from schema.HR_Automation.attendance_capture import (
    BiometricDeviceCreate, BiometricDeviceUpdate,
    BiometricPunchSimulate,
    GeoFenceCreate, GeoFenceUpdate,
    GPSCheckInCreate,
    IPWhitelistCreate,
    WebCheckInCreate,
    AttendanceSettingsUpdate,
    AttendanceDashboardSummary,
)




def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))




def add_biometric_device(db: Session, payload: BiometricDeviceCreate) -> BiometricDevice:
    device = BiometricDevice(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def list_biometric_devices(db: Session, active_only: bool = False) -> List[BiometricDevice]:
    q = db.query(BiometricDevice)
    if active_only:
        q = q.filter(BiometricDevice.is_active == True)
    return q.all()


def get_biometric_device(db: Session, device_id: int) -> Optional[BiometricDevice]:
    return db.query(BiometricDevice).filter(BiometricDevice.id == device_id).first()


def update_biometric_device(db: Session, device_id: int, payload: BiometricDeviceUpdate) -> BiometricDevice:
    device = get_biometric_device(db, device_id)
    if not device:
        raise ValueError(f"Device {device_id} not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(device, field, val)
    device.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(device)
    return device


def delete_biometric_device(db: Session, device_id: int) -> bool:
    device = get_biometric_device(db, device_id)
    if not device:
        return False
    db.delete(device)
    db.commit()
    return True


def sync_device(db: Session, device_id: int) -> DeviceSyncLog:
    
    device = get_biometric_device(db, device_id)
    if not device:
        raise ValueError(f"Device {device_id} not found")

    
    device.status = DeviceStatus.SYNCING
    db.commit()

    try:
        # TODO: Replace with real SDK integration
        
        records_synced = 0  # placeholder

        device.status = DeviceStatus.ONLINE
        device.last_sync_at = datetime.utcnow()
        log = DeviceSyncLog(
            device_id=device_id,
            status="Success",
            records_synced=records_synced,
        )
    except Exception as exc:
        device.status = DeviceStatus.ERROR
        log = DeviceSyncLog(
            device_id=device_id,
            status="Failed",
            records_synced=0,
            error_message=str(exc),
        )

    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def sync_all_devices(db: Session) -> List[DeviceSyncLog]:
    devices = list_biometric_devices(db, active_only=True)
    return [sync_device(db, d.id) for d in devices]


def reconnect_offline_devices(db: Session) -> List[BiometricDevice]:
    offline = db.query(BiometricDevice).filter(BiometricDevice.status == DeviceStatus.OFFLINE).all()
    for d in offline:
        sync_device(db, d.id)
    return offline


def get_sync_logs(db: Session, device_id: Optional[int] = None, limit: int = 20) -> List[DeviceSyncLog]:
    q = db.query(DeviceSyncLog).order_by(DeviceSyncLog.sync_time.desc())
    if device_id:
        q = q.filter(DeviceSyncLog.device_id == device_id)
    return q.limit(limit).all()




def simulate_biometric_punch(db: Session, payload: BiometricPunchSimulate) -> BiometricPunch:
    punch = BiometricPunch(
        device_id=payload.device_id or 0,
        employee_id=payload.employee_id,
        punch_time=payload.punch_time or datetime.utcnow(),
        punch_type=payload.punch_type,
        is_simulated=True,
    )
    db.add(punch)
    db.commit()

    
    _upsert_daily_attendance(db, punch.employee_id, punch.punch_time.date(), punch.punch_type, AttendanceMethod.BIOMETRIC)

    db.refresh(punch)
    return punch


def get_punch_statistics(db: Session, employee_id: int) -> dict:
    today = date.today()
    total = db.query(func.count(BiometricPunch.id)).filter(BiometricPunch.employee_id == employee_id).scalar()
    today_count = db.query(func.count(BiometricPunch.id)).filter(
        BiometricPunch.employee_id == employee_id,
        func.date(BiometricPunch.punch_time) == today,
    ).scalar()
    return {"total_punches": total, "today_punches": today_count}



def add_geo_fence(db: Session, payload: GeoFenceCreate) -> GeoFenceLocation:
    fence = GeoFenceLocation(**payload.model_dump())
    db.add(fence)
    db.commit()
    db.refresh(fence)
    return fence


def list_geo_fences(db: Session, active_only: bool = True) -> List[GeoFenceLocation]:
    q = db.query(GeoFenceLocation)
    if active_only:
        q = q.filter(GeoFenceLocation.is_active == True)
    return q.all()


def update_geo_fence(db: Session, fence_id: int, payload: GeoFenceUpdate) -> GeoFenceLocation:
    fence = db.query(GeoFenceLocation).filter(GeoFenceLocation.id == fence_id).first()
    if not fence:
        raise ValueError(f"Geo-fence {fence_id} not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(fence, field, val)
    fence.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(fence)
    return fence


def delete_geo_fence(db: Session, fence_id: int) -> bool:
    fence = db.query(GeoFenceLocation).filter(GeoFenceLocation.id == fence_id).first()
    if not fence:
        return False
    db.delete(fence)
    db.commit()
    return True


def gps_check_in(db: Session, payload: GPSCheckInCreate, client_ip: str = "") -> GPSAttendance:
  
    fences = list_geo_fences(db, active_only=True)
    matched_fence_id: Optional[int] = None
    within_fence = False

    for fence in fences:
        dist = _haversine(payload.latitude, payload.longitude, fence.latitude, fence.longitude)
        if dist <= fence.radius_meters:
            matched_fence_id = fence.id
            within_fence = True
            break

    record = GPSAttendance(
        employee_id=payload.employee_id,
        punch_type=payload.punch_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=payload.accuracy_meters,
        geo_fence_id=matched_fence_id,
        within_fence=within_fence,
        punch_time=datetime.utcnow(),
        device_info=payload.device_info,
    )
    db.add(record)
    db.commit()

    _upsert_daily_attendance(db, payload.employee_id, date.today(), payload.punch_type, AttendanceMethod.GPS_MOBILE)

    db.refresh(record)
    return record


def get_gps_statistics(db: Session, employee_id: Optional[int] = None) -> dict:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    base = db.query(GPSAttendance)
    if employee_id:
        base = base.filter(GPSAttendance.employee_id == employee_id)

    today_count = base.filter(func.date(GPSAttendance.punch_time) == today).count()
    week_count = base.filter(GPSAttendance.punch_time >= week_start).count()
    offline_count = base.filter(GPSAttendance.within_fence == False).count()

    return {
        "today": today_count,
        "this_week": week_count,
        "pending": 0,          
        "offline": offline_count,
        "avg_hours_today": 0.0,
    }




def add_ip_whitelist(db: Session, payload: IPWhitelistCreate) -> IPWhitelist:
    entry = IPWhitelist(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_ip_whitelist(db: Session) -> List[IPWhitelist]:
    return db.query(IPWhitelist).filter(IPWhitelist.is_active == True).all()


def remove_ip_whitelist(db: Session, entry_id: int) -> bool:
    entry = db.query(IPWhitelist).filter(IPWhitelist.id == entry_id).first()
    if not entry:
        return False
    db.delete(entry)
    db.commit()
    return True


def is_ip_whitelisted(db: Session, ip: str) -> bool:
    return db.query(IPWhitelist).filter(
        IPWhitelist.ip_address == ip,
        IPWhitelist.is_active == True
    ).first() is not None




def web_check_in(db: Session, payload: WebCheckInCreate, client_ip: str) -> WebPortalAttendance:
    whitelisted = is_ip_whitelisted(db, client_ip)

    record = WebPortalAttendance(
        employee_id=payload.employee_id,
        punch_type=payload.punch_type,
        ip_address=client_ip,
        is_whitelisted_ip=whitelisted,
        webcam_snapshot_url=payload.webcam_snapshot_url,
        punch_time=datetime.utcnow(),
        attendance_type=payload.attendance_type or "Office",
    )
    db.add(record)
    db.commit()

    _upsert_daily_attendance(db, payload.employee_id, date.today(), payload.punch_type, AttendanceMethod.WEB_PORTAL)

    db.refresh(record)
    return record


def get_recent_web_activity(db: Session, limit: int = 20) -> List[WebPortalAttendance]:
    return (
        db.query(WebPortalAttendance)
        .filter(func.date(WebPortalAttendance.punch_time) == date.today())
        .order_by(WebPortalAttendance.punch_time.desc())
        .limit(limit)
        .all()
    )


def mark_wfh(db: Session, employee_id: int, work_date: date) -> WebPortalAttendance:
    record = WebPortalAttendance(
        employee_id=employee_id,
        punch_type=PunchType.CHECK_IN,
        ip_address="0.0.0.0",
        is_whitelisted_ip=False,
        punch_time=datetime.combine(work_date, datetime.min.time()),
        attendance_type="WFH",
    )
    db.add(record)
    db.commit()

    _upsert_daily_attendance(db, employee_id, work_date, PunchType.CHECK_IN, AttendanceMethod.WEB_PORTAL,
                             status=AttendanceStatus.WFH)
    db.refresh(record)
    return record




def _upsert_daily_attendance(
    db: Session,
    employee_id: int,
    att_date: date,
    punch_type: PunchType,
    method: AttendanceMethod,
    status: Optional[AttendanceStatus] = None,
):
    from datetime import time as dtime

    record = db.query(DailyAttendance).filter(
        DailyAttendance.employee_id == employee_id,
        DailyAttendance.attendance_date == att_date,
    ).first()

    now_time = datetime.utcnow().time()
    settings = _get_settings(db)

    if not record:
        record = DailyAttendance(
            employee_id=employee_id,
            attendance_date=att_date,
            method=method,
        )
        db.add(record)

    if punch_type == PunchType.CHECK_IN and record.check_in_time is None:
        record.check_in_time = now_time
        record.status = status or AttendanceStatus.PRESENT
        record.method = method

       
        if settings and settings.work_start_time:
            start = datetime.combine(att_date, settings.work_start_time)
            actual = datetime.combine(att_date, now_time)
            diff_minutes = int((actual - start).total_seconds() / 60)
            threshold = settings.late_arrival_threshold_minutes or 15
            if diff_minutes > threshold:
                record.is_late = True
                record.late_minutes = diff_minutes
                record.status = AttendanceStatus.LATE

    elif punch_type == PunchType.CHECK_OUT:
        record.check_out_time = now_time
        if record.check_in_time:
            ci = datetime.combine(att_date, record.check_in_time)
            co = datetime.combine(att_date, now_time)
            total = (co - ci).total_seconds() / 3600
            record.total_hours = round(total, 2)

            if settings:
                std_hours = (
                    (datetime.combine(att_date, settings.work_end_time) -
                     datetime.combine(att_date, settings.work_start_time)).total_seconds() / 3600
                    if settings.work_start_time and settings.work_end_time else 8.0
                )
                if total > std_hours:
                    record.overtime_hours = round(total - std_hours, 2)

                
                half = settings.half_day_leave_hours or 4.0
                if total < half:
                    record.status = AttendanceStatus.HALF_DAY

    db.commit()


def _get_settings(db: Session) -> Optional[AttendanceSettings]:
    return db.query(AttendanceSettings).first()


def get_daily_attendance(
    db: Session,
    employee_id: Optional[int] = None,
    att_date: Optional[date] = None,
) -> List[DailyAttendance]:
    q = db.query(DailyAttendance)
    if employee_id:
        q = q.filter(DailyAttendance.employee_id == employee_id)
    if att_date:
        q = q.filter(DailyAttendance.attendance_date == att_date)
    return q.order_by(DailyAttendance.attendance_date.desc()).all()


def get_attendance_dashboard_summary(db: Session) -> AttendanceDashboardSummary:
    today = date.today()
    total = db.query(DailyAttendance).count()
    present = db.query(DailyAttendance).filter(
        DailyAttendance.attendance_date == today,
        DailyAttendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.WFH])
    ).count()
    late = db.query(DailyAttendance).filter(
        DailyAttendance.attendance_date == today,
        DailyAttendance.is_late == True,
    ).count()
    ot_row = db.query(func.coalesce(func.sum(DailyAttendance.overtime_hours), 0)).filter(
        DailyAttendance.attendance_date == today
    ).scalar()

    return AttendanceDashboardSummary(
        total_records=total,
        present_today=present,
        late_arrivals=late,
        overtime_hours=round(float(ot_row), 1),
    )



def get_attendance_settings(db: Session) -> AttendanceSettings:
    settings = db.query(AttendanceSettings).first()
    if not settings:
        settings = AttendanceSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_attendance_settings(db: Session, payload: AttendanceSettingsUpdate) -> AttendanceSettings:
    settings = get_attendance_settings(db)
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(settings, field, val)
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    return settings


def reset_attendance_settings(db: Session) -> AttendanceSettings:
    settings = get_attendance_settings(db)
    db.delete(settings)
    db.commit()
    new_settings = AttendanceSettings()
    db.add(new_settings)
    db.commit()
    db.refresh(new_settings)
    return new_settings
