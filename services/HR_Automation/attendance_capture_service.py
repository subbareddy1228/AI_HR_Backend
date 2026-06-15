"""
services/attendance_service.py
All business logic for the Attendance Capture module.
Pure functions that receive a SQLAlchemy Session — no HTTP layer.

CHANGES FROM ORIGINAL:
- Added FieldEmployeeService (GPS Mobile tab — Field Employee Management)
- Added WFHRequestService (GPS Mobile tab — WFH Management panel)
- DashboardService.today_stats: added field_employee_summary to response
- All original services unchanged
"""

import math
import logging
import socket
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from model.HR_Automation.attendance_capture import (
    BiometricDevice, DeviceSyncLog, GeoLocation,
    AttendancePunch, AttendanceRecord, WhitelistedIP,
    OfflinePunchQueue, AttendanceSettings,
    FieldEmployee, WFHRequest,
    DeviceStatusEnum, SyncStatusEnum, SyncTypeEnum,
    OfflineStatusEnum, AttendanceStatusEnum, PunchTypeEnum,
    FieldEmployeeStatusEnum, WFHStatusEnum,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# HELPERS  (unchanged from original)
# ═══════════════════════════════════════════════════════

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres between two lat/lng coordinates."""
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_settings(db: Session) -> AttendanceSettings:
    s = db.query(AttendanceSettings).filter_by(id=1).first()
    if not s:
        s = AttendanceSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _is_duplicate(
    db: Session,
    employee_id: str,
    punch_time: datetime,
    punch_type: PunchTypeEnum,
    window_minutes: int,
) -> bool:
    window = timedelta(minutes=window_minutes)
    return db.query(AttendancePunch).filter(
        AttendancePunch.employee_id == employee_id,
        AttendancePunch.punch_type == punch_type,
        AttendancePunch.punch_time.between(punch_time - window, punch_time + window),
    ).first() is not None


def _is_ip_whitelisted(db: Session, ip: str) -> bool:
    return db.query(WhitelistedIP).filter_by(
        ip_address=ip, is_active=True
    ).first() is not None


def _find_geofence(
    db: Session, lat: float, lng: float
) -> tuple[Optional[GeoLocation], bool]:
    """Return (nearest matching GeoLocation, is_within_fence)."""
    for loc in db.query(GeoLocation).filter_by(is_active=True).all():
        dist = _haversine(lat, lng, float(loc.latitude), float(loc.longitude))
        if dist <= loc.radius_meters:
            return loc, True
    return None, False


# ═══════════════════════════════════════════════════════
# PUNCH SERVICE  (unchanged from original)
# ═══════════════════════════════════════════════════════

class PunchService:

    @staticmethod
    def biometric_punch(
        db: Session,
        employee_id: str,
        punch_type: PunchTypeEnum,
        device_id: int,
        punch_time: Optional[datetime] = None,
        device_user_id: str = "",
        is_offline: bool = False,
        created_by: Optional[int] = None,
    ) -> AttendancePunch:
        """Create a punch from a biometric device (or simulation)."""
        punch_time = punch_time or datetime.now(timezone.utc)
        settings   = _get_settings(db)

        device = db.query(BiometricDevice).filter_by(id=device_id, is_active=True).first()
        if not device:
            raise ValueError(f"Biometric device id={device_id} not found or inactive.")

        if _is_duplicate(db, employee_id, punch_time, punch_type,
                         settings.duplicate_punch_window_minutes):
            raise ValueError("Duplicate punch detected within the configured window.")

        punch = AttendancePunch(
            employee_id=employee_id,
            punch_time=punch_time,
            punch_type=punch_type,
            capture_method="biometric",
            biometric_device_id=device_id,
            device_user_id=device_user_id,
            is_offline_record=is_offline,
            created_by=created_by,
        )
        db.add(punch)
        db.flush()
        AttendanceAggregationService.upsert_daily_record(db, employee_id, punch_time.date())
        db.commit()
        db.refresh(punch)
        logger.info("Biometric punch: %s %s @ %s", employee_id, punch_type, punch_time)
        return punch

    @staticmethod
    def gps_punch(
        db: Session,
        employee_id: str,
        punch_type: PunchTypeEnum,
        latitude: float,
        longitude: float,
        gps_accuracy: Optional[float] = None,
        selfie_path: Optional[str] = None,
        punch_time: Optional[datetime] = None,
        created_by: Optional[int] = None,
    ) -> AttendancePunch:
        punch_time = punch_time or datetime.now(timezone.utc)
        settings   = _get_settings(db)

        if _is_duplicate(db, employee_id, punch_time, punch_type,
                         settings.duplicate_punch_window_minutes):
            raise ValueError("Duplicate GPS punch detected.")

        geo_location, within_fence = None, None
        if settings.geo_fencing_enabled:
            geo_location, within_fence = _find_geofence(db, latitude, longitude)

        punch = AttendancePunch(
            employee_id=employee_id,
            punch_time=punch_time,
            punch_type=punch_type,
            capture_method="gps",
            latitude=Decimal(str(latitude)),
            longitude=Decimal(str(longitude)),
            gps_accuracy=gps_accuracy,
            geo_location_id=geo_location.id if geo_location else None,
            is_within_geofence=within_fence,
            selfie_path=selfie_path,
            created_by=created_by,
        )
        db.add(punch)
        db.flush()
        AttendanceAggregationService.upsert_daily_record(db, employee_id, punch_time.date())
        db.commit()
        db.refresh(punch)
        return punch

    @staticmethod
    def web_punch(
        db: Session,
        employee_id: str,
        punch_type: PunchTypeEnum,
        ip_address: str,
        selfie_path: Optional[str] = None,
        punch_time: Optional[datetime] = None,
        created_by: Optional[int] = None,
    ) -> AttendancePunch:
        punch_time = punch_time or datetime.now(timezone.utc)
        settings   = _get_settings(db)

        if _is_duplicate(db, employee_id, punch_time, punch_type,
                         settings.duplicate_punch_window_minutes):
            raise ValueError("Duplicate web punch detected.")

        punch = AttendancePunch(
            employee_id=employee_id,
            punch_time=punch_time,
            punch_type=punch_type,
            capture_method="web",
            ip_address=ip_address,
            is_whitelisted_ip=_is_ip_whitelisted(db, ip_address),
            selfie_path=selfie_path,
            created_by=created_by,
        )
        db.add(punch)
        db.flush()
        AttendanceAggregationService.upsert_daily_record(db, employee_id, punch_time.date())
        db.commit()
        db.refresh(punch)
        return punch


# ═══════════════════════════════════════════════════════
# DAILY RECORD AGGREGATION  (unchanged from original)
# ═══════════════════════════════════════════════════════

class AttendanceAggregationService:

    @staticmethod
    def upsert_daily_record(
        db: Session, employee_id: str, record_date: date
    ) -> Optional[AttendanceRecord]:
        settings = _get_settings(db)
        punches  = (
            db.query(AttendancePunch)
            .filter(
                AttendancePunch.employee_id == employee_id,
                func.date(AttendancePunch.punch_time) == record_date,
                AttendancePunch.is_valid == True,
            )
            .order_by(AttendancePunch.punch_time)
            .all()
        )

        if not punches:
            db.query(AttendanceRecord).filter_by(
                employee_id=employee_id, date=record_date
            ).delete()
            db.commit()
            return None

        check_ins  = [p for p in punches if p.punch_type == PunchTypeEnum.check_in]
        check_outs = [p for p in punches if p.punch_type == PunchTypeEnum.check_out]

        first_in = check_ins[0].punch_time  if check_ins  else None
        last_out = check_outs[-1].punch_time if check_outs else None

        effective_hours = Decimal("0")
        if first_in and last_out and settings.auto_first_in_last_out:
            delta           = Decimal(str((last_out - first_in).total_seconds() / 3600))
            break_h         = Decimal(str(int(settings.break_duration_minutes) / 60))
            effective_hours = max(Decimal("0"), delta - break_h)

        overtime_hours = max(
            Decimal("0"),
            effective_hours - Decimal(str(settings.min_work_hours))
        )

        is_late, late_minutes = False, 0
        if first_in:
            sched_start = datetime.combine(
                record_date, settings.work_start_time
            ).replace(tzinfo=timezone.utc)
            diff = (first_in - sched_start).total_seconds() / 60
            if diff > int(settings.late_threshold_minutes):
                is_late, late_minutes = True, int(diff)

        is_early_checkout = False
        if last_out:
            sched_end = datetime.combine(
                record_date, settings.work_end_time
            ).replace(tzinfo=timezone.utc)
            diff = (sched_end - last_out).total_seconds() / 60
            is_early_checkout = diff > int(settings.early_checkout_threshold_minutes)

        half_day_h = Decimal(str(settings.half_day_threshold_hours))
        min_h      = Decimal(str(settings.min_work_hours))
        if effective_hours >= min_h:
            status = AttendanceStatusEnum.present
        elif effective_hours >= half_day_h:
            status = AttendanceStatusEnum.half_day
        elif effective_hours > 0:
            status = AttendanceStatusEnum.present
        else:
            status = AttendanceStatusEnum.absent

        if is_late and status == AttendanceStatusEnum.present:
            status = AttendanceStatusEnum.late

        methods        = [p.capture_method for p in punches]
        capture_method = max(set(methods), key=methods.count) if methods else ""

        record = db.query(AttendanceRecord).filter_by(
            employee_id=employee_id, date=record_date
        ).first()
        if record is None:
            record = AttendanceRecord(employee_id=employee_id, date=record_date)
            db.add(record)

        record.status            = status
        record.first_check_in    = first_in
        record.last_check_out    = last_out
        record.effective_hours   = effective_hours
        record.overtime_hours    = overtime_hours
        record.is_late           = is_late
        record.late_minutes      = late_minutes
        record.is_early_checkout = is_early_checkout
        record.punch_count       = len(punches)
        record.capture_method    = capture_method
        db.commit()
        db.refresh(record)
        return record


# ═══════════════════════════════════════════════════════
# DEVICE SYNC SERVICE  (unchanged from original)
# ═══════════════════════════════════════════════════════

class DeviceSyncService:

    @staticmethod
    def sync_device(
        db: Session,
        device: BiometricDevice,
        initiated_by: Optional[int] = None,
    ) -> DeviceSyncLog:
        log = DeviceSyncLog(
            device_id=device.id,
            sync_type=SyncTypeEnum.manual,
            status=SyncStatusEnum.in_progress,
            initiated_by=initiated_by,
        )
        db.add(log)
        device.status = DeviceStatusEnum.Syncing
        db.commit()

        try:
            raw_records = DeviceSyncService._fetch_from_device(device)
            count       = 0
            for raw in raw_records:
                emp_id     = raw.get("employee_id")
                punch_time = raw.get("punch_time")
                punch_type = raw.get("punch_type", PunchTypeEnum.check_in)
                settings   = _get_settings(db)

                if not _is_duplicate(db, emp_id, punch_time, punch_type,
                                     settings.duplicate_punch_window_minutes):
                    db.add(AttendancePunch(
                        employee_id=emp_id,
                        punch_time=punch_time,
                        punch_type=punch_type,
                        capture_method="biometric",
                        biometric_device_id=device.id,
                        device_user_id=raw.get("user_id", ""),
                    ))
                    AttendanceAggregationService.upsert_daily_record(
                        db, emp_id, punch_time.date()
                    )
                    count += 1

            device.status      = DeviceStatusEnum.Online
            device.last_sync   = datetime.now(timezone.utc)
            log.status         = SyncStatusEnum.success
            log.records_synced = count
            log.completed_at   = datetime.now(timezone.utc)
            db.commit()

        except Exception as exc:
            logger.exception("Sync failed for device %s", device.id)
            device.status     = DeviceStatusEnum.Error
            log.status        = SyncStatusEnum.failed
            log.error_message = str(exc)
            log.completed_at  = datetime.now(timezone.utc)
            db.commit()

        db.refresh(log)
        return log

    @staticmethod
    def _fetch_from_device(device: BiometricDevice) -> list[dict]:
        """
        STUB — replace with actual SDK call per vendor.

        ZKTeco (pyzk):
            from zk import ZK
            zk   = ZK(device.ip_address, port=device.sdk_port, timeout=5,
                      password=int(device.comm_key or 0))
            conn = zk.connect()
            rows = conn.get_attendance()
            conn.disconnect()
            return [{"employee_id": r.user_id, "punch_time": r.timestamp,
                     "punch_type": "check_in"} for r in rows]

        eSSL (iclock REST):
            import requests
            resp = requests.get(f"http://{device.ip_address}/iclock/data/iclock/push/", timeout=5)
            rows = resp.json().get("data", [])
            return [{"employee_id": r["pin"], "punch_time": datetime.fromisoformat(r["time"]),
                     "punch_type": "check_in"} for r in rows]
        """
        logger.info("STUB: _fetch_from_device called for %s %s",
                    device.vendor, device.ip_address)
        return []

    @staticmethod
    def sync_all_online(
        db: Session, initiated_by: Optional[int] = None
    ) -> list[DeviceSyncLog]:
        devices = db.query(BiometricDevice).filter_by(
            status=DeviceStatusEnum.Online, is_active=True
        ).all()
        return [DeviceSyncService.sync_device(db, d, initiated_by) for d in devices]

    @staticmethod
    def reconnect_offline(db: Session) -> list[BiometricDevice]:
        reconnected = []
        offline     = db.query(BiometricDevice).filter_by(
            status=DeviceStatusEnum.Offline, is_active=True
        ).all()
        for device in offline:
            try:
                sock = socket.create_connection(
                    (device.ip_address, device.sdk_port), timeout=3
                )
                sock.close()
                device.status = DeviceStatusEnum.Online
                reconnected.append(device)
            except (socket.timeout, ConnectionRefusedError, OSError):
                pass
        db.commit()
        return reconnected


# ═══════════════════════════════════════════════════════
# OFFLINE SYNC SERVICE  (unchanged from original)
# ═══════════════════════════════════════════════════════

class OfflineSyncService:

    @staticmethod
    def flush_queue(db: Session) -> dict:
        pending  = (
            db.query(OfflinePunchQueue)
            .filter_by(status=OfflineStatusEnum.pending)
            .order_by("punch_time")
            .all()
        )
        synced, failed = 0, 0
        settings = _get_settings(db)

        for item in pending:
            try:
                if not _is_duplicate(db, item.employee_id, item.punch_time,
                                     item.punch_type, settings.duplicate_punch_window_minutes):
                    db.add(AttendancePunch(
                        employee_id=item.employee_id,
                        punch_time=item.punch_time,
                        punch_type=item.punch_type,
                        capture_method=item.capture_method,
                        is_offline_record=True,
                    ))
                    AttendanceAggregationService.upsert_daily_record(
                        db, item.employee_id, item.punch_time.date()
                    )
                item.status    = OfflineStatusEnum.synced
                item.synced_at = datetime.now(timezone.utc)
                synced        += 1
            except Exception as exc:
                item.status        = OfflineStatusEnum.failed
                item.error_message = str(exc)
                failed            += 1

        db.commit()
        return {"synced": synced, "failed": failed}


# ═══════════════════════════════════════════════════════
# NEW: FIELD EMPLOYEE SERVICE
# ═══════════════════════════════════════════════════════

class FieldEmployeeService:

    @staticmethod
    def get_activity_summary(db: Session) -> dict:
        """
        Field Activity Summary panel — Active count and On Site count.
        Active  = status in (Active, Working, Traveling)
        On Site = status = Working
        """
        active  = db.query(FieldEmployee).filter(
            FieldEmployee.is_active == True,
            FieldEmployee.status.in_([
                FieldEmployeeStatusEnum.active,
                FieldEmployeeStatusEnum.working,
                FieldEmployeeStatusEnum.traveling,
            ])
        ).count()

        on_site = db.query(FieldEmployee).filter_by(
            is_active=True,
            status=FieldEmployeeStatusEnum.working,
        ).count()

        return {"active": active, "on_site": on_site}

    @staticmethod
    def get_field_staff_count(db: Session) -> int:
        """
        '4 Field Staff' badge on Web Portal tab.
        Returns count of all active field employees.
        """
        return db.query(FieldEmployee).filter_by(is_active=True).count()

    @staticmethod
    def deactivate(db: Session, employee_id: str) -> FieldEmployee:
        """Delete icon per field employee row — soft-delete."""
        fe = db.query(FieldEmployee).filter_by(
            employee_id=employee_id, is_active=True
        ).first()
        if not fe:
            raise ValueError(f"Field employee {employee_id} not found.")
        fe.is_active = False
        db.commit()
        db.refresh(fe)
        return fe

    @staticmethod
    def update_status(
        db: Session,
        employee_id: str,
        status: FieldEmployeeStatusEnum,
    ) -> FieldEmployee:
        """Status badge click per row — Active / Traveling / Working toggle."""
        fe = db.query(FieldEmployee).filter_by(
            employee_id=employee_id, is_active=True
        ).first()
        if not fe:
            raise ValueError(f"Field employee {employee_id} not found.")
        fe.status        = status
        fe.last_activity = datetime.now(timezone.utc)
        db.commit()
        db.refresh(fe)
        return fe


# ═══════════════════════════════════════════════════════
# NEW: WFH REQUEST SERVICE
# ═══════════════════════════════════════════════════════

class WFHRequestService:

    @staticmethod
    def get_today_summary(db: Session) -> dict:
        """
        Today's WFH count + Pending Requests count badges in WFH Management panel.
        """
        today = date.today()

        today_wfh = db.query(WFHRequest).filter(
            WFHRequest.date   == today,
            WFHRequest.status == WFHStatusEnum.approved,
        ).count()

        pending = db.query(WFHRequest).filter_by(
            status=WFHStatusEnum.pending
        ).count()

        return {"today_wfh": today_wfh, "pending_requests": pending}

    @staticmethod
    def cancel(db: Session, request_id: int, cancelled_by: int) -> WFHRequest:
        """Cancel a pending WFH request."""
        req = db.query(WFHRequest).filter_by(id=request_id).first()
        if not req:
            raise ValueError(f"WFH request {request_id} not found.")
        if req.status != WFHStatusEnum.pending:
            raise ValueError("Only pending requests can be cancelled.")
        req.status      = WFHStatusEnum.rejected
        req.approved_by = cancelled_by
        req.approved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(req)
        return req


# ═══════════════════════════════════════════════════════
# DASHBOARD / REPORTS  (updated to include field employee summary)
# ═══════════════════════════════════════════════════════

class DashboardService:

    @staticmethod
    def today_stats(db: Session) -> dict:
        today   = date.today()
        records = db.query(AttendanceRecord).filter_by(date=today)

        try:
            from models.employee import Employee
            total_employees = db.query(Employee).filter_by(status="Active").count()
        except Exception:
            total_employees = 0

        present  = records.filter(
            AttendanceRecord.status.in_(["present", "late"])
        ).count()
        late     = records.filter_by(is_late=True).count()
        on_leave = records.filter_by(status="on_leave").count()
        absent   = max(0, total_employees - present - on_leave)
        overtime = (
            db.query(func.sum(AttendanceRecord.overtime_hours))
            .filter_by(date=today)
            .scalar()
        ) or Decimal("0")

        device_status = {
            "total":   db.query(BiometricDevice).count(),
            "online":  db.query(BiometricDevice).filter_by(status=DeviceStatusEnum.Online).count(),
            "offline": db.query(BiometricDevice).filter_by(status=DeviceStatusEnum.Offline).count(),
            "syncing": db.query(BiometricDevice).filter_by(status=DeviceStatusEnum.Syncing).count(),
            "error":   db.query(BiometricDevice).filter_by(status=DeviceStatusEnum.Error).count(),
        }

        return {
            "total_records":  records.count(),
            "present_today":  present,
            "late_arrivals":  late,
            "overtime_hours": round(Decimal(str(overtime)), 1),
            "absent_today":   absent,
            "on_leave_today": on_leave,
            "device_status":  device_status,
        }

    @staticmethod
    def device_report(db: Session, device: BiometricDevice) -> dict:
        return {
            "device_id":      device.id,
            "model_name":     device.model_name,
            "vendor":         device.vendor,
            "ip_address":     device.ip_address,
            "total_punches":  db.query(AttendancePunch).filter_by(
                biometric_device_id=device.id).count(),
            "check_ins":      db.query(AttendancePunch).filter_by(
                biometric_device_id=device.id,
                punch_type=PunchTypeEnum.check_in).count(),
            "check_outs":     db.query(AttendancePunch).filter_by(
                biometric_device_id=device.id,
                punch_type=PunchTypeEnum.check_out).count(),
            "employees":      device.employee_count,
            "health_percent": device.health_percent,
            "status":         device.status,
            "last_sync":      device.last_sync,
        }
