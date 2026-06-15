from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class AttendanceMark(str, Enum):
    present   = "Present"
    absent    = "Absent"
    half_day  = "Half Day"
    wfh       = "WFH"
    holiday   = "Holiday"
    weekend   = "Weekend"
    on_leave  = "On Leave"


class ProcessStatus(str, Enum):
    pending   = "Pending"
    processed = "Processed"


class PunchTime(BaseModel):
    time: Optional[str] = None   




class DailyPunchCreate(BaseModel):
    employee_id: int
    punch_date:  date
    punch_time:  datetime
    punch_type:  str = "IN"   


class DailyPunchUpdate(BaseModel):
    punch_time:  Optional[datetime] = None
    punch_type:  Optional[str]      = None


class ManualPunchCreate(BaseModel):
    employee_id: int
    punch_date:  date
    in_time:     Optional[str] = None   
    out_time:    Optional[str] = None
    reason:      Optional[str] = None


class RegularisePunch(BaseModel):
    employee_id:  int
    punch_date:   date
    in_time:      Optional[str] = None
    out_time:     Optional[str] = None
    reason:       str




class DailyPunchesFilter(BaseModel):
    punch_date:    date
    employee_id:   Optional[int] = None
    business_unit: Optional[str] = None
    location:      Optional[str] = None
    cost_center:   Optional[str] = None
    department:    Optional[str] = None
    late_only:     bool = False
    absent_only:   bool = False
    no_punches:    bool = False
    page:          int  = 1
    page_size:     int  = 20




class DailyPunchOut(BaseModel):
    id:              int
    sn:              int = 0
    employee_id:     int
    employee_name:   Optional[str] = None
    employee_code:   Optional[str] = None
    designation:     Optional[str] = None
    department:      Optional[str] = None
    business_unit:   Optional[str] = None
    location_name:   Optional[str] = None
    cost_center:     Optional[str] = None
    summary_date:    date
    start:           PunchTime = PunchTime()
    end:             PunchTime = PunchTime()
    duration:        str = "0h 0m"
    attendance_mark: AttendanceMark = AttendanceMark.absent
    is_late:         bool = False
    process_status:  ProcessStatus = ProcessStatus.pending

    class Config:
        from_attributes = True


class PaginatedDailyPunchesResponse(BaseModel):
    total:     int
    page:      int
    page_size: int
    items:     List[DailyPunchOut]