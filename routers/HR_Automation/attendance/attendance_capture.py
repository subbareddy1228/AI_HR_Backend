"""
routers/attendance.py
FastAPI router — Attendance Capture & Tracking module.
Prefix: /api/attendance/capture
Matches the existing backend pattern: JWT via OAuth2PasswordBearer.
"""

import os
import uuid
from datetime import date, datetime
from typing import Optional, List

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Form, Query, Request, BackgroundTasks,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io, csv

from core.database import get_db
from core.dependencies import get_current_user  # reuse existing auth helpers
from model.HR_Automation.attendance_capture import (
    BiometricDevice, DeviceSyncLog, GeoLocation,
    AttendancePunch, AttendanceRecord, WhitelistedIP,
    OfflinePunchQueue, AttendanceSettings,
    PunchTypeEnum, CaptureMethodEnum,
)
from schema.HR_Automation.attendance_capture import (
    DeviceCreate, DeviceUpdate, DeviceOut, SyncLogOut,
    SyncAllResponse, ReconnectResponse, OfflineSyncResponse,
    GeoLocationCreate, GeoLocationOut,
    BiometricPunchIn, GPSPunchIn, WebPunchIn, PunchOut,
    AttendanceRecordOut, AttendanceRecordWithEmployee,
    AttendanceDashboard, DeviceReport,
    WhitelistedIPCreate, WhitelistedIPOut,
    AttendanceSettingsOut, AttendanceSettingsUpdate,
    MessageResponse,
)
from services.HR_Automation.attendance_capture import (
    PunchService, AttendanceAggregationService,
    DeviceSyncService, OfflineSyncService, DashboardService,
)

router = APIRouter(prefix="/api/attendance/capture", tags=["Attendance Capture"])

