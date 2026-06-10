"""
schemas/attendance.py
Pydantic v2 request / response schemas — matches the FastAPI + PostgreSQL stack.
"""

from __future__ import annotations
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, IPvAnyAddress, field_validator, model_validator

from model.HR_Automation.attendance_capture import (
    DeviceTypeEnum, DeviceStatusEnum, VendorEnum,
    PunchTypeEnum, CaptureMethodEnum, AttendanceStatusEnum,
    SyncStatusEnum, SyncTypeEnum, OfflineStatusEnum,
)


# ─────────────────────────────────────────────────────────
# BIOMETRIC DEVICE
# ─────────────────────────────────────────────────────────

class DeviceCreate(BaseModel):
    vendor:      VendorEnum
    model_name:  str        = Field(..., max_length=100)
    ip_address:  str        = Field(..., description="Device LAN IP, e.g. 192.168.1.100")
    device_type: DeviceTypeEnum
    sdk_port:    int        = Field(4370, ge=1, le=65535)
    comm_key:    str        = Field("0", max_length=50)
    auto_sync:   bool       = False


class DeviceUpdate(BaseModel):
    model_name:  Optional[str]            = None
    device_type: Optional[DeviceTypeEnum] = None
    sdk_port:    Optional[int]            = None
    comm_key:    Optional[str]            = None
    auto_sync:   Optional[bool]           = None
    is_active:   Optional[bool]           = None


class SyncLogOut(BaseModel):
    id:             int
    device_id:      int
    sync_type:      SyncTypeEnum
    status:         SyncStatusEnum
    records_synced: int
    error_message:  str
    started_at:     datetime
    completed_at:   Optional[datetime]

    model_config = {"from_attributes": True}


class DeviceOut(BaseModel):
    id:             int
    vendor:         VendorEnum
    model_name:     str
    ip_address:     str
    device_type:    DeviceTypeEnum
    status:         DeviceStatusEnum
    health_percent: int
    employee_count: int
    last_sync:      Optional[datetime]
    auto_sync:      bool
    is_active:      bool
    created_at:     datetime
    # aggregates (populated by service)
    total_punches:  int = 0
    check_ins:      int = 0
    check_outs:     int = 0
    recent_syncs:   List[SyncLogOut] = []

    model_config = {"from_attributes": True}


class DeviceStatusDashboard(BaseModel):
    total:   int
    online:  int
    offline: int
    syncing: int
    error:   int


# ─────────────────────────────────────────────────────────
# GEO LOCATION
# ─────────────────────────────────────────────────────────

class GeoLocationCreate(BaseModel):
    name:          str     = Field(..., max_length=100)
    address:       str     = ""
    latitude:      Decimal = Field(..., ge=-90, le=90)
    longitude:     Decimal = Field(..., ge=-180, le=180)
    radius_meters: int     = Field(100, ge=10, le=5000)


class GeoLocationOut(BaseModel):
    id:             int
    name:           str
    address:        str
    latitude:       Decimal
    longitude:      Decimal
    radius_meters:  int
    employee_count: int
    is_active:      bool
    created_at:     datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# PUNCH REQUESTS
# ─────────────────────────────────────────────────────────

class BiometricPunchIn(BaseModel):
    """Simulate / receive a biometric punch from device or UI."""
    employee_id:       str         = Field(..., description="Employee ID, e.g. EMP001")
    punch_type:        PunchTypeEnum
    device_id:         int
    punch_time:        Optional[datetime] = None   # defaults to now server-side
    device_user_id:    str         = ""
    is_offline_record: bool        = False


class GPSPunchIn(BaseModel):
    employee_id: str
    punch_type:  PunchTypeEnum = Field(..., description="check_in or check_out")
    latitude:    Decimal       = Field(..., ge=-90, le=90)
    longitude:   Decimal       = Field(..., ge=-180, le=180)
    gps_accuracy: Optional[float] = None
    punch_time:  Optional[datetime] = None

    @field_validator("punch_type")
    @classmethod
    def gps_punch_type_must_be_checkin_out(cls, v):
        if v not in (PunchTypeEnum.check_in, PunchTypeEnum.check_out):
            raise ValueError("GPS punches support only check_in / check_out")
        return v


class WebPunchIn(BaseModel):
    employee_id: str
    punch_type:  PunchTypeEnum
    punch_time:  Optional[datetime] = None
    # selfie handled as UploadFile in the router


class PunchOut(BaseModel):
    id:                 UUID
    employee_id:        str
    punch_time:         datetime
    punch_type:         PunchTypeEnum
    capture_method:     CaptureMethodEnum
    biometric_device_id: Optional[int]
    geo_location_id:    Optional[int]
    latitude:           Optional[Decimal]
    longitude:          Optional[Decimal]
    is_within_geofence: Optional[bool]
    ip_address:         Optional[str]
    is_whitelisted_ip:  Optional[bool]
    is_offline_record:  bool
    is_valid:           bool
    notes:              str
    created_at:         datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# ATTENDANCE RECORD
# ─────────────────────────────────────────────────────────

