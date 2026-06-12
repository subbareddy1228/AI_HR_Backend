"""
routers/attendance.py
FastAPI router — Attendance Capture & Tracking module.
Prefix: /api/attendance/capture

CHANGES FROM ORIGINAL:
1. sync_all_devices: added BackgroundTasks to avoid timeout
2. web_punch: fixed IP detection behind proxy (X-Forwarded-For)
3. list_records: added search + capture_method query params
4. export_records: added search + capture_method + status params
5. list_sync_logs: populates device_name on SyncLogOut
6. NEW: PATCH /locations/{id}/toggle-status
7. NEW: GET /gps/statistics
8. NEW: GET /gps/recent-activity
9. NEW: GET /field-employees
10. NEW: POST /field-employees
11. NEW: PATCH /field-employees/{id}/location
12. NEW: POST /field-employees/{id}/report
13. NEW: GET /wfh-requests
14. NEW: POST /wfh-requests
15. NEW: PATCH /wfh-requests/{id}/approve
16. NEW: POST /web/verify-ip
17. NEW: POST /web/mark-wfh
18. NEW: GET /web/current-status
19. NEW: GET /web/today-activity
20. NEW: GET /punches/statistics
21. NEW: POST /settings/reset-to-defaults
22. NEW: GET /settings/export
23. NEW: POST /settings/import
"""

