from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date




class BiometricDeviceCreate(BaseModel):
    name:        str
    device_code: str
    location:    Optional[str] = None
    ip_address:  Optional[str] = None
    port:        int = 4370
    is_active:   bool = True

class BiometricDeviceUpdate(BaseModel):
    name:       Optional[str]  = None
    location:   Optional[str]  = None
    ip_address: Optional[str]  = None
    port:       Optional[int]  = None
    is_active:  Optional[bool] = None

class BiometricDeviceOut(BaseModel):
    id:          int
    name:        str
    device_code: str
    location:    Optional[str]
    ip_address:  Optional[str]
    port:        int
    is_active:   bool
    is_online:   bool
    last_sync_at: Optional[datetime]
    created_at:  datetime
    class Config:
        from_attributes = True



class DeviceSyncLogOut(BaseModel):
    id:             int
    device_id:      int
    status:         str
    records_synced: int
    error_msg:      Optional[str]
    synced_at:      datetime
    class Config:
        from_attributes = True




class BiometricPunchSimulate(BaseModel):
    device_id:   int
    employee_id: int
    punch_time:  Optional[datetime] = None
    punch_type:  str = "IN"   # IN | OUT

class BiometricPunchOut(BaseModel):
    id:          int
    device_id:   Optional[int]
    employee_id: int
    punch_time:  datetime
    punch_type:  str
    created_at:  datetime
    class Config:
        from_attributes = True




class GeoFenceCreate(BaseModel):
    name:          str
    latitude:      float
    longitude:     float
    radius_meters: float = 100.0
    is_active:     bool  = True

class GeoFenceUpdate(BaseModel):
    name:          Optional[str]   = None
    latitude:      Optional[float] = None
    longitude:     Optional[float] = None
    radius_meters: Optional[float] = None
    is_active:     Optional[bool]  = None

class GeoFenceOut(BaseModel):
    id:            int
    name:          str
    latitude:      float
    longitude:     float
    radius_meters: float
    is_active:     bool
    created_at:    datetime
    class Config:
        from_attributes = True



class GPSCheckInCreate(BaseModel):
    employee_id:  int
    latitude:     float
    longitude:    float
    punch_type:   str = "IN"
    geo_fence_id: Optional[int] = None

class GPSAttendanceOut(BaseModel):
    id:              int
    employee_id:     int
    geo_fence_id:    Optional[int]
    latitude:        float
    longitude:       float
    punch_time:      datetime
    punch_type:      str
    ip_address:      Optional[str]
    is_within_fence: bool
    class Config:
        from_attributes = True

class GPSStatsOut(BaseModel):
    total_checkins:      int
    within_fence:        int
    outside_fence:       int
    fence_compliance_pct: float



class IPWhitelistCreate(BaseModel):
    ip_address: str
    label:      Optional[str] = None
    is_active:  bool = True

class IPWhitelistOut(BaseModel):
    id:         int
    ip_address: str
    label:      Optional[str]
    is_active:  bool
    created_at: datetime
    class Config:
        from_attributes = True



class WebCheckInCreate(BaseModel):
    employee_id: int
    punch_type:  str = "IN"  
    is_wfh:      bool = False

class WebPortalAttendanceOut(BaseModel):
    id:          int
    employee_id: int
    punch_time:  datetime
    punch_type:  str
    ip_address:  Optional[str]
    is_wfh:      bool
    created_at:  datetime
    class Config:
        from_attributes = True




class DailyAttendanceOut(BaseModel):
    id:          int
    employee_id: int
    att_date:    date
    status:      str
    first_in:    Optional[datetime]
    last_out:    Optional[datetime]
    total_hours: float
    is_late:     bool
    class Config:
        from_attributes = True




class AttendanceSettingsUpdate(BaseModel):
    grace_minutes:         Optional[int]   = None
    half_day_hours:        Optional[float] = None
    full_day_hours:        Optional[float] = None
    allow_gps:             Optional[bool]  = None
    allow_web:             Optional[bool]  = None
    allow_biometric:       Optional[bool]  = None
    ip_restriction:        Optional[bool]  = None
    geo_fence_restriction: Optional[bool]  = None

class AttendanceSettingsOut(BaseModel):
    id:                    int
    grace_minutes:         int
    half_day_hours:        float
    full_day_hours:        float
    allow_gps:             bool
    allow_web:             bool
    allow_biometric:       bool
    ip_restriction:        bool
    geo_fence_restriction: bool
    class Config:
        from_attributes = True


class AttendanceDashboardSummary(BaseModel):
    total_employees:   int
    present_today:     int
    absent_today:      int
    wfh_today:         int
    late_today:        int
    biometric_punches: int
    gps_checkins:      int
    web_checkins:      int