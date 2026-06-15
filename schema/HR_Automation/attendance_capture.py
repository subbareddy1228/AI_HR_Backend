from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress
from typing import Optional, List
from datetime import datetime, date, time
from enum import Enum




class BiometricVendor(str, Enum):
    ZKTECO = "ZKTeco"
    SUPREMA = "Suprema"
    BIOMAX = "Biomax"
    HIKVISION = "Hikvision"
    ESSL = "eSSL"
    VIRDI = "Virdi"
    OTHER = "Other"


class BiometricDeviceType(str, Enum):
    FINGERPRINT = "Fingerprint"
    FACE = "Face"
    IRIS = "Iris"
    RFID = "RFID"
    FACE_FINGERPRINT = "Face+Fingerprint"


class DeviceStatus(str, Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    ERROR = "Error"
    SYNCING = "Syncing"


class PunchType(str, Enum):
    CHECK_IN = "Check In"
    CHECK_OUT = "Check Out"
    BREAK_IN = "Break In"
    BREAK_OUT = "Break Out"
    OVERTIME_IN = "Overtime In"
    OVERTIME_OUT = "Overtime Out"


class AttendanceMethod(str, Enum):
    BIOMETRIC = "Biometric"
    GPS_MOBILE = "GPS Mobile"
    WEB_PORTAL = "Web Portal"
    MANUAL = "Manual"


class AttendanceStatus(str, Enum):
    PRESENT = "Present"
    ABSENT = "Absent"
    LATE = "Late"
    HALF_DAY = "Half Day"
    WFH = "Work From Home"
    FIELD = "Field"
    LEAVE = "Leave"
    HOLIDAY = "Holiday"




class BiometricDeviceCreate(BaseModel):
    vendor: BiometricVendor = BiometricVendor.ZKTECO
    device_type: BiometricDeviceType = BiometricDeviceType.FINGERPRINT
    model_name: str = Field(..., example="iClock 880")
    ip_address: str = Field(..., example="192.168.1.100")
    port: Optional[int] = 4370
    location_name: Optional[str] = None
    auto_sync: Optional[bool] = False


class BiometricDeviceUpdate(BaseModel):
    vendor: Optional[BiometricVendor] = None
    device_type: Optional[BiometricDeviceType] = None
    model_name: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    location_name: Optional[str] = None
    auto_sync: Optional[bool] = None
    is_active: Optional[bool] = None
    status: Optional[DeviceStatus] = None


class BiometricDeviceOut(BaseModel):
    id: int
    vendor: BiometricVendor
    device_type: BiometricDeviceType
    model_name: str
    ip_address: str
    port: Optional[int]
    location_name: Optional[str]
    status: DeviceStatus
    last_sync_at: Optional[datetime]
    auto_sync: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




class BiometricPunchSimulate(BaseModel):
    employee_id: int
    punch_type: PunchType = PunchType.CHECK_IN
    punch_time: Optional[datetime] = None      
    device_id: Optional[int] = None


class BiometricPunchOut(BaseModel):
    id: int
    device_id: int
    employee_id: int
    punch_time: datetime
    punch_type: PunchType
    is_simulated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




class DeviceSyncLogOut(BaseModel):
    id: int
    device_id: int
    sync_time: datetime
    status: str
    records_synced: int
    error_message: Optional[str]

    model_config = ConfigDict(from_attributes=True)




class GeoFenceCreate(BaseModel):
    location_name: str
    address: Optional[str] = None
    latitude: float
    longitude: float
    radius_meters: int = 100


class GeoFenceUpdate(BaseModel):
    location_name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: Optional[int] = None
    is_active: Optional[bool] = None


class GeoFenceOut(BaseModel):
    id: int
    location_name: str
    address: Optional[str]
    latitude: float
    longitude: float
    radius_meters: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GPSCheckInCreate(BaseModel):
    employee_id: int
    punch_type: PunchType = PunchType.CHECK_IN
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    device_info: Optional[str] = None


class GPSAttendanceOut(BaseModel):
    id: int
    employee_id: int
    punch_type: PunchType
    latitude: float
    longitude: float
    accuracy_meters: Optional[float]
    geo_fence_id: Optional[int]
    within_fence: bool
    punch_time: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class GPSStatsOut(BaseModel):
    today_checkins: int
    this_week_records: int
    pending: int
    offline: int
    avg_hours_today: float




class IPWhitelistCreate(BaseModel):
    ip_address: str = Field(..., example="192.168.1.1")
    label: Optional[str] = None


class IPWhitelistOut(BaseModel):
    id: int
    ip_address: str
    label: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




class WebCheckInCreate(BaseModel):
    employee_id: int
    punch_type: PunchType = PunchType.CHECK_IN
    attendance_type: Optional[str] = "Office"   
    webcam_snapshot_url: Optional[str] = None


class WebPortalAttendanceOut(BaseModel):
    id: int
    employee_id: int
    punch_type: PunchType
    ip_address: str
    is_whitelisted_ip: bool
    webcam_snapshot_url: Optional[str]
    punch_time: datetime
    attendance_type: str

    model_config = ConfigDict(from_attributes=True)




class DailyAttendanceOut(BaseModel):
    id: int
    employee_id: int
    attendance_date: date
    check_in_time: Optional[time]
    check_out_time: Optional[time]
    total_hours: float
    overtime_hours: float
    status: AttendanceStatus
    method: AttendanceMethod
    is_late: bool
    late_minutes: int
    early_checkout: bool
    shift_id: Optional[int]
    remarks: Optional[str]
    regularized: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




class AttendanceSettingsUpdate(BaseModel):
    
    geo_fencing_enabled: Optional[bool] = None
    require_selfie: Optional[bool] = None
    weekend_working: Optional[bool] = None
    holiday_working: Optional[bool] = None
    offline_mode: Optional[bool] = None
    auto_calculate_hours: Optional[bool] = None

    
    work_start_time: Optional[time] = None
    work_end_time: Optional[time] = None
    break_duration_minutes: Optional[int] = None
    overtime_rate: Optional[float] = None
    night_shift_start: Optional[time] = None
    night_shift_end: Optional[time] = None
    max_geo_radius_meters: Optional[int] = None
    duplicate_punch_window_minutes: Optional[int] = None

    
    late_arrival_threshold_minutes: Optional[int] = None
    early_checkout_threshold_minutes: Optional[int] = None
    half_day_leave_hours: Optional[float] = None
    short_leave_threshold_hours: Optional[float] = None

   
    field_tracking_enabled: Optional[bool] = None
    require_daily_reports: Optional[bool] = None
    auto_location_updates: Optional[bool] = None
    location_update_interval_minutes: Optional[int] = None
    max_field_radius_km: Optional[int] = None
    report_deadline_time: Optional[time] = None

   
    spoofing_detection: Optional[bool] = None
    checkin_reminder: Optional[bool] = None
    overtime_tracking: Optional[bool] = None
    auto_checkout: Optional[bool] = None


class AttendanceSettingsOut(BaseModel):
    id: int
    geo_fencing_enabled: bool
    require_selfie: bool
    weekend_working: bool
    holiday_working: bool
    offline_mode: bool
    auto_calculate_hours: bool
    work_start_time: Optional[time]
    work_end_time: Optional[time]
    break_duration_minutes: int
    overtime_rate: float
    night_shift_start: Optional[time]
    night_shift_end: Optional[time]
    max_geo_radius_meters: int
    duplicate_punch_window_minutes: int
    late_arrival_threshold_minutes: int
    early_checkout_threshold_minutes: int
    half_day_leave_hours: float
    short_leave_threshold_hours: float
    field_tracking_enabled: bool
    require_daily_reports: bool
    auto_location_updates: bool
    location_update_interval_minutes: int
    max_field_radius_km: int
    report_deadline_time: Optional[time]
    spoofing_detection: bool
    checkin_reminder: bool
    overtime_tracking: bool
    auto_checkout: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




class AttendanceDashboardSummary(BaseModel):
    total_records: int
    present_today: int
    late_arrivals: int
    overtime_hours: float
