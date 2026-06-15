
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from core.database import get_db
from schema.HR_Automation.attendance_capture import (
    
    BiometricDeviceCreate, BiometricDeviceUpdate, BiometricDeviceOut,
    BiometricPunchSimulate, BiometricPunchOut,
    DeviceSyncLogOut,
   
    GeoFenceCreate, GeoFenceUpdate, GeoFenceOut,
    GPSCheckInCreate, GPSAttendanceOut,
    GPSStatsOut,
    
    IPWhitelistCreate, IPWhitelistOut,
    WebCheckInCreate, WebPortalAttendanceOut,
    
    DailyAttendanceOut,
   
    AttendanceSettingsUpdate, AttendanceSettingsOut,
    
    AttendanceDashboardSummary,
)
from services.HR_Automation.attendance_capture_service import attendance_capture_service as svc

router = APIRouter(
    prefix="/capture",
    tags=["Attendance Capture & Tracking"],
)




@router.get("/dashboard/summary", response_model=AttendanceDashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    
    return svc.get_attendance_dashboard_summary(db)




@router.post("/biometric/devices", response_model=BiometricDeviceOut, status_code=201)
def add_device(payload: BiometricDeviceCreate, db: Session = Depends(get_db)):
    
    return svc.add_biometric_device(db, payload)


@router.get("/biometric/devices", response_model=List[BiometricDeviceOut])
def list_devices(active_only: bool = Query(False), db: Session = Depends(get_db)):
    
    return svc.list_biometric_devices(db, active_only=active_only)


@router.get("/biometric/devices/{device_id}", response_model=BiometricDeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = svc.get_biometric_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.patch("/biometric/devices/{device_id}", response_model=BiometricDeviceOut)
def update_device(device_id: int, payload: BiometricDeviceUpdate, db: Session = Depends(get_db)):
    try:
        return svc.update_biometric_device(db, device_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/biometric/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    if not svc.delete_biometric_device(db, device_id):
        raise HTTPException(status_code=404, detail="Device not found")
    return {"message": "Device deleted successfully"}




@router.post("/biometric/devices/{device_id}/sync", response_model=DeviceSyncLogOut)
def sync_device(device_id: int, db: Session = Depends(get_db)):
    
    try:
        return svc.sync_device(db, device_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/biometric/sync-all")
def sync_all_devices(db: Session = Depends(get_db)):
    
    logs = svc.sync_all_devices(db)
    return {"message": f"Synced {len(logs)} device(s)", "logs": [l.id for l in logs]}


@router.post("/biometric/reconnect-offline")
def reconnect_offline(db: Session = Depends(get_db)):
   
    devices = svc.reconnect_offline_devices(db)
    return {"message": f"Attempted reconnect for {len(devices)} offline device(s)"}


@router.get("/biometric/sync-logs", response_model=List[DeviceSyncLogOut])
def get_sync_logs(
    device_id: Optional[int] = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    return svc.get_sync_logs(db, device_id=device_id, limit=limit)




@router.post("/biometric/simulate-punch", response_model=BiometricPunchOut, status_code=201)
def simulate_punch(payload: BiometricPunchSimulate, db: Session = Depends(get_db)):
    
    return svc.simulate_biometric_punch(db, payload)


@router.get("/biometric/punch-stats/{employee_id}")
def punch_statistics(employee_id: int, db: Session = Depends(get_db)):
    
    return svc.get_punch_statistics(db, employee_id)




@router.post("/gps/geo-fences", response_model=GeoFenceOut, status_code=201)
def add_geo_fence(payload: GeoFenceCreate, db: Session = Depends(get_db)):
    
    return svc.add_geo_fence(db, payload)


@router.get("/gps/geo-fences", response_model=List[GeoFenceOut])
def list_geo_fences(active_only: bool = Query(True), db: Session = Depends(get_db)):
    
    return svc.list_geo_fences(db, active_only=active_only)


@router.patch("/gps/geo-fences/{fence_id}", response_model=GeoFenceOut)
def update_geo_fence(fence_id: int, payload: GeoFenceUpdate, db: Session = Depends(get_db)):
    try:
        return svc.update_geo_fence(db, fence_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/gps/geo-fences/{fence_id}")
def delete_geo_fence(fence_id: int, db: Session = Depends(get_db)):
    if not svc.delete_geo_fence(db, fence_id):
        raise HTTPException(status_code=404, detail="Geo-fence not found")
    return {"message": "Geo-fence deleted"}


@router.post("/gps/check-in", response_model=GPSAttendanceOut, status_code=201)
def gps_check_in(payload: GPSCheckInCreate, request: Request, db: Session = Depends(get_db)):
    
    client_ip = request.client.host if request.client else "0.0.0.0"
    return svc.gps_check_in(db, payload, client_ip)


@router.get("/gps/statistics")
def gps_statistics(employee_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    
    return svc.get_gps_statistics(db, employee_id=employee_id)


@router.get("/gps/recent-activity", response_model=List[GPSAttendanceOut])
def gps_recent_activity(limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    
    from sqlalchemy import func as sf
    from datetime import date
    from model.HR_Automation.attendance_capture import GPSAttendance
    today = date.today()
    records = (
        db.query(GPSAttendance)
        .filter(sf.date(GPSAttendance.punch_time) == today)
        .order_by(GPSAttendance.punch_time.desc())
        .limit(limit)
        .all()
    )
    return records




@router.post("/web/ip-whitelist", response_model=IPWhitelistOut, status_code=201)
def add_ip(payload: IPWhitelistCreate, db: Session = Depends(get_db)):
    
    return svc.add_ip_whitelist(db, payload)


@router.get("/web/ip-whitelist", response_model=List[IPWhitelistOut])
def list_ips(db: Session = Depends(get_db)):
    
    return svc.list_ip_whitelist(db)


@router.delete("/web/ip-whitelist/{entry_id}")
def remove_ip(entry_id: int, db: Session = Depends(get_db)):
    if not svc.remove_ip_whitelist(db, entry_id):
        raise HTTPException(status_code=404, detail="IP entry not found")
    return {"message": "IP removed from whitelist"}


@router.get("/web/check-ip")
def check_my_ip(request: Request, db: Session = Depends(get_db)):
  
    client_ip = request.client.host if request.client else "0.0.0.0"
    allowed = svc.is_ip_whitelisted(db, client_ip)
    return {"ip_address": client_ip, "is_whitelisted": allowed}


@router.post("/web/check-in", response_model=WebPortalAttendanceOut, status_code=201)
def web_check_in(payload: WebCheckInCreate, request: Request, db: Session = Depends(get_db)):
    
    client_ip = request.client.host if request.client else "0.0.0.0"
    return svc.web_check_in(db, payload, client_ip)


@router.post("/web/mark-wfh")
def mark_wfh(
    employee_id: int = Query(...),
    work_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    wd = work_date or date.today()
    record = svc.mark_wfh(db, employee_id, wd)
    return {"message": "Marked as WFH", "record_id": record.id}


@router.get("/web/recent-activity", response_model=List[WebPortalAttendanceOut])
def web_recent_activity(limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    
    return svc.get_recent_web_activity(db, limit=limit)




@router.get("/daily", response_model=List[DailyAttendanceOut])
def get_daily_attendance(
    employee_id: Optional[int] = Query(None),
    att_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.get_daily_attendance(db, employee_id=employee_id, att_date=att_date)


@router.get("/daily/today", response_model=List[DailyAttendanceOut])
def get_today_attendance(db: Session = Depends(get_db)):
    
    return svc.get_daily_attendance(db, att_date=date.today())




@router.get("/settings", response_model=AttendanceSettingsOut)
def get_settings(db: Session = Depends(get_db)):
   
    return svc.get_attendance_settings(db)


@router.patch("/settings", response_model=AttendanceSettingsOut)
def update_settings(payload: AttendanceSettingsUpdate, db: Session = Depends(get_db)):
   
    return svc.update_attendance_settings(db, payload)


@router.post("/settings/reset", response_model=AttendanceSettingsOut)
def reset_settings(db: Session = Depends(get_db)):
    
    return svc.reset_attendance_settings(db)
