from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, time, datetime
from enum import Enum




class PunchSource(str, Enum):
    REMOTE          = "Remote"
    SELFIE          = "Selfie"
    WEB_CHAT        = "Web/Chat"
    QR_SCAN         = "QR Scan"
    BIOMETRIC_FETCH = "Biometric Fetch"
    BIOMETRIC_SYNC  = "Biometric Sync"
    MANUAL          = "Manual"
    EXCEL_IMPORT    = "Excel Import"
    MISSED          = "Missed"
    TIME_RELAX      = "Time Relax"
    TRAVEL          = "Travel"
    API             = "API"


class PunchProcessStatus(str, Enum):
    PROCESSED = "Processed"
    PENDING   = "Pending"


class AttendanceMark(str, Enum):
    PRESENT  = "P"
    ABSENT   = "A"
    LATE     = "L"
    HALF_DAY = "H"
    WFH      = "W"
    LEAVE    = "LV"
    HOLIDAY  = "HOL"


class PunchType(str, Enum):
    IN  = "IN"
    OUT = "OUT"




class DailyPunchCreate(BaseModel):
   
    employee_id:    int
    employee_code:  Optional[str]  = None
    punch_date:     date
    punch_time:     time
    punch_type:     PunchType      = PunchType.IN
    source:         PunchSource    = PunchSource.MANUAL
    latitude:       Optional[float] = None
    longitude:      Optional[float] = None
    location_tag:   Optional[str]  = None
    photo_url:      Optional[str]  = None
    business_unit:  Optional[str]  = None
    location_name:  Optional[str]  = None
    cost_center:    Optional[str]  = None
    department:     Optional[str]  = None
    remarks:        Optional[str]  = None


class DailyPunchUpdate(BaseModel):
   
    punch_time:     Optional[time]         = None
    punch_type:     Optional[PunchType]    = None
    source:         Optional[PunchSource]  = None
    latitude:       Optional[float]        = None
    longitude:      Optional[float]        = None
    photo_url:      Optional[str]          = None
    remarks:        Optional[str]          = None
    is_regularized: Optional[bool]         = None
    process_status: Optional[PunchProcessStatus] = None


class DailyPunchOut(BaseModel):
    id:             int
    employee_id:    int
    employee_code:  Optional[str]
    punch_date:     date
    punch_time:     time
    punch_datetime: datetime
    punch_type:     str
    source:         PunchSource
    latitude:       Optional[float]
    longitude:      Optional[float]
    location_tag:   Optional[str]
    photo_url:      Optional[str]
    process_status: PunchProcessStatus
    business_unit:  Optional[str]
    location_name:  Optional[str]
    cost_center:    Optional[str]
    department:     Optional[str]
    remarks:        Optional[str]
    is_regularized: bool
    created_at:     datetime

    model_config = ConfigDict(from_attributes=True)



class PunchInfo(BaseModel):
    
    time:       Optional[str]              
    source:     Optional[PunchSource]
    has_photo:  bool = False
    has_gps:    bool = False
    photo_url:  Optional[str] = None
    latitude:   Optional[float] = None
    longitude:  Optional[float] = None


class DailyPunchSummaryOut(BaseModel):
    
    sn:               int                        
    employee_id:      int
    employee_name:    str
    employee_code:    Optional[str]
    designation:      Optional[str]
    summary_date:     date
    start:            PunchInfo                 
    end:              PunchInfo                  
    duration:         str                        
    duration_minutes: int
    attendance_mark:  AttendanceMark
    is_late:          bool
    has_no_punch:     bool
    process_status:   PunchProcessStatus
    department:       Optional[str]
    business_unit:    Optional[str]
    location_name:    Optional[str]
    cost_center:      Optional[str]

    model_config = ConfigDict(from_attributes=True)



class DailyPunchesFilter(BaseModel):
    
    punch_date:     date                        = Field(default_factory=date.today)
    employee_id:    Optional[int]               = None   
    business_unit:  Optional[str]               = None   
    location:       Optional[str]               = None   
    cost_center:    Optional[str]               = None  
    department:     Optional[str]               = None   

    
    late_only:      bool = False    
    absent_only:    bool = False    
    no_punches:     bool = False   
    

    
    page:           int  = 1
    page_size:      int  = 20




class PaginatedDailyPunchesResponse(BaseModel):
    total:      int
    page:       int
    page_size:  int
    pages:      int
    items:      List[DailyPunchSummaryOut]




class ManualPunchCreate(BaseModel):
    employee_id: int
    punch_date:  date
    punch_time:  time
    punch_type:  PunchType   = PunchType.IN
    remarks:     Optional[str] = None




class RegularisePunch(BaseModel):
    punch_id:      int
    new_time:      time
    reason:        str
    approved_by:   Optional[int] = None  