UPLOAD_DIR = os.getenv("SELFIE_UPLOAD_DIR", "/tmp/selfies")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=AttendanceDashboard)
def get_dashboard(
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    """Live attendance dashboard — total records, present, late, OT hours, device health."""
    return DashboardService.today_stats(db)


# ─────────────────────────────────────────────────────────
# BIOMETRIC DEVICES — CRUD
# ─────────────────────────────────────────────────────────

@router.get("/devices", response_model=List[DeviceOut])
def list_devices(
    status:       Optional[str] = Query(None, description="Filter by status: Online|Offline|Syncing|Error"),
    db:           Session       = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    q = db.query(BiometricDevice).filter_by(is_active=True)
    if status:
        q = q.filter(BiometricDevice.status == status)
    devices = q.order_by(BiometricDevice.id).all()

    result = []
    for d in devices:
        out = DeviceOut.model_validate(d)
        out.total_punches = db.query(AttendancePunch).filter_by(biometric_device_id=d.id).count()
        out.check_ins     = db.query(AttendancePunch).filter_by(biometric_device_id=d.id, punch_type=PunchTypeEnum.check_in).count()
        out.check_outs    = db.query(AttendancePunch).filter_by(biometric_device_id=d.id, punch_type=PunchTypeEnum.check_out).count()
        out.recent_syncs  = [SyncLogOut.model_validate(l) for l in d.sync_logs[:5]]
        result.append(out)
    return result


@router.post("/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def add_device(
    payload:      DeviceCreate,
    db:           Session       = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    """Register a new biometric device."""
    if db.query(BiometricDevice).filter_by(ip_address=payload.ip_address).first():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Device with IP {payload.ip_address} already exists.")
    device = BiometricDevice(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return DeviceOut.model_validate(device)


@router.get("/devices/{device_id}", response_model=DeviceOut)
def get_device(
    device_id: int,
    db:        Session = Depends(get_db),
    current_user       = Depends(get_current_user),
):
    device = db.query(BiometricDevice).filter_by(id=device_id).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")
    out = DeviceOut.model_validate(device)
    out.recent_syncs = [SyncLogOut.model_validate(l) for l in device.sync_logs[:5]]
    return out


@router.put("/devices/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: int,
    payload:   DeviceUpdate,
    db:        Session = Depends(get_db),
    current_user       = Depends(get_current_user),
):
    device = db.query(BiometricDevice).filter_by(id=device_id).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(device, field, val)
    db.commit()
    db.refresh(device)
    return DeviceOut.model_validate(device)


@router.delete("/devices/{device_id}", response_model=MessageResponse)
def delete_device(
    device_id: int,
    db:        Session = Depends(get_db),
    current_user       = Depends(get_current_user),
):
    device = db.query(BiometricDevice).filter_by(id=device_id).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")
    device.is_active = False  # soft-delete
    db.commit()
    return {"message": f"Device {device_id} deactivated."}


# ─────────────────────────────────────────────────────────
# SYNC ACTIONS
# ─────────────────────────────────────────────────────────

@router.post("/devices/{device_id}/sync", response_model=SyncLogOut)
def sync_device(
    device_id:          int,
    background_tasks:   BackgroundTasks,
    db:                 Session = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    """Trigger a manual sync for a single device."""
    device = db.query(BiometricDevice).filter_by(id=device_id, is_active=True).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")
    log = DeviceSyncService.sync_device(db, device, initiated_by=current_user.id)
    return SyncLogOut.model_validate(log)


@router.post("/devices/sync-all", response_model=SyncAllResponse)
def sync_all_devices(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Sync all Online devices at once."""
    logs = DeviceSyncService.sync_all_online(db, initiated_by=current_user.id)
    return {
        "devices_triggered": len(logs),
        "logs": [SyncLogOut.model_validate(l) for l in logs],
    }


@router.post("/devices/reconnect-offline", response_model=ReconnectResponse)
def reconnect_offline_devices(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Attempt to reconnect all Offline devices."""
    reconnected = DeviceSyncService.reconnect_offline(db)
    return {"reconnected_count": len(reconnected), "device_ids": [d.id for d in reconnected]}


@router.get("/devices/{device_id}/report", response_model=DeviceReport)
def device_report(
    device_id:   int,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    device = db.query(BiometricDevice).filter_by(id=device_id).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")
    return DashboardService.device_report(db, device)


@router.get("/devices/{device_id}/report/export")
def export_device_report(
    device_id:   int,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Download device punch stats as CSV."""
    device = db.query(BiometricDevice).filter_by(id=device_id).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")

    punches = db.query(AttendancePunch).filter_by(biometric_device_id=device_id).all()
    output  = io.StringIO()
    writer  = csv.writer(output)
    writer.writerow(["Punch ID", "Employee ID", "Punch Time", "Type"])
    for p in punches:
        writer.writerow([str(p.id), p.employee_id, p.punch_time.isoformat(), p.punch_type])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=device_{device_id}_report.csv"},
    )


# ─────────────────────────────────────────────────────────
# SYNC LOGS
# ─────────────────────────────────────────────────────────

@router.get("/sync-logs", response_model=List[SyncLogOut])
def list_sync_logs(
    device_id:   Optional[int] = Query(None),
    limit:       int           = Query(50, le=500),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    q = db.query(DeviceSyncLog).order_by(DeviceSyncLog.started_at.desc())
    if device_id:
        q = q.filter_by(device_id=device_id)
    return [SyncLogOut.model_validate(l) for l in q.limit(limit).all()]


@router.get("/sync-logs/export")
def export_sync_logs(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    logs    = db.query(DeviceSyncLog).order_by(DeviceSyncLog.started_at.desc()).limit(500).all()
    output  = io.StringIO()
    writer  = csv.writer(output)
    writer.writerow(["ID", "Device ID", "Type", "Status", "Records", "Started", "Completed"])
    for l in logs:
        writer.writerow([l.id, l.device_id, l.sync_type, l.status, l.records_synced,
                         l.started_at.isoformat(), l.completed_at.isoformat() if l.completed_at else ""])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sync_logs.csv"},
    )


# ─────────────────────────────────────────────────────────
# GEO LOCATIONS
# ─────────────────────────────────────────────────────────

@router.get("/locations", response_model=List[GeoLocationOut])
def list_locations(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    return db.query(GeoLocation).filter_by(is_active=True).all()


@router.post("/locations", response_model=GeoLocationOut, status_code=status.HTTP_201_CREATED)
def create_location(
    payload:     GeoLocationCreate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    loc = GeoLocation(**payload.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return GeoLocationOut.model_validate(loc)


@router.delete("/locations/{location_id}", response_model=MessageResponse)
def delete_location(
    location_id: int,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    loc = db.query(GeoLocation).filter_by(id=location_id).first()
    if not loc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found.")
    loc.is_active = False
    db.commit()
    return {"message": "Location deactivated."}


# ─────────────────────────────────────────────────────────
# PUNCHES — BIOMETRIC / GPS / WEB
# ─────────────────────────────────────────────────────────

@router.post("/punch/biometric", response_model=PunchOut, status_code=status.HTTP_201_CREATED)
def biometric_punch(
    payload:     BiometricPunchIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Record a punch received from a biometric device or simulate one from the UI.
    Used by: Biometric tab → 'Simulate Biometric CHECKIN' button.
    """
    try:
        punch = PunchService.biometric_punch(
            db=db,
            employee_id=payload.employee_id,
            punch_type=payload.punch_type,
            device_id=payload.device_id,
            punch_time=payload.punch_time,
            device_user_id=payload.device_user_id,
            is_offline=payload.is_offline_record,
            created_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return PunchOut.model_validate(punch)


@router.post("/punch/gps", response_model=PunchOut, status_code=status.HTTP_201_CREATED)
async def gps_punch(
    employee_id:  str             = Form(...),
    punch_type:   PunchTypeEnum   = Form(...),
    latitude:     float           = Form(...),
    longitude:    float           = Form(...),
    gps_accuracy: Optional[float] = Form(None),
    punch_time:   Optional[str]   = Form(None),
    selfie:       Optional[UploadFile] = File(None),
    db:           Session         = Depends(get_db),
    current_user                  = Depends(get_current_user),
):
    """GPS / mobile check-in with optional selfie upload."""
    selfie_path = None
    if selfie:
        ext        = selfie.filename.rsplit(".", 1)[-1]
        fname      = f"{uuid.uuid4()}.{ext}"
        selfie_path = os.path.join(UPLOAD_DIR, fname)
        with open(selfie_path, "wb") as f:
            f.write(await selfie.read())

    pt = datetime.fromisoformat(punch_time) if punch_time else None
    try:
        punch = PunchService.gps_punch(
            db=db,
            employee_id=employee_id,
            punch_type=punch_type,
            latitude=latitude,
            longitude=longitude,
            gps_accuracy=gps_accuracy,
            selfie_path=selfie_path,
            punch_time=pt,
            created_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return PunchOut.model_validate(punch)


@router.post("/punch/web", response_model=PunchOut, status_code=status.HTTP_201_CREATED)
async def web_punch(
    request:     Request,
    employee_id: str           = Form(...),
    punch_type:  PunchTypeEnum = Form(...),
    punch_time:  Optional[str] = Form(None),
    selfie:      Optional[UploadFile] = File(None),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """Web-portal check-in/out with IP whitelist check and optional selfie."""
    selfie_path = None
    if selfie:
        ext = selfie.filename.rsplit(".", 1)[-1]
        selfie_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.{ext}")
        with open(selfie_path, "wb") as f:
            f.write(await selfie.read())

    client_ip = request.client.host
    pt = datetime.fromisoformat(punch_time) if punch_time else None
    try:
        punch = PunchService.web_punch(
            db=db,
            employee_id=employee_id,
            punch_type=punch_type,
            ip_address=client_ip,
            selfie_path=selfie_path,
            punch_time=pt,
            created_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return PunchOut.model_validate(punch)


@router.get("/punches", response_model=List[PunchOut])
def list_punches(
    employee_id:    Optional[str]              = Query(None),
    capture_method: Optional[CaptureMethodEnum] = Query(None),
    date_from:      Optional[date]             = Query(None),
    date_to:        Optional[date]             = Query(None),
    limit:          int                        = Query(100, le=1000),
    offset:         int                        = Query(0),
    db:             Session                    = Depends(get_db),
    current_user                               = Depends(get_current_user),
):
    q = db.query(AttendancePunch).filter_by(is_valid=True)
    if employee_id:
        q = q.filter_by(employee_id=employee_id)
    if capture_method:
        q = q.filter_by(capture_method=capture_method)
    if date_from:
        q = q.filter(AttendancePunch.punch_time >= date_from)
    if date_to:
        from sqlalchemy import func as sqlfunc
        q = q.filter(sqlfunc.date(AttendancePunch.punch_time) <= date_to)
    punches = q.order_by(AttendancePunch.punch_time.desc()).offset(offset).limit(limit).all()
    return [PunchOut.model_validate(p) for p in punches]


# ─────────────────────────────────────────────────────────
# ATTENDANCE RECORDS (daily aggregated)
# ─────────────────────────────────────────────────────────

@router.get("/records", response_model=List[AttendanceRecordOut])
def list_records(
    employee_id: Optional[str]  = Query(None),
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit:       int             = Query(100, le=1000),
    offset:      int             = Query(0),
    db:          Session         = Depends(get_db),
    current_user                 = Depends(get_current_user),
):
    q = db.query(AttendanceRecord)
    if employee_id:
        q = q.filter_by(employee_id=employee_id)
    if status_filter:
        q = q.filter(AttendanceRecord.status == status_filter)
    if date_from:
        q = q.filter(AttendanceRecord.date >= date_from)
    if date_to:
        q = q.filter(AttendanceRecord.date <= date_to)
    records = q.order_by(AttendanceRecord.date.desc()).offset(offset).limit(limit).all()
    return [AttendanceRecordOut.model_validate(r) for r in records]


@router.get("/records/today", response_model=List[AttendanceRecordOut])
def today_records(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    today = date.today()
    return [AttendanceRecordOut.model_validate(r) for r in
            db.query(AttendanceRecord).filter_by(date=today).all()]


@router.get("/records/export")
def export_records(
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    db:          Session        = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    q = db.query(AttendanceRecord)
    if date_from:
        q = q.filter(AttendanceRecord.date >= date_from)
    if date_to:
        q = q.filter(AttendanceRecord.date <= date_to)
    records = q.order_by(AttendanceRecord.date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee ID", "Date", "Status", "First In", "Last Out",
                     "Effective Hours", "Overtime Hours", "Late", "Late Minutes", "Punch Count"])
    for r in records:
        writer.writerow([
            r.employee_id, r.date, r.status,
            r.first_check_in.isoformat() if r.first_check_in else "",
            r.last_check_out.isoformat() if r.last_check_out else "",
            r.effective_hours, r.overtime_hours,
            r.is_late, r.late_minutes, r.punch_count,
        ])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_records.csv"},
    )


# ─────────────────────────────────────────────────────────
# OFFLINE SYNC
# ─────────────────────────────────────────────────────────

@router.post("/offline/sync", response_model=OfflineSyncResponse)
def sync_offline_queue(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Flush the offline punch queue into the main attendance table."""
    return OfflineSyncService.flush_queue(db)


@router.get("/offline/queue", response_model=List[dict])
def list_offline_queue(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    items = db.query(OfflinePunchQueue).filter_by(status="pending").order_by("punch_time").all()
    return [{"id": str(i.id), "employee_id": i.employee_id, "punch_time": i.punch_time.isoformat(),
             "punch_type": i.punch_type, "capture_method": i.capture_method} for i in items]


# ─────────────────────────────────────────────────────────
# WHITELISTED IPs
# ─────────────────────────────────────────────────────────

@router.get("/whitelist-ips", response_model=List[WhitelistedIPOut])
def list_whitelist_ips(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    return db.query(WhitelistedIP).filter_by(is_active=True).all()


@router.post("/whitelist-ips", response_model=WhitelistedIPOut, status_code=status.HTTP_201_CREATED)
def add_whitelist_ip(
    payload:     WhitelistedIPCreate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    if db.query(WhitelistedIP).filter_by(ip_address=payload.ip_address).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "IP already whitelisted.")
    ip = WhitelistedIP(**payload.model_dump())
    db.add(ip)
    db.commit()
    db.refresh(ip)
    return WhitelistedIPOut.model_validate(ip)


@router.delete("/whitelist-ips/{ip_id}", response_model=MessageResponse)
def remove_whitelist_ip(
    ip_id:       int,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    ip = db.query(WhitelistedIP).filter_by(id=ip_id).first()
    if not ip:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "IP not found.")
    ip.is_active = False
    db.commit()
    return {"message": "IP removed from whitelist."}


# ─────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────

@router.get("/settings", response_model=AttendanceSettingsOut)
def get_settings(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    s = db.query(AttendanceSettings).filter_by(id=1).first()
    if not s:
        s = AttendanceSettings(id=1)
        db.add(s); db.commit(); db.refresh(s)
    return AttendanceSettingsOut.model_validate(s)


@router.put("/settings", response_model=AttendanceSettingsOut)
def update_settings(
    payload:     AttendanceSettingsUpdate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    s = db.query(AttendanceSettings).filter_by(id=1).first()
    if not s:
        s = AttendanceSettings(id=1)
        db.add(s)
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(s, field, val)
    s.updated_by = current_user.id
    db.commit()
    db.refresh(s)
    return AttendanceSettingsOut.model_validate(s)