import io
import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Form, Query, Request, BackgroundTasks,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from model.HR_Automation.attendance_capture import (
    BiometricDevice, DeviceSyncLog, GeoLocation,
    AttendancePunch, AttendanceRecord, WhitelistedIP,
    OfflinePunchQueue, AttendanceSettings,
    FieldEmployee, WFHRequest,
    PunchTypeEnum, CaptureMethodEnum,
    DeviceStatusEnum, SyncTypeEnum,
    WFHStatusEnum, FieldEmployeeStatusEnum,
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
    FieldEmployeeCreate, FieldEmployeeOut,
    FieldLocationUpdate, FieldReportCreate,
    WFHRequestCreate, WFHRequestOut, WFHDecision,
    GPSStatistics, WebCurrentStatus, PunchStatistics,
    MessageResponse,
)
from services.HR_Automation.attendance_capture_service import (
    PunchService, AttendanceAggregationService,
    DeviceSyncService, OfflineSyncService, DashboardService,
    _is_ip_whitelisted,
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
    """4 KPI tiles — Total Records, Present Today, Late Arrivals, Overtime Hours."""
    return DashboardService.today_stats(db)


# ─────────────────────────────────────────────────────────
# BIOMETRIC DEVICES — CRUD
# ─────────────────────────────────────────────────────────

@router.get("/devices", response_model=List[DeviceOut])
def list_devices(
    status:       Optional[str] = Query(None, description="Online|Offline|Syncing|Error"),
    db:           Session       = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    """Device Status Dashboard table + Device Health Monitor cards."""
    q = db.query(BiometricDevice).filter_by(is_active=True)
    if status:
        q = q.filter(BiometricDevice.status == status)
    devices = q.order_by(BiometricDevice.id).all()

    result = []
    for d in devices:
        out = DeviceOut.model_validate(d)
        out.total_punches = db.query(AttendancePunch).filter_by(biometric_device_id=d.id).count()
        out.check_ins     = db.query(AttendancePunch).filter_by(
            biometric_device_id=d.id, punch_type=PunchTypeEnum.check_in).count()
        out.check_outs    = db.query(AttendancePunch).filter_by(
            biometric_device_id=d.id, punch_type=PunchTypeEnum.check_out).count()
        out.recent_syncs  = [SyncLogOut.model_validate(l) for l in d.sync_logs[:5]]
        result.append(out)
    return result


@router.post("/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def add_device(
    payload:      DeviceCreate,
    db:           Session       = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    """+ Add Device form — Vendor, Device Type, Model Name, IP Address."""
    if db.query(BiometricDevice).filter_by(ip_address=payload.ip_address).first():
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"Device with IP {payload.ip_address} already exists.")
    device = BiometricDevice(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return DeviceOut.model_validate(device)


@router.get("/devices/{device_id}", response_model=DeviceOut)
def get_device(
    device_id:   int,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Edit icon — fetches device to pre-fill edit form."""
    device = db.query(BiometricDevice).filter_by(id=device_id).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")
    out = DeviceOut.model_validate(device)
    out.recent_syncs = [SyncLogOut.model_validate(l) for l in device.sync_logs[:5]]
    return out


@router.put("/devices/{device_id}", response_model=DeviceOut)
def update_device(
    device_id:   int,
    payload:     DeviceUpdate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Edit device modal → Save."""
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
    device_id:   int,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Trash icon in Device Status table — soft-delete."""
    device = db.query(BiometricDevice).filter_by(id=device_id).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")
    device.is_active = False
    db.commit()
    return {"message": f"Device {device_id} deactivated."}


# ─────────────────────────────────────────────────────────
# SYNC ACTIONS
# ─────────────────────────────────────────────────────────

@router.post("/devices/{device_id}/sync", response_model=SyncLogOut)
def sync_device(
    device_id:        int,
    background_tasks: BackgroundTasks,
    db:               Session = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    """Sync icon per device row — triggers manual sync for that device."""
    device = db.query(BiometricDevice).filter_by(id=device_id, is_active=True).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")
    log = DeviceSyncService.sync_device(db, device, initiated_by=current_user.id)
    return SyncLogOut.model_validate(log)


@router.post("/devices/sync-all", response_model=SyncAllResponse)
def sync_all_devices(
    background_tasks: BackgroundTasks,          # FIXED: added BackgroundTasks
    db:               Session = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    """Sync All Devices green button — queues all online devices in background."""
    devices = db.query(BiometricDevice).filter_by(
        status=DeviceStatusEnum.Online, is_active=True
    ).all()

    logs = []
    for device in devices:
        log = DeviceSyncLog(
            device_id=device.id,
            sync_type=SyncTypeEnum.manual,
            status="in_progress",
            initiated_by=current_user.id,
        )
        db.add(log)
        db.flush()
        logs.append(log)
        background_tasks.add_task(
            DeviceSyncService.sync_device, db, device, current_user.id
        )
    db.commit()

    return {
        "devices_triggered": len(devices),
        "logs": [SyncLogOut.model_validate(l) for l in logs],
    }


@router.post("/devices/reconnect-offline", response_model=ReconnectResponse)
def reconnect_offline_devices(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Reconnect Offline button — attempts reconnection for all offline devices."""
    reconnected = DeviceSyncService.reconnect_offline(db)
    return {"reconnected_count": len(reconnected), "device_ids": [d.id for d in reconnected]}


@router.get("/devices/{device_id}/report", response_model=DeviceReport)
def device_report(
    device_id:   int,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Device-wise Reports card — Total Punches, Check-ins, Check-outs, Employees."""
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
    """Export Device Report button — downloads device punch data as CSV."""
    device = db.query(BiometricDevice).filter_by(id=device_id).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found.")

    punches = db.query(AttendancePunch).filter_by(biometric_device_id=device_id).all()
    output  = io.StringIO()
    import csv
    writer = csv.writer(output)
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
    """Recent Syncing Activity table — Time, Device, Type, Status, Records."""
    q = db.query(DeviceSyncLog).order_by(DeviceSyncLog.started_at.desc())
    if device_id:
        q = q.filter_by(device_id=device_id)
    logs = q.limit(limit).all()

    result = []
    for l in logs:
        out = SyncLogOut.model_validate(l)
        out.device_name = l.device.model_name if l.device else ""   # FIXED: populate device_name
        result.append(out)
    return result


@router.get("/sync-logs/export")
def export_sync_logs(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Export Logs button — downloads sync activity as CSV."""
    import csv
    logs   = db.query(DeviceSyncLog).order_by(DeviceSyncLog.started_at.desc()).limit(500).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Device ID", "Device Name", "Type", "Status", "Records", "Started", "Completed"])
    for l in logs:
        writer.writerow([
            l.id, l.device_id,
            l.device.model_name if l.device else "",
            l.sync_type, l.status, l.records_synced,
            l.started_at.isoformat(),
            l.completed_at.isoformat() if l.completed_at else "",
        ])
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
    """Geo-fence Locations table — Location, Radius, Coordinates, Status."""
    return db.query(GeoLocation).filter_by(is_active=True).all()


@router.post("/locations", response_model=GeoLocationOut, status_code=status.HTTP_201_CREATED)
def create_location(
    payload:     GeoLocationCreate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """+ Add Geo-fence at Current Location button."""
    loc = GeoLocation(**payload.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return GeoLocationOut.model_validate(loc)


# NEW: Toggle geo-fence status (Status column toggle per row)
@router.patch("/locations/{location_id}/toggle-status", response_model=GeoLocationOut)
def toggle_location_status(
    location_id: int,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Status column toggle per geo-fence row — switches between Inactive and Active."""
    loc = db.query(GeoLocation).filter_by(id=location_id).first()
    if not loc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found.")
    loc.is_active = not loc.is_active
    db.commit()
    db.refresh(loc)
    return GeoLocationOut.model_validate(loc)


@router.delete("/locations/{location_id}", response_model=MessageResponse)
def delete_location(
    location_id: int,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Delete icon per geo-fence row."""
    loc = db.query(GeoLocation).filter_by(id=location_id).first()
    if not loc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found.")
    loc.is_active = False
    db.commit()
    return {"message": "Location deactivated."}


# ─────────────────────────────────────────────────────────
# GPS MOBILE TAB — STATISTICS & RECENT ACTIVITY
# ─────────────────────────────────────────────────────────

@router.get("/gps/statistics", response_model=GPSStatistics)
def get_gps_statistics(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """GPS Statistics panel — Today check-ins, This Week, Pending offline, Avg Hours."""
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())

    today_ci = db.query(AttendancePunch).filter(
        AttendancePunch.capture_method == CaptureMethodEnum.gps,
        AttendancePunch.punch_type     == PunchTypeEnum.check_in,
        func.date(AttendancePunch.punch_time) == today,
    ).count()

    this_week = db.query(AttendancePunch).filter(
        AttendancePunch.capture_method == CaptureMethodEnum.gps,
        func.date(AttendancePunch.punch_time) >= week_start,
    ).count()

    pending   = db.query(OfflinePunchQueue).filter_by(status="pending").count()

    avg_result = db.query(func.avg(AttendanceRecord.effective_hours)).filter_by(date=today).scalar()
    avg_hours  = round(Decimal(str(avg_result or 0)), 1)

    return {
        "today_checkins":    today_ci,
        "this_week_records": this_week,
        "pending_offline":   pending,
        "avg_hours_today":   avg_hours,
    }


@router.get("/gps/recent-activity")
def get_gps_recent_activity(
    limit:       int     = Query(20, ge=1, le=100),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Recent GPS Activity table — Employee, Time, Type, Hours, Status."""
    punches = (
        db.query(AttendancePunch)
        .filter_by(capture_method=CaptureMethodEnum.gps, is_valid=True)
        .order_by(AttendancePunch.punch_time.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "employee_id":      p.employee_id,
            "time":             p.punch_time,
            "type":             p.punch_type,
            "is_within_geofence": p.is_within_geofence,
            "status":           "Within Fence" if p.is_within_geofence else "Outside Fence",
        }
        for p in punches
    ]


# ─────────────────────────────────────────────────────────
# FIELD EMPLOYEE MANAGEMENT
# ─────────────────────────────────────────────────────────

@router.get("/field-employees", response_model=List[FieldEmployeeOut])
def list_field_employees(
    status_filter: Optional[str] = Query(None, alias="status",
                                         description="Active|Traveling|Working|Inactive"),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(get_current_user),
):
    """Field Employee Management table — Employee, Location, Status, Last Activity."""
    q = db.query(FieldEmployee).filter_by(is_active=True)
    if status_filter:
        q = q.filter_by(status=status_filter)
    return q.all()


@router.post("/field-employees", response_model=FieldEmployeeOut,
             status_code=status.HTTP_201_CREATED)
def add_field_employee(
    payload:     FieldEmployeeCreate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """+ Add Field Employee button."""
    existing = db.query(FieldEmployee).filter_by(
        employee_id=payload.employee_id, is_active=True
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"Employee {payload.employee_id} is already a field employee.")
    fe = FieldEmployee(**payload.model_dump())
    db.add(fe)
    db.commit()
    db.refresh(fe)
    return FieldEmployeeOut.model_validate(fe)


@router.patch("/field-employees/{employee_id}/location", response_model=FieldEmployeeOut)
def update_field_location(
    employee_id: str,
    payload:     FieldLocationUpdate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Update Field Location button — updates employee's current GPS coordinates."""
    fe = db.query(FieldEmployee).filter_by(
        employee_id=employee_id, is_active=True
    ).first()
    if not fe:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Field employee not found.")
    fe.latitude      = payload.latitude
    fe.longitude     = payload.longitude
    fe.location      = payload.location
    fe.last_activity = datetime.now(timezone.utc)
    db.commit()
    db.refresh(fe)
    return FieldEmployeeOut.model_validate(fe)


@router.post("/field-employees/{employee_id}/report",
             response_model=MessageResponse,
             status_code=status.HTTP_201_CREATED)
def submit_field_report(
    employee_id: str,
    payload:     FieldReportCreate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Submit Field Report button — submits daily activity report."""
    fe = db.query(FieldEmployee).filter_by(
        employee_id=employee_id, is_active=True
    ).first()
    if not fe:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Field employee not found.")
    fe.last_activity = datetime.now(timezone.utc)
    db.commit()
    return {"message": f"Field report submitted for {employee_id}."}


# ─────────────────────────────────────────────────────────
# WFH REQUESTS
# ─────────────────────────────────────────────────────────

@router.get("/wfh-requests", response_model=List[WFHRequestOut])
def list_wfh_requests(
    employee_id:   Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(get_current_user),
):
    """View Requests button + Today's WFH count + Pending Requests count badges."""
    q = db.query(WFHRequest)
    if employee_id:
        q = q.filter_by(employee_id=employee_id)
    if status_filter:
        q = q.filter_by(status=status_filter)
    return q.order_by(WFHRequest.date.desc()).all()


@router.post("/wfh-requests", response_model=WFHRequestOut,
             status_code=status.HTTP_201_CREATED)
def create_wfh_request(
    payload:     WFHRequestCreate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Date picker + Request button in WFH panel."""
    existing = db.query(WFHRequest).filter_by(
        employee_id=payload.employee_id, date=payload.date
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "WFH request already exists for this date.")
    req = WFHRequest(**payload.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    return WFHRequestOut.model_validate(req)


@router.patch("/wfh-requests/{request_id}/approve", response_model=WFHRequestOut)
def decide_wfh_request(
    request_id: int,
    payload:    WFHDecision,
    db:         Session = Depends(get_db),
    current_user        = Depends(get_current_user),
):
    """HR approval action on pending WFH request."""
    req = db.query(WFHRequest).filter_by(id=request_id).first()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "WFH request not found.")
    req.status      = WFHStatusEnum.approved if payload.approved else WFHStatusEnum.rejected
    req.approved_by = current_user.id
    req.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)
    return WFHRequestOut.model_validate(req)


# ─────────────────────────────────────────────────────────
# PUNCHES — BIOMETRIC / GPS / WEB
# ─────────────────────────────────────────────────────────

@router.post("/punch/biometric", response_model=PunchOut, status_code=status.HTTP_201_CREATED)
def biometric_punch(
    payload:     BiometricPunchIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Simulate Biometric CHECKIN button."""
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
    """GPS Check In button — GPS punch with coordinates and optional selfie."""
    selfie_path = None
    if selfie:
        ext         = selfie.filename.rsplit(".", 1)[-1]
        fname       = f"{uuid.uuid4()}.{ext}"
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
    """Web Check-in / Web Check-out / Quick Check-in / Quick Check-out buttons."""
    selfie_path = None
    if selfie:
        ext = selfie.filename.rsplit(".", 1)[-1]
        selfie_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.{ext}")
        with open(selfie_path, "wb") as f:
            f.write(await selfie.read())

    # FIXED: handle proxy/load balancer correctly
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
    )
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


# NEW: Punch Statistics (View Punch Statistics button)
@router.get("/punches/statistics", response_model=PunchStatistics)
def get_punch_statistics(
    employee_id:    Optional[str]               = Query(None),
    capture_method: Optional[CaptureMethodEnum] = Query(None),
    date_from:      Optional[date]              = Query(None),
    date_to:        Optional[date]              = Query(None),
    db:             Session                     = Depends(get_db),
    current_user                                = Depends(get_current_user),
):
    """View Punch Statistics button — aggregated punch counts by method/employee/date."""
    q = db.query(AttendancePunch).filter_by(is_valid=True)
    if employee_id:
        q = q.filter_by(employee_id=employee_id)
    if capture_method:
        q = q.filter_by(capture_method=capture_method)
    if date_from:
        q = q.filter(AttendancePunch.punch_time >= date_from)
    if date_to:
        q = q.filter(func.date(AttendancePunch.punch_time) <= date_to)

    total  = q.count()
    ci     = q.filter(AttendancePunch.punch_type == PunchTypeEnum.check_in).count()
    co     = q.filter(AttendancePunch.punch_type == PunchTypeEnum.check_out).count()

    by_method = {
        m.value: db.query(AttendancePunch).filter_by(
            capture_method=m, is_valid=True
        ).count()
        for m in CaptureMethodEnum
    }

    return {
        "total_punches": total,
        "check_ins":     ci,
        "check_outs":    co,
        "by_method":     by_method,
        "date_from":     date_from,
        "date_to":       date_to,
    }


@router.get("/punches", response_model=List[PunchOut])
def list_punches(
    employee_id:    Optional[str]               = Query(None),
    capture_method: Optional[CaptureMethodEnum] = Query(None),
    date_from:      Optional[date]              = Query(None),
    date_to:        Optional[date]              = Query(None),
    limit:          int                         = Query(100, le=1000),
    offset:         int                         = Query(0),
    db:             Session                     = Depends(get_db),
    current_user                                = Depends(get_current_user),
):
    """Raw punch list with filters."""
    q = db.query(AttendancePunch).filter_by(is_valid=True)
    if employee_id:
        q = q.filter_by(employee_id=employee_id)
    if capture_method:
        q = q.filter_by(capture_method=capture_method)
    if date_from:
        q = q.filter(AttendancePunch.punch_time >= date_from)
    if date_to:
        q = q.filter(func.date(AttendancePunch.punch_time) <= date_to)
    punches = q.order_by(AttendancePunch.punch_time.desc()).offset(offset).limit(limit).all()
    return [PunchOut.model_validate(p) for p in punches]


# ─────────────────────────────────────────────────────────
# ATTENDANCE RECORDS
# ─────────────────────────────────────────────────────────

@router.get("/records/today", response_model=List[AttendanceRecordOut])
def today_records(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Present Today KPI tile — today's specific records."""
    today = date.today()
    return [AttendanceRecordOut.model_validate(r) for r in
            db.query(AttendanceRecord).filter_by(date=today).all()]


@router.get("/records/export")
def export_records(
    search:         Optional[str]               = Query(None),           # ADDED
    capture_method: Optional[CaptureMethodEnum] = Query(None),           # ADDED
    status_filter:  Optional[str]               = Query(None, alias="status"),  # ADDED
    date_from:      Optional[date]              = Query(None),
    date_to:        Optional[date]              = Query(None),
    db:             Session                     = Depends(get_db),
    current_user                                = Depends(get_current_user),
):
    """Export button — downloads filtered records as CSV."""
    import csv
    q = db.query(AttendanceRecord)
    if search:
        try:
            from models.employee import Employee
            q = q.join(Employee, AttendanceRecord.employee_id == Employee.employee_id)
            q = q.filter(or_(
                Employee.name.ilike(f"%{search}%"),
                AttendanceRecord.employee_id.ilike(f"%{search}%"),
            ))
        except ImportError:
            q = q.filter(AttendanceRecord.employee_id.ilike(f"%{search}%"))
    if capture_method:
        q = q.filter(AttendanceRecord.capture_method == capture_method.value)
    if status_filter:
        q = q.filter(AttendanceRecord.status == status_filter)
    if date_from:
        q = q.filter(AttendanceRecord.date >= date_from)
    if date_to:
        q = q.filter(AttendanceRecord.date <= date_to)
    records = q.order_by(AttendanceRecord.date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Employee ID", "Date", "Status", "First In", "Last Out",
        "Effective Hours", "Overtime Hours", "Late", "Late Minutes",
        "Punch Count", "Capture Method",
    ])
    for r in records:
        writer.writerow([
            r.employee_id, r.date, r.status,
            r.first_check_in.isoformat()  if r.first_check_in  else "",
            r.last_check_out.isoformat()  if r.last_check_out  else "",
            r.effective_hours, r.overtime_hours,
            r.is_late, r.late_minutes, r.punch_count, r.capture_method,
        ])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_records.csv"},
    )


@router.get("/records", response_model=List[AttendanceRecordOut])
def list_records(
    employee_id:    Optional[str]               = Query(None),
    search:         Optional[str]               = Query(None),           # ADDED: name search
    capture_method: Optional[CaptureMethodEnum] = Query(None),           # ADDED: All Methods filter
    date_from:      Optional[date]              = Query(None),
    date_to:        Optional[date]              = Query(None),
    status_filter:  Optional[str]               = Query(None, alias="status"),
    limit:          int                         = Query(100, le=1000),
    offset:         int                         = Query(0),
    db:             Session                     = Depends(get_db),
    current_user                                = Depends(get_current_user),
):
    """Top filter bar — Search employees + All Status + All Methods + All Dates."""
    q = db.query(AttendanceRecord)
    if employee_id:
        q = q.filter_by(employee_id=employee_id)
    if search:
        try:
            from models.employee import Employee
            q = q.join(Employee, AttendanceRecord.employee_id == Employee.employee_id)
            q = q.filter(or_(
                Employee.name.ilike(f"%{search}%"),
                AttendanceRecord.employee_id.ilike(f"%{search}%"),
            ))
        except ImportError:
            q = q.filter(AttendanceRecord.employee_id.ilike(f"%{search}%"))
    if capture_method:
        q = q.filter(AttendanceRecord.capture_method == capture_method.value)
    if status_filter:
        q = q.filter(AttendanceRecord.status == status_filter)
    if date_from:
        q = q.filter(AttendanceRecord.date >= date_from)
    if date_to:
        q = q.filter(AttendanceRecord.date <= date_to)
    records = q.order_by(AttendanceRecord.date.desc()).offset(offset).limit(limit).all()
    return [AttendanceRecordOut.model_validate(r) for r in records]


# ─────────────────────────────────────────────────────────
# OFFLINE SYNC
# ─────────────────────────────────────────────────────────

@router.post("/offline/sync", response_model=OfflineSyncResponse)
def sync_offline_queue(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Offline Mode — flush offline punch queue when back online."""
    return OfflineSyncService.flush_queue(db)


@router.get("/offline/queue", response_model=List[dict])
def list_offline_queue(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """GPS Statistics Pending tile — count of punches in offline queue."""
    items = db.query(OfflinePunchQueue).filter_by(status="pending").order_by("punch_time").all()
    return [
        {
            "id":             str(i.id),
            "employee_id":    i.employee_id,
            "punch_time":     i.punch_time.isoformat(),
            "punch_type":     i.punch_type,
            "capture_method": i.capture_method,
        }
        for i in items
    ]


# ─────────────────────────────────────────────────────────
# WHITELISTED IPs
# ─────────────────────────────────────────────────────────

@router.get("/whitelist-ips", response_model=List[WhitelistedIPOut])
def list_whitelist_ips(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """IP Whitelist Management table."""
    return db.query(WhitelistedIP).filter_by(is_active=True).all()


@router.post("/whitelist-ips", response_model=WhitelistedIPOut,
             status_code=status.HTTP_201_CREATED)
def add_whitelist_ip(
    payload:     WhitelistedIPCreate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """IP input + + button — adds IP to whitelist."""
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
    """Trash icon per IP row."""
    ip = db.query(WhitelistedIP).filter_by(id=ip_id).first()
    if not ip:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "IP not found.")
    ip.is_active = False
    db.commit()
    return {"message": "IP removed from whitelist."}


# ─────────────────────────────────────────────────────────
# WEB PORTAL TAB
# ─────────────────────────────────────────────────────────

@router.post("/web/verify-ip")
def verify_ip(
    ip_address:  str     = Query(..., description="IP address to verify"),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Verify IP button — checks if IP is in whitelist, returns Allowed/Blocked."""
    is_wl = db.query(WhitelistedIP).filter_by(
        ip_address=ip_address, is_active=True
    ).first() is not None
    return {
        "ip_address":    ip_address,
        "is_whitelisted": is_wl,
        "status":        "Allowed" if is_wl else "Blocked",
    }


@router.post("/web/mark-wfh", response_model=WFHRequestOut,
             status_code=status.HTTP_201_CREATED)
def mark_wfh(
    employee_id: str     = Query(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Mark WFH quick button + Mark as Work From Home button — marks employee WFH for today."""
    today    = date.today()
    existing = db.query(WFHRequest).filter_by(
        employee_id=employee_id, date=today
    ).first()
    if existing:
        existing.status      = WFHStatusEnum.approved
        existing.approved_by = current_user.id
        existing.approved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return WFHRequestOut.model_validate(existing)
    req = WFHRequest(
        employee_id=employee_id,
        date=today,
        status=WFHStatusEnum.approved,
        approved_by=current_user.id,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return WFHRequestOut.model_validate(req)


@router.get("/web/current-status", response_model=WebCurrentStatus)
def get_web_current_status(
    employee_id: str,
    request:     Request,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Current Network Status panel (IP + Whitelisted badge) + Current Status: Ready badge."""
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
    )
    is_wl = _is_ip_whitelisted(db, client_ip)

    last_punch = (
        db.query(AttendancePunch)
        .filter_by(employee_id=employee_id)
        .order_by(AttendancePunch.punch_time.desc())
        .first()
    )

    if not last_punch:
        current_status = "Ready"
    elif last_punch.punch_type == PunchTypeEnum.check_in:
        current_status = "Checked In"
    else:
        current_status = "Checked Out"

    return {
        "employee_id":     employee_id,
        "ip_address":      client_ip,
        "is_whitelisted":  is_wl,
        "current_status":  current_status,
        "last_punch_type": last_punch.punch_type if last_punch else None,
        "last_punch_time": last_punch.punch_time if last_punch else None,
    }


@router.get("/web/today-activity")
def get_today_activity(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Today's Web & Field Activity section — Recent Web Attendance + Field Activity Today tables."""
    today = date.today()

    web_punches = (
        db.query(AttendancePunch)
        .filter(
            AttendancePunch.capture_method == CaptureMethodEnum.web,
            func.date(AttendancePunch.punch_time) == today,
        )
        .order_by(AttendancePunch.punch_time.desc())
        .limit(50)
        .all()
    )

    field_employees = db.query(FieldEmployee).filter_by(is_active=True).all()

    return {
        "recent_web_attendance": [
            {
                "employee_id": p.employee_id,
                "time":        p.punch_time,
                "type":        p.punch_type,
                "ip":          p.ip_address,
                "status":      "Whitelisted" if p.is_whitelisted_ip else "Not Whitelisted",
            }
            for p in web_punches
        ],
        "field_activity_today": [
            {
                "employee_id": fe.employee_id,
                "location":    fe.location,
                "check_in":    fe.last_activity,
                "status":      fe.status,
            }
            for fe in field_employees
        ],
    }


# ─────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────

# NEW: Reset to Defaults button
@router.post("/settings/reset-to-defaults", response_model=AttendanceSettingsOut)
def reset_settings_to_defaults(
    confirm:     bool    = Query(..., description="Must be true to proceed"),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Reset to Defaults button on Settings tab."""
    if not confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Pass confirm=true to reset to defaults.")
    s = db.query(AttendanceSettings).filter_by(id=1).first()
    if s:
        db.delete(s)
        db.commit()
    s = AttendanceSettings(id=1)
    db.add(s)
    db.commit()
    db.refresh(s)
    return AttendanceSettingsOut.model_validate(s)


# NEW: Export Settings button
@router.get("/settings/export")
def export_settings(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Export Settings button — downloads current settings as JSON file."""
    s = db.query(AttendanceSettings).filter_by(id=1).first()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No settings found.")
    data    = AttendanceSettingsOut.model_validate(s).model_dump(mode="json")
    payload = {"exported_at": datetime.now(timezone.utc).isoformat(), "settings": data}
    content = json.dumps(payload, indent=2, default=str)
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=attendance_settings.json"},
    )


# NEW: Import Settings button
@router.post("/settings/import", response_model=AttendanceSettingsOut)
async def import_settings(
    file:        UploadFile = File(..., description="JSON file from Export Settings"),
    db:          Session    = Depends(get_db),
    current_user            = Depends(get_current_user),
):
    """Import Settings button — uploads and applies a previously exported settings file."""
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .json files accepted.")
    content = await file.read()
    try:
        payload  = json.loads(content)
        raw      = payload.get("settings", payload)
        update   = AttendanceSettingsUpdate(**{
            k: v for k, v in raw.items()
            if k in AttendanceSettingsUpdate.model_fields
        })
    except Exception:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Invalid settings file format.")
    s = db.query(AttendanceSettings).filter_by(id=1).first()
    if not s:
        s = AttendanceSettings(id=1)
        db.add(s)
    for field, val in update.model_dump(exclude_none=True).items():
        setattr(s, field, val)
    s.updated_by = current_user.id
    db.commit()
    db.refresh(s)
    return AttendanceSettingsOut.model_validate(s)


@router.get("/settings", response_model=AttendanceSettingsOut)
def get_settings(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Settings tab load — all toggles, work hours, thresholds, field employee settings."""
    s = db.query(AttendanceSettings).filter_by(id=1).first()
    if not s:
        s = AttendanceSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return AttendanceSettingsOut.model_validate(s)


@router.put("/settings", response_model=AttendanceSettingsOut)
def update_settings(
    payload:     AttendanceSettingsUpdate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Save Settings / Save All Settings button."""
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
