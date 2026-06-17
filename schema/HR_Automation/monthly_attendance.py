
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict
from datetime import date


DAY_CODE_MAP = {
    "P":  {"label": "Present",           "leave_code": "LV454"},
    "A":  {"label": "Absent",            "leave_code": "LV455"},
    "H":  {"label": "Holiday",           "leave_code": "LV456"},
    "W":  {"label": "Week Off",          "leave_code": "LV457"},
    "CO": {"label": "Comp Off",          "leave_code": "LV458"},
    "CL": {"label": "Casual Leave",      "leave_code": "LV459"},
    "LW": {"label": "Leave without Pay", "leave_code": "LV1055"},
    "SL": {"label": "Sick Leave",        "leave_code": "LV2638"},
    "HD": {"label": "Half Day",          "leave_code": "LV2640"},
}


class EmployeeProfileCard(BaseModel):
    employee_id:    int
    employee_code:  str
    employee_name:  str
    date_of_joining: Optional[date]
    date_of_exit:   Optional[date]
    location:       Optional[str]
    department:     Optional[str]
    designation:    Optional[str]
    default_shift:  Optional[str]


class CalendarDayOut(BaseModel):
    date:        date
    day_number:  int           
    weekday:     str         
    day_code:    str           
    status:      str           
    leave_code:  Optional[str] 
    has_punch:   bool
    check_in:    Optional[str]
    check_out:   Optional[str]
    worked_hours: float
    is_late:     bool
    is_weekend:  bool
    is_holiday:  bool


class MonthlyCalendarOut(BaseModel):
    employee:    EmployeeProfileCard
    month:       int
    year:        int
    month_label: str             
    days:        List[CalendarDayOut]

    total_present:  int
    total_absent:   int
    total_holiday:  int
    total_week_off: int
    total_half_day: int
    total_leave:    int
    total_working_days: int


class MonthlyAttendanceFilter(BaseModel):
    month:         int
    year:          int
    employee_id:   Optional[int] = None
    business_unit: Optional[str] = None
    location:      Optional[str] = None
    cost_center:   Optional[str] = None
    department:    Optional[str] = None


class MonthlyFilterOptions(BaseModel):
    business_units: List[str]
    locations:      List[str]
    cost_centers:   List[str]
    departments:    List[str]


class DayCodeUpdate(BaseModel):

    day_code:   str   
    check_in:   Optional[str] = None
    check_out:  Optional[str] = None
    shift_name: Optional[str] = None


class MonthlyDownloadRow(BaseModel):
    employee_code: str
    employee_name: str
    department:    Optional[str]
    location:      Optional[str]
    month:         int
    year:          int
    present_days:  int
    absent_days:   int
    half_days:     int
    week_offs:     int
    holidays:      int
    leave_days:    int
    total_working_days: int
