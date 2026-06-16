from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime



class DailyAttendanceCreate(BaseModel):
    
    employee_id:      int
    att_date:         date
    status:           str  = "Present"   
    remarks:          Optional[str] = None
    shift_name:       Optional[str] = "General"
    check_in:         Optional[str] = None  
    check_in_source:  Optional[str] = None   
    check_out:        Optional[str] = None  
    check_out_source: Optional[str] = None
    is_late:          bool = False
    is_half_day:      bool = False


class DailyAttendanceUpdate(BaseModel):
    
    status:           Optional[str] = None
    remarks:          Optional[str] = None
    shift_name:       Optional[str] = None
    check_in:         Optional[str] = None
    check_in_source:  Optional[str] = None
    check_out:        Optional[str] = None
    check_out_source: Optional[str] = None
    is_late:          Optional[bool] = None
    is_half_day:      Optional[bool] = None


class UploadAttendanceRow(BaseModel):
    
    employee_code:    str
    att_date:         date
    check_in:         Optional[str] = None
    check_out:        Optional[str] = None
    check_in_source:  Optional[str] = "Manual"
    check_out_source: Optional[str] = "Manual"


class BulkUploadPayload(BaseModel):
    rows: List[UploadAttendanceRow]




class DailyAttendanceFilter(BaseModel):
    att_date:      date
    business_unit: Optional[str] = None   
    location:      Optional[str] = None  
    cost_center:   Optional[str] = None   
    department:    Optional[str] = None   
    employee_id:   Optional[int] = None   
    late_only:     bool = False           
    absent_only:   bool = False           
    no_punches:    bool = False            
    page:          int  = 1
    page_size:     int  = 20




class ShiftTimeline(BaseModel):
    
    shift_name:  str = "General"
    shift_start: str = "03:00A"    
    shift_end:   str = "12:00A"   
    work_start:  str = "09:00A"    
    work_end:    str = "06:00P"    


class DailyAttendanceOut(BaseModel):
    id:               int
    employee_id:      int
    employee_name:    str
    employee_code:    str
    designation:      Optional[str]
    department:       Optional[str]
    location:         Optional[str]
    att_date:         date
    status:           str
    remarks:          Optional[str]
    shift_name:       Optional[str]
    check_in:         Optional[str]
    check_in_source:  Optional[str]
    check_out:        Optional[str]
    check_out_source: Optional[str]
    worked_hours:     float
    in_time_display:  str = "0 h 0 m"  
    is_late:          bool
    is_half_day:      bool
    timeline:         ShiftTimeline

    model_config = ConfigDict(from_attributes=True)


class PaginatedDailyAttendance(BaseModel):
    total:     int
    page:      int
    page_size: int
    items:     List[DailyAttendanceOut]


class FilterOptions(BaseModel):

    business_units: List[str]
    locations:      List[str]
    cost_centers:   List[str]
    departments:    List[str]


class DownloadRow(BaseModel):
    employee_code: str
    employee_name: str
    designation:   Optional[str]
    department:    Optional[str]
    location:      Optional[str]
    att_date:      str
    status:        str
    check_in:      Optional[str]
    check_out:     Optional[str]
    worked_hours:  float
    is_late:       bool