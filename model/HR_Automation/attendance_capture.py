"""
models/attendance.py
SQLAlchemy ORM models for the Attendance Capture module.
Stack: FastAPI + PostgreSQL + SQLAlchemy (matches existing backend pattern)

CHANGES FROM ORIGINAL:
- Added FieldEmployeeStatusEnum
- Added FieldEmployee model (GPS Mobile tab — Field Employee Management)
- Added WFHStatusEnum
- Added WFHRequest model (GPS Mobile tab — WFH Management panel)
"""

import uuid
from datetime import datetime, date, time
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time,
    ForeignKey, Text, Numeric, Enum as SAEnum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from core.database import Base


# ─────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────

class DeviceTypeEnum(str, enum.Enum):
    fingerprint = "fingerprint"
    face        = "face"
    rfid        = "rfid"
    iris        = "iris"
    pin         = "pin"


class DeviceStatusEnum(str, enum.Enum):
    Online  = "Online"
    Offline = "Offline"
    Syncing = "Syncing"
    Error   = "Error"


class VendorEnum(str, enum.Enum):
    ZKTeco    = "ZKTeco"
    eSSL      = "eSSL"
    Honeywell = "Honeywell"
    Suprema   = "Suprema"
    Hikvision = "Hikvision"
    Other     = "Other"


class PunchTypeEnum(str, enum.Enum):
    check_in       = "check_in"
    check_out      = "check_out"
    break_start    = "break_start"
    break_end      = "break_end"
    overtime_start = "overtime_start"
    overtime_end   = "overtime_end"


class CaptureMethodEnum(str, enum.Enum):
    biometric  = "biometric"
    gps        = "gps"
    web        = "web"
    manual     = "manual"
    simulation = "simulation"


class AttendanceStatusEnum(str, enum.Enum):
    present  = "present"
    absent   = "absent"
    late     = "late"
    half_day = "half_day"
    on_leave = "on_leave"
    holiday  = "holiday"
    weekend  = "weekend"


class SyncStatusEnum(str, enum.Enum):
    success     = "success"
    failed      = "failed"
    partial     = "partial"
    in_progress = "in_progress"


class SyncTypeEnum(str, enum.Enum):
    manual    = "manual"
    auto      = "auto"
    scheduled = "scheduled"


class OfflineStatusEnum(str, enum.Enum):
    pending = "pending"
    synced  = "synced"
    failed  = "failed"


# ─────────────────────────────────────────────────────────
# NEW: FIELD EMPLOYEE STATUS ENUM
# ─────────────────────────────────────────────────────────

class FieldEmployeeStatusEnum(str, enum.Enum):
    active    = "Active"
    traveling = "Traveling"
    working   = "Working"
    inactive  = "Inactive"


# ─────────────────────────────────────────────────────────
# NEW: WFH STATUS ENUM
# ─────────────────────────────────────────────────────────

class WFHStatusEnum(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


# ─────────────────────────────────────────────────────────
# BIOMETRIC DEVICE
# ─────────────────────────────────────────────────────────

class BiometricDevice(Base):
    __tablename__ = "biometric_devices"

    id             = Column(Integer, primary_key=True, index=True)
    vendor         = Column(SAEnum(VendorEnum), nullable=False)
    model_name     = Column(String(100), nullable=False)
    ip_address     = Column(String(45), unique=True, nullable=False, index=True)
    device_type    = Column(SAEnum(DeviceTypeEnum), nullable=False)
    status         = Column(SAEnum(DeviceStatusEnum), default=DeviceStatusEnum.Offline, nullable=False)
    health_percent = Column(Integer, default=100)
    employee_count = Column(Integer, default=0)
    last_sync      = Column(DateTime(timezone=True), nullable=True)
    auto_sync      = Column(Boolean, default=False)
    sdk_port       = Column(Integer, default=4370)
    comm_key       = Column(String(50), default="0")
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sync_logs = relationship("DeviceSyncLog", back_populates="device", cascade="all, delete-orphan")
    punches   = relationship("AttendancePunch", back_populates="biometric_device")

    def __repr__(self):
        return f"<BiometricDevice {self.vendor} {self.model_name} @ {self.ip_address}>"


# ─────────────────────────────────────────────────────────
# DEVICE SYNC LOG
# ─────────────────────────────────────────────────────────

class DeviceSyncLog(Base):
    __tablename__ = "device_sync_logs"

    id             = Column(Integer, primary_key=True, index=True)
    device_id      = Column(Integer, ForeignKey("biometric_devices.id", ondelete="CASCADE"), nullable=False)
    sync_type      = Column(SAEnum(SyncTypeEnum), default=SyncTypeEnum.manual)
    status         = Column(SAEnum(SyncStatusEnum), default=SyncStatusEnum.in_progress)
    records_synced = Column(Integer, default=0)
    error_message  = Column(Text, default="")
    started_at     = Column(DateTime(timezone=True), server_default=func.now())
    completed_at   = Column(DateTime(timezone=True), nullable=True)
    initiated_by   = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)

    device = relationship("BiometricDevice", back_populates="sync_logs")

    __table_args__ = (
        Index("ix_sync_logs_device_started", "device_id", "started_at"),
    )


