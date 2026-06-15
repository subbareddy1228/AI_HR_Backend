from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text
from core.database import Base


class BiometricDevice(Base):
    __tablename__ = "biometric_devices"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(200), nullable=False)
    device_code  = Column(String(100), unique=True, nullable=False)
    location     = Column(String(200))
    ip_address   = Column(String(50))
    port         = Column(Integer, default=4370)
    is_active    = Column(Boolean, default=True)
    is_online    = Column(Boolean, default=False)
    last_sync_at = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeviceSyncLog(Base):
    __tablename__ = "device_sync_logs"

    id          = Column(Integer, primary_key=True, index=True)
    device_id   = Column(Integer, ForeignKey("biometric_devices.id", ondelete="CASCADE"))
    status      = Column(String(50), default="success")   
    records_synced = Column(Integer, default=0)
    error_msg   = Column(Text, nullable=True)
    synced_at   = Column(DateTime, default=datetime.utcnow)


class BiometricPunch(Base):
    __tablename__ = "biometric_punches"

    id          = Column(Integer, primary_key=True, index=True)
    device_id   = Column(Integer, ForeignKey("biometric_devices.id", ondelete="SET NULL"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))
    punch_time  = Column(DateTime, nullable=False)
    punch_type  = Column(String(20), default="IN")   
    created_at  = Column(DateTime, default=datetime.utcnow)


class GeoFence(Base):
    __tablename__ = "geo_fences"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    latitude    = Column(Float, nullable=False)
    longitude   = Column(Float, nullable=False)
    radius_meters = Column(Float, default=100.0)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GPSAttendance(Base):
    __tablename__ = "gps_attendance"

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))
    geo_fence_id = Column(Integer, ForeignKey("geo_fences.id", ondelete="SET NULL"), nullable=True)
    latitude     = Column(Float, nullable=False)
    longitude    = Column(Float, nullable=False)
    punch_time   = Column(DateTime, default=datetime.utcnow)
    punch_type   = Column(String(20), default="IN")
    ip_address   = Column(String(50))
    is_within_fence = Column(Boolean, default=False)


class IPWhitelist(Base):
    __tablename__ = "ip_whitelist"

    id          = Column(Integer, primary_key=True, index=True)
    ip_address  = Column(String(50), unique=True, nullable=False)
    label       = Column(String(200))
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)


class WebPortalAttendance(Base):
    __tablename__ = "web_portal_attendance"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))
    punch_time  = Column(DateTime, default=datetime.utcnow)
    punch_type  = Column(String(20), default="IN")   
    ip_address  = Column(String(50))
    is_wfh      = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


class DailyAttendance(Base):
    __tablename__ = "daily_attendance"

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))
    att_date     = Column(Date, nullable=False)
    status       = Column(String(50), default="Present")  
    first_in     = Column(DateTime, nullable=True)
    last_out     = Column(DateTime, nullable=True)
    total_hours  = Column(Float, default=0.0)
    is_late      = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AttendanceSettings(Base):
    __tablename__ = "attendance_settings"

    id                    = Column(Integer, primary_key=True, index=True)
    grace_minutes         = Column(Integer, default=10)
    half_day_hours        = Column(Float, default=4.0)
    full_day_hours        = Column(Float, default=8.0)
    allow_gps             = Column(Boolean, default=True)
    allow_web             = Column(Boolean, default=True)
    allow_biometric       = Column(Boolean, default=True)
    ip_restriction        = Column(Boolean, default=False)
    geo_fence_restriction = Column(Boolean, default=False)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)