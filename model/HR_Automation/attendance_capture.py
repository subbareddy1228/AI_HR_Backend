from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Date, Time, Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime
import enum




class BiometricVendor(str, enum.Enum):
    ZKTECO = "ZKTeco"
    SUPREMA = "Suprema"
    BIOMAX = "Biomax"
    HIKVISION = "Hikvision"
    ESSL = "eSSL"
    VIRDI = "Virdi"
    OTHER = "Other"


class BiometricDeviceType(str, enum.Enum):
    FINGERPRINT = "Fingerprint"
    FACE = "Face"
    IRIS = "Iris"
    RFID = "RFID"
    FACE_FINGERPRINT = "Face+Fingerprint"


class DeviceStatus(str, enum.Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    ERROR = "Error"
    SYNCING = "Syncing"


class PunchType(str, enum.Enum):
    CHECK_IN = "Check In"
    CHECK_OUT = "Check Out"
    BREAK_IN = "Break In"
    BREAK_OUT = "Break Out"
    OVERTIME_IN = "Overtime In"
    OVERTIME_OUT = "Overtime Out"


class AttendanceMethod(str, enum.Enum):
    BIOMETRIC = "Biometric"
    GPS_MOBILE = "GPS Mobile"
    WEB_PORTAL = "Web Portal"
    MANUAL = "Manual"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "Present"
    ABSENT = "Absent"
    LATE = "Late"
    HALF_DAY = "Half Day"
    WFH = "Work From Home"
    FIELD = "Field"
    LEAVE = "Leave"
    HOLIDAY = "Holiday"




class BiometricDevice(Base):
    
    __tablename__ = "biometric_devices"

    id = Column(Integer, primary_key=True, index=True)
    vendor = Column(SAEnum(BiometricVendor), nullable=False, default=BiometricVendor.ZKTECO)
    device_type = Column(SAEnum(BiometricDeviceType), nullable=False, default=BiometricDeviceType.FINGERPRINT)
    model_name = Column(String(150), nullable=False)
    ip_address = Column(String(45), nullable=False)        
    port = Column(Integer, default=4370)
    location_name = Column(String(200), nullable=True)       
    status = Column(SAEnum(DeviceStatus), default=DeviceStatus.OFFLINE)
    last_sync_at = Column(DateTime, nullable=True)
    auto_sync = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    punches = relationship("BiometricPunch", back_populates="device", cascade="all, delete-orphan")
    sync_logs = relationship("DeviceSyncLog", back_populates="device", cascade="all, delete-orphan")




class BiometricPunch(Base):
    
    __tablename__ = "biometric_punches"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("biometric_devices.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employee_master.id"), nullable=False)
    punch_time = Column(DateTime, nullable=False)
    punch_type = Column(SAEnum(PunchType), default=PunchType.CHECK_IN)
    is_simulated = Column(Boolean, default=False)           
    raw_data = Column(Text, nullable=True)                   
    created_at = Column(DateTime, default=datetime.utcnow)

    device = relationship("BiometricDevice", back_populates="punches")




class DeviceSyncLog(Base):
    
    __tablename__ = "device_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("biometric_devices.id"), nullable=False)
    sync_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), nullable=False)              
    records_synced = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    device = relationship("BiometricDevice", back_populates="sync_logs")




class GeoFenceLocation(Base):
    
    __tablename__ = "geo_fence_locations"

    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(200), nullable=False)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Integer, default=100)            
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)




class GPSAttendance(Base):
    
    __tablename__ = "gps_attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employee_master.id"), nullable=False)
    punch_type = Column(SAEnum(PunchType), nullable=False, default=PunchType.CHECK_IN)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=True)
    geo_fence_id = Column(Integer, ForeignKey("geo_fence_locations.id"), nullable=True)
    within_fence = Column(Boolean, default=False)
    punch_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    device_info = Column(String(255), nullable=True)         
    created_at = Column(DateTime, default=datetime.utcnow)




class IPWhitelist(Base):
    
    __tablename__ = "ip_whitelist"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), nullable=False, unique=True)
    label = Column(String(100), nullable=True)               
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WebPortalAttendance(Base):
    
    __tablename__ = "web_portal_attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employee_master.id"), nullable=False)
    punch_type = Column(SAEnum(PunchType), nullable=False, default=PunchType.CHECK_IN)
    ip_address = Column(String(45), nullable=False)
    is_whitelisted_ip = Column(Boolean, default=False)
    webcam_snapshot_url = Column(String(500), nullable=True)  
    punch_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    attendance_type = Column(String(50), default="Office")   
    created_at = Column(DateTime, default=datetime.utcnow)




class DailyAttendance(Base):
    
    __tablename__ = "daily_attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employee_master.id"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    check_in_time = Column(Time, nullable=True)
    check_out_time = Column(Time, nullable=True)
    total_hours = Column(Float, default=0.0)
    overtime_hours = Column(Float, default=0.0)
    status = Column(SAEnum(AttendanceStatus), default=AttendanceStatus.ABSENT)
    method = Column(SAEnum(AttendanceMethod), default=AttendanceMethod.MANUAL)
    is_late = Column(Boolean, default=False)
    late_minutes = Column(Integer, default=0)
    early_checkout = Column(Boolean, default=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)
    remarks = Column(Text, nullable=True)
    regularized = Column(Boolean, default=False)
    regularized_by = Column(Integer, nullable=True)   
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)




class AttendanceSettings(Base):
    
    __tablename__ = "attendance_settings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=True)              

    
    geo_fencing_enabled = Column(Boolean, default=True)
    require_selfie = Column(Boolean, default=False)
    weekend_working = Column(Boolean, default=False)
    holiday_working = Column(Boolean, default=False)
    offline_mode = Column(Boolean, default=True)
    auto_calculate_hours = Column(Boolean, default=True)

    
    work_start_time = Column(Time, nullable=True)            
    work_end_time = Column(Time, nullable=True)              
    break_duration_minutes = Column(Integer, default=60)
    overtime_rate = Column(Float, default=1.5)
    night_shift_start = Column(Time, nullable=True)          
    night_shift_end = Column(Time, nullable=True)            
    max_geo_radius_meters = Column(Integer, default=500)
    duplicate_punch_window_minutes = Column(Integer, default=5)

    
    late_arrival_threshold_minutes = Column(Integer, default=15)
    early_checkout_threshold_minutes = Column(Integer, default=30)
    half_day_leave_hours = Column(Float, default=4.0)
    short_leave_threshold_hours = Column(Float, default=2.0)

    
    field_tracking_enabled = Column(Boolean, default=True)
    require_daily_reports = Column(Boolean, default=True)
    auto_location_updates = Column(Boolean, default=False)
    location_update_interval_minutes = Column(Integer, default=30)
    max_field_radius_km = Column(Integer, default=50)
    report_deadline_time = Column(Time, nullable=True)       

    
    spoofing_detection = Column(Boolean, default=False)
    checkin_reminder = Column(Boolean, default=True)
    overtime_tracking = Column(Boolean, default=True)
    auto_checkout = Column(Boolean, default=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