class AttendanceRecordOut(BaseModel):
    id:                     int
    employee_id:            str
    date:                   date
    status:                 AttendanceStatusEnum
    first_check_in:         Optional[datetime]
    last_check_out:         Optional[datetime]
    effective_hours:        Decimal
    overtime_hours:         Decimal
    break_duration_minutes: int
    is_late:                bool
    late_minutes:           int
    is_early_checkout:      bool
    is_regularized:         bool
    regularization_reason:  str
    punch_count:            int
    capture_method:         str
    created_at:             datetime
    updated_at:             datetime

    model_config = {"from_attributes": True}


class AttendanceRecordWithEmployee(AttendanceRecordOut):
    employee_name:  str = ""
    department:     str = ""


# ─────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────

class AttendanceDashboard(BaseModel):
    total_records:   int
    present_today:   int
    late_arrivals:   int
    overtime_hours:  Decimal
    absent_today:    int
    on_leave_today:  int
    device_status:   DeviceStatusDashboard


# ─────────────────────────────────────────────────────────
# DEVICE REPORT
# ─────────────────────────────────────────────────────────

class DeviceReport(BaseModel):
    device_id:      int
    model_name:     str
    vendor:         str
    ip_address:     str
    total_punches:  int
    check_ins:      int
    check_outs:     int
    employees:      int
    health_percent: int
    status:         str
    last_sync:      Optional[datetime]


# ─────────────────────────────────────────────────────────
# SYNC ACTIONS
# ─────────────────────────────────────────────────────────

class SyncAllResponse(BaseModel):
    devices_triggered: int
    logs:              List[SyncLogOut]


class ReconnectResponse(BaseModel):
    reconnected_count: int
    device_ids:        List[int]


class OfflineSyncResponse(BaseModel):
    synced: int
    failed: int


# ─────────────────────────────────────────────────────────
# WHITELISTED IP
# ─────────────────────────────────────────────────────────

class WhitelistedIPCreate(BaseModel):
    ip_address:  str = Field(..., max_length=45)
    description: str = ""


class WhitelistedIPOut(BaseModel):
    id:          int
    ip_address:  str
    description: str
    is_active:   bool
    created_at:  datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────

class AttendanceSettingsOut(BaseModel):
    geo_fencing_enabled:              bool
    require_selfie:                   bool
    max_geo_radius:                   int
    work_start_time:                  time
    work_end_time:                    time
    break_duration_minutes:           int
    min_work_hours:                   Decimal
    overtime_rate:                    Decimal
    weekend_overtime_rate:            Decimal
    holiday_overtime_rate:            Decimal
    night_shift_bonus:                Decimal
    overtime_daily_cap:               Decimal
    overtime_weekly_cap:              Decimal
    overtime_monthly_cap:             Decimal
    night_shift_start:                time
    night_shift_end:                  time
    weekend_working:                  bool
    holiday_working:                  bool
    duplicate_punch_window_minutes:   int
    offline_mode_enabled:             bool
    auto_calculate_work_hours:        bool
    auto_first_in_last_out:           bool
    multiple_punch_handling:          bool
    late_threshold_minutes:           int
    early_checkout_threshold_minutes: int
    half_day_threshold_hours:         Decimal
    short_leave_threshold_hours:      Decimal
    auto_sync_enabled:                bool
    updated_at:                       datetime

    model_config = {"from_attributes": True}


class AttendanceSettingsUpdate(BaseModel):
    geo_fencing_enabled:              Optional[bool]    = None
    require_selfie:                   Optional[bool]    = None
    max_geo_radius:                   Optional[int]     = None
    work_start_time:                  Optional[time]    = None
    work_end_time:                    Optional[time]    = None
    break_duration_minutes:           Optional[int]     = None
    min_work_hours:                   Optional[Decimal] = None
    overtime_rate:                    Optional[Decimal] = None
    weekend_overtime_rate:            Optional[Decimal] = None
    holiday_overtime_rate:            Optional[Decimal] = None
    night_shift_bonus:                Optional[Decimal] = None
    overtime_daily_cap:               Optional[Decimal] = None
    overtime_weekly_cap:              Optional[Decimal] = None
    overtime_monthly_cap:             Optional[Decimal] = None
    night_shift_start:                Optional[time]    = None
    night_shift_end:                  Optional[time]    = None
    weekend_working:                  Optional[bool]    = None
    holiday_working:                  Optional[bool]    = None
    duplicate_punch_window_minutes:   Optional[int]     = None
    offline_mode_enabled:             Optional[bool]    = None
    auto_calculate_work_hours:        Optional[bool]    = None
    auto_first_in_last_out:           Optional[bool]    = None
    multiple_punch_handling:          Optional[bool]    = None
    late_threshold_minutes:           Optional[int]     = None
    early_checkout_threshold_minutes: Optional[int]     = None
    half_day_threshold_hours:         Optional[Decimal] = None
    short_leave_threshold_hours:      Optional[Decimal] = None
    auto_sync_enabled:                Optional[bool]    = None


# ─────────────────────────────────────────────────────────
# GENERIC
# ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str

class PaginatedResponse(BaseModel):
    total:   int
    page:    int
    size:    int
    items:   list
