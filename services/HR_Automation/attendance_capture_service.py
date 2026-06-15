import math
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from model.HR_Automation.attendance_capture import (
    BiometricDevice, DeviceSyncLog, BiometricPunch,
    GeoFence, GPSAttendance,
    IPWhitelist, WebPortalAttendance,
    DailyAttendance, AttendanceSettings,
)
from schema.HR_Automation.attendance_capture import (
    BiometricDeviceCreate, BiometricDeviceUpdate,
    BiometricPunchSimulate,
    GeoFenceCreate, GeoFenceUpdate,
    GPSCheckInCreate,
    IPWhitelistCreate,
    WebCheckInCreate,
    AttendanceSettingsUpdate,
)


def _haversine(lat1, lon1, lat2, lon2) -> float:
    
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class AttendanceCaptureService:

    

    def get_attendance_dashboard_summary(self, db: Session) -> dict:
        today = date.today()

        total_employees = db.query(func.count()).select_from(
            __import__("model.onboarding.employee", fromlist=["Employee"]).Employee
        ).scalar() or 0

        present = db.query(func.count(DailyAttendance.id)).filter(
            DailyAttendance.att_date == today,
            DailyAttendance.status == "Present",
        ).scalar() or 0

        absent = db.query(func.count(DailyAttendance.id)).filter(
            DailyAttendance.att_date == today,
            DailyAttendance.status == "Absent",
        ).scalar() or 0

        wfh = db.query(func.count(DailyAttendance.id)).filter(
            DailyAttendance.att_date == today,
            DailyAttendance.status == "WFH",
        ).scalar() or 0

        late = db.query(func.count(DailyAttendance.id)).filter(
            DailyAttendance.att_date == today,
            DailyAttendance.is_late == True,
        ).scalar() or 0

        bio_punches = db.query(func.count(BiometricPunch.id)).filter(
            func.date(BiometricPunch.punch_time) == today
        ).scalar() or 0

        gps_checkins = db.query(func.count(GPSAttendance.id)).filter(
            func.date(GPSAttendance.punch_time) == today
        ).scalar() or 0

        web_checkins = db.query(func.count(WebPortalAttendance.id)).filter(
            func.date(WebPortalAttendance.punch_time) == today
        ).scalar() or 0

        return {
            "total_employees":   total_employees,
            "present_today":     present,
            "absent_today":      absent,
            "wfh_today":         wfh,
            "late_today":        late,
            "biometric_punches": bio_punches,
            "gps_checkins":      gps_checkins,
            "web_checkins":      web_checkins,
        }

    

    def add_biometric_device(self, db: Session, payload: BiometricDeviceCreate) -> BiometricDevice:
        device = BiometricDevice(**payload.model_dump())
        db.add(device)
        db.commit()
        db.refresh(device)
        return device

    def list_biometric_devices(self, db: Session, active_only: bool = False) -> List[BiometricDevice]:
        q = db.query(BiometricDevice)
        if active_only:
            q = q.filter(BiometricDevice.is_active == True)
        return q.order_by(BiometricDevice.id).all()

    def get_biometric_device(self, db: Session, device_id: int) -> Optional[BiometricDevice]:
        return db.query(BiometricDevice).filter(BiometricDevice.id == device_id).first()

    def update_biometric_device(self, db: Session, device_id: int, payload: BiometricDeviceUpdate) -> BiometricDevice:
        device = self.get_biometric_device(db, device_id)
        if not device:
            raise ValueError("Device not found")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(device, k, v)
        device.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(device)
        return device

    def delete_biometric_device(self, db: Session, device_id: int) -> bool:
        device = self.get_biometric_device(db, device_id)
        if not device:
            return False
        db.delete(device)
        db.commit()
        return True

    

    def sync_device(self, db: Session, device_id: int) -> DeviceSyncLog:
        device = self.get_biometric_device(db, device_id)
        if not device:
            raise ValueError("Device not found")
        device.last_sync_at = datetime.utcnow()
        device.is_online = True
        log = DeviceSyncLog(device_id=device_id, status="success", records_synced=0)
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def sync_all_devices(self, db: Session) -> List[DeviceSyncLog]:
        devices = db.query(BiometricDevice).filter(BiometricDevice.is_active == True).all()
        logs = []
        for device in devices:
            log = self.sync_device(db, device.id)
            logs.append(log)
        return logs

    def reconnect_offline_devices(self, db: Session) -> List[BiometricDevice]:
        devices = db.query(BiometricDevice).filter(
            BiometricDevice.is_active == True,
            BiometricDevice.is_online == False,
        ).all()
        for d in devices:
            d.is_online = True
        db.commit()
        return devices

    def get_sync_logs(self, db: Session, device_id: Optional[int] = None, limit: int = 20) -> List[DeviceSyncLog]:
        q = db.query(DeviceSyncLog)
        if device_id:
            q = q.filter(DeviceSyncLog.device_id == device_id)
        return q.order_by(DeviceSyncLog.synced_at.desc()).limit(limit).all()

    

    def simulate_biometric_punch(self, db: Session, payload: BiometricPunchSimulate) -> BiometricPunch:
        punch = BiometricPunch(
            device_id=payload.device_id,
            employee_id=payload.employee_id,
            punch_time=payload.punch_time or datetime.utcnow(),
            punch_type=payload.punch_type,
        )
        db.add(punch)
        db.commit()
        db.refresh(punch)
        return punch

    def get_punch_statistics(self, db: Session, employee_id: int) -> dict:
        total = db.query(func.count(BiometricPunch.id)).filter(
            BiometricPunch.employee_id == employee_id
        ).scalar() or 0
        ins  = db.query(func.count(BiometricPunch.id)).filter(
            BiometricPunch.employee_id == employee_id,
            BiometricPunch.punch_type == "IN",
        ).scalar() or 0
        outs = total - ins
        return {"total_punches": total, "in_punches": ins, "out_punches": outs}

   

    def add_geo_fence(self, db: Session, payload: GeoFenceCreate) -> GeoFence:
        fence = GeoFence(**payload.model_dump())
        db.add(fence)
        db.commit()
        db.refresh(fence)
        return fence

    def list_geo_fences(self, db: Session, active_only: bool = True) -> List[GeoFence]:
        q = db.query(GeoFence)
        if active_only:
            q = q.filter(GeoFence.is_active == True)
        return q.all()

    def update_geo_fence(self, db: Session, fence_id: int, payload: GeoFenceUpdate) -> GeoFence:
        fence = db.query(GeoFence).filter(GeoFence.id == fence_id).first()
        if not fence:
            raise ValueError("Geo-fence not found")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(fence, k, v)
        fence.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(fence)
        return fence

    def delete_geo_fence(self, db: Session, fence_id: int) -> bool:
        fence = db.query(GeoFence).filter(GeoFence.id == fence_id).first()
        if not fence:
            return False
        db.delete(fence)
        db.commit()
        return True

    def gps_check_in(self, db: Session, payload: GPSCheckInCreate, client_ip: str) -> GPSAttendance:
        within = False
        fence_id = payload.geo_fence_id
        if fence_id:
            fence = db.query(GeoFence).filter(GeoFence.id == fence_id).first()
            if fence:
                dist = _haversine(payload.latitude, payload.longitude, fence.latitude, fence.longitude)
                within = dist <= fence.radius_meters

        record = GPSAttendance(
            employee_id=payload.employee_id,
            geo_fence_id=fence_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            punch_type=payload.punch_type,
            ip_address=client_ip,
            is_within_fence=within,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_gps_statistics(self, db: Session, employee_id: Optional[int] = None) -> dict:
        q = db.query(GPSAttendance)
        if employee_id:
            q = q.filter(GPSAttendance.employee_id == employee_id)
        total   = q.count()
        within  = q.filter(GPSAttendance.is_within_fence == True).count()
        outside = total - within
        pct     = round(within / total * 100, 1) if total > 0 else 0.0
        return {"total_checkins": total, "within_fence": within, "outside_fence": outside, "fence_compliance_pct": pct}

   

    def add_ip_whitelist(self, db: Session, payload: IPWhitelistCreate) -> IPWhitelist:
        entry = IPWhitelist(**payload.model_dump())
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def list_ip_whitelist(self, db: Session) -> List[IPWhitelist]:
        return db.query(IPWhitelist).filter(IPWhitelist.is_active == True).all()

    def remove_ip_whitelist(self, db: Session, entry_id: int) -> bool:
        entry = db.query(IPWhitelist).filter(IPWhitelist.id == entry_id).first()
        if not entry:
            return False
        db.delete(entry)
        db.commit()
        return True

    def is_ip_whitelisted(self, db: Session, ip: str) -> bool:
        return db.query(IPWhitelist).filter(
            IPWhitelist.ip_address == ip,
            IPWhitelist.is_active == True,
        ).first() is not None

    

    def web_check_in(self, db: Session, payload: WebCheckInCreate, client_ip: str) -> WebPortalAttendance:
        record = WebPortalAttendance(
            employee_id=payload.employee_id,
            punch_type=payload.punch_type,
            ip_address=client_ip,
            is_wfh=payload.is_wfh,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def mark_wfh(self, db: Session, employee_id: int, work_date: date) -> DailyAttendance:
        record = db.query(DailyAttendance).filter(
            DailyAttendance.employee_id == employee_id,
            DailyAttendance.att_date == work_date,
        ).first()
        if not record:
            record = DailyAttendance(employee_id=employee_id, att_date=work_date)
            db.add(record)
        record.status = "WFH"
        db.commit()
        db.refresh(record)
        return record

    def get_recent_web_activity(self, db: Session, limit: int = 20) -> List[WebPortalAttendance]:
        return db.query(WebPortalAttendance).order_by(
            WebPortalAttendance.punch_time.desc()
        ).limit(limit).all()

    

    def get_daily_attendance(
        self, db: Session,
        employee_id: Optional[int] = None,
        att_date: Optional[date] = None,
    ) -> List[DailyAttendance]:
        q = db.query(DailyAttendance)
        if employee_id:
            q = q.filter(DailyAttendance.employee_id == employee_id)
        if att_date:
            q = q.filter(DailyAttendance.att_date == att_date)
        return q.order_by(DailyAttendance.att_date.desc()).all()

    

    def _get_or_create_settings(self, db: Session) -> AttendanceSettings:
        settings = db.query(AttendanceSettings).first()
        if not settings:
            settings = AttendanceSettings()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    def get_attendance_settings(self, db: Session) -> AttendanceSettings:
        return self._get_or_create_settings(db)

    def update_attendance_settings(self, db: Session, payload: AttendanceSettingsUpdate) -> AttendanceSettings:
        settings = self._get_or_create_settings(db)
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(settings, k, v)
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
        return settings

    def reset_attendance_settings(self, db: Session) -> AttendanceSettings:
        settings = self._get_or_create_settings(db)
        settings.grace_minutes         = 10
        settings.half_day_hours        = 4.0
        settings.full_day_hours        = 8.0
        settings.allow_gps             = True
        settings.allow_web             = True
        settings.allow_biometric       = True
        settings.ip_restriction        = False
        settings.geo_fence_restriction = False
        settings.updated_at            = datetime.utcnow()
        db.commit()
        db.refresh(settings)
        return settings


attendance_capture_service = AttendanceCaptureService()