# ─────────────────────────────────────────────────────────
# GEO LOCATION
# ─────────────────────────────────────────────────────────

class GeoLocation(Base):
    __tablename__ = "geo_locations"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(100), nullable=False)
    address        = Column(Text, default="")
    latitude       = Column(Numeric(10, 7), nullable=False)
    longitude      = Column(Numeric(10, 7), nullable=False)
    radius_meters  = Column(Integer, default=100)
    employee_count = Column(Integer, default=0)
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    punches = relationship("AttendancePunch", back_populates="geo_location")


# ─────────────────────────────────────────────────────────
# ATTENDANCE PUNCH
# ─────────────────────────────────────────────────────────

class AttendancePunch(Base):
    __tablename__ = "attendance_punches"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    employee_id         = Column(String(20), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    punch_time          = Column(DateTime(timezone=True), nullable=False, index=True)
    punch_type          = Column(SAEnum(PunchTypeEnum), nullable=False)
    capture_method      = Column(SAEnum(CaptureMethodEnum), nullable=False)

    biometric_device_id = Column(Integer, ForeignKey("biometric_devices.id", ondelete="SET NULL"), nullable=True)
    device_user_id      = Column(String(50), default="")

    geo_location_id     = Column(Integer, ForeignKey("geo_locations.id", ondelete="SET NULL"), nullable=True)
    latitude            = Column(Numeric(10, 7), nullable=True)
    longitude           = Column(Numeric(10, 7), nullable=True)
    gps_accuracy        = Column(Float, nullable=True)
    is_within_geofence  = Column(Boolean, nullable=True)

    selfie_path         = Column(String(500), nullable=True)
    ip_address          = Column(String(45), nullable=True)
    is_whitelisted_ip   = Column(Boolean, nullable=True)

    is_offline_record   = Column(Boolean, default=False)
    is_valid            = Column(Boolean, default=True)
    notes               = Column(Text, default="")
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    created_by          = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)

    employee         = relationship("Employee", back_populates="punches")
    biometric_device = relationship("BiometricDevice", back_populates="punches")
    geo_location     = relationship("GeoLocation", back_populates="punches")

    __table_args__ = (
        Index("ix_punch_employee_time", "employee_id", "punch_time"),
        Index("ix_punch_method", "capture_method"),
        Index("ix_punch_date", func.date("punch_time")),
    )


# ─────────────────────────────────────────────────────────
# ATTENDANCE RECORD
# ─────────────────────────────────────────────────────────

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id                      = Column(Integer, primary_key=True, index=True)
    employee_id             = Column(String(20), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    date                    = Column(Date, nullable=False, index=True)
    status                  = Column(SAEnum(AttendanceStatusEnum), default=AttendanceStatusEnum.absent)

    first_check_in          = Column(DateTime(timezone=True), nullable=True)
    last_check_out          = Column(DateTime(timezone=True), nullable=True)
    effective_hours         = Column(Numeric(5, 2), default=0)
    overtime_hours          = Column(Numeric(5, 2), default=0)
    break_duration_minutes  = Column(Integer, default=0)

    is_late                 = Column(Boolean, default=False)
    late_minutes            = Column(Integer, default=0)
    is_early_checkout       = Column(Boolean, default=False)
    is_regularized          = Column(Boolean, default=False)
    regularized_by          = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    regularization_reason   = Column(Text, default="")

    punch_count             = Column(Integer, default=0)
    capture_method          = Column(String(20), default="")

    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    employee = relationship("Employee", back_populates="attendance_records")

    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),
        Index("ix_attendance_status", "status"),
    )


# ─────────────────────────────────────────────────────────
# WHITELISTED IPs
# ─────────────────────────────────────────────────────────

class WhitelistedIP(Base):
    __tablename__ = "whitelisted_ips"

    id          = Column(Integer, primary_key=True, index=True)
    ip_address  = Column(String(45), unique=True, nullable=False)
    description = Column(String(200), default="")
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────────────────
# OFFLINE PUNCH QUEUE
# ─────────────────────────────────────────────────────────

class OfflinePunchQueue(Base):
    __tablename__ = "offline_punch_queue"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id    = Column(String(20), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    punch_time     = Column(DateTime(timezone=True), nullable=False)
    punch_type     = Column(SAEnum(PunchTypeEnum), nullable=False)
    capture_method = Column(SAEnum(CaptureMethodEnum), nullable=False)
    raw_data       = Column(JSONB, default={})
    status         = Column(SAEnum(OfflineStatusEnum), default=OfflineStatusEnum.pending, index=True)
    synced_at      = Column(DateTime(timezone=True), nullable=True)
    error_message  = Column(Text, default="")
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")


# ─────────────────────────────────────────────────────────
# ATTENDANCE SETTINGS
# ─────────────────────────────────────────────────────────

class AttendanceSettings(Base):
    __tablename__ = "attendance_settings"

    id                               = Column(Integer, primary_key=True, default=1)
    geo_fencing_enabled              = Column(Boolean, default=True)
    require_selfie                   = Column(Boolean, default=False)
    max_geo_radius                   = Column(Integer, default=500)
    work_start_time                  = Column(Time, default=time(9, 0))
    work_end_time                    = Column(Time, default=time(18, 0))
    break_duration_minutes           = Column(Integer, default=60)
    min_work_hours                   = Column(Numeric(4, 1), default=8.0)
    overtime_rate                    = Column(Numeric(4, 2), default=1.5)
    weekend_overtime_rate            = Column(Numeric(4, 2), default=2.0)
    holiday_overtime_rate            = Column(Numeric(4, 2), default=2.5)
    night_shift_bonus                = Column(Numeric(4, 2), default=0.25)
    overtime_daily_cap               = Column(Numeric(4, 1), default=4.0)
    overtime_weekly_cap              = Column(Numeric(5, 1), default=20.0)
    overtime_monthly_cap             = Column(Numeric(6, 1), default=80.0)
    night_shift_start                = Column(Time, default=time(22, 0))
    night_shift_end                  = Column(Time, default=time(6, 0))
    weekend_working                  = Column(Boolean, default=False)
    holiday_working                  = Column(Boolean, default=True)
    duplicate_punch_window_minutes   = Column(Integer, default=5)
    offline_mode_enabled             = Column(Boolean, default=True)
    auto_calculate_work_hours        = Column(Boolean, default=True)
    auto_first_in_last_out           = Column(Boolean, default=True)
    multiple_punch_handling          = Column(Boolean, default=True)
    late_threshold_minutes           = Column(Integer, default=15)
    early_checkout_threshold_minutes = Column(Integer, default=30)
    half_day_threshold_hours         = Column(Numeric(3, 1), default=4.0)
    short_leave_threshold_hours      = Column(Numeric(3, 1), default=2.0)
    auto_sync_enabled                = Column(Boolean, default=False)
    
    # Field Employee Settings (Settings tab — Field Employee Settings section)
    enable_field_tracking            = Column(Boolean, default=True)
    require_daily_reports            = Column(Boolean, default=True)
    auto_location_updates            = Column(Boolean, default=False)
    location_update_interval         = Column(String(20), default="30 minutes")
    max_field_radius_km              = Column(Integer, default=50)
    report_deadline                  = Column(Time, default=time(18, 0))
    spoofing_detection_enabled   = Column(Boolean, default=False)
    overtime_tracking_enabled    = Column(Boolean, default=True)
    auto_checkout_enabled        = Column(Boolean, default=False)
    checkin_reminder_enabled     = Column(Boolean, default=False)
    updated_at                       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by                       = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)


# ─────────────────────────────────────────────────────────
# NEW: FIELD EMPLOYEE  (GPS Mobile tab — Field Employee Management table)
# ─────────────────────────────────────────────────────────

class FieldEmployee(Base):
    __tablename__ = "field_employees"

    id            = Column(Integer, primary_key=True, index=True)
    employee_id   = Column(String(20), ForeignKey("employees.id", ondelete="CASCADE"),
                           nullable=False, unique=True)
    location      = Column(String(200), default="")
    latitude      = Column(Numeric(10, 7), nullable=True)
    longitude     = Column(Numeric(10, 7), nullable=True)
    status        = Column(SAEnum(FieldEmployeeStatusEnum),
                           default=FieldEmployeeStatusEnum.active)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(),
                           onupdate=func.now())

    employee = relationship("Employee")


# ─────────────────────────────────────────────────────────
# NEW: WFH REQUEST  (GPS Mobile tab — WFH Management panel)
# ─────────────────────────────────────────────────────────

class WFHRequest(Base):
    __tablename__ = "wfh_requests"

    id            = Column(Integer, primary_key=True, index=True)
    employee_id   = Column(String(20), ForeignKey("employees.id", ondelete="CASCADE"),
                           nullable=False)
    date          = Column(Date, nullable=False)
    reason        = Column(Text, default="")
    status        = Column(SAEnum(WFHStatusEnum), default=WFHStatusEnum.pending, index=True)
    approved_by   = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    approved_at   = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")

    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_wfh_employee_date"),
        Index("ix_wfh_status", "status"),
    )
