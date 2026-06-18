
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum




class OptionalAppStatus(str, Enum):
    PENDING  = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class CalendarStatus(str, Enum):
    ACTIVE   = "Active"
    INACTIVE = "Inactive"
    DRAFT    = "Draft"


class SwapRequestStatus(str, Enum):
    PENDING   = "Pending"
    APPROVED  = "Approved"
    REJECTED  = "Rejected"
    CANCELLED = "Cancelled"


class CarryForwardStatus(str, Enum):
    PENDING   = "Pending"
    PROCESSED = "Processed"
    FAILED    = "Failed"




class OptionalHolidayApplicationCreate(BaseModel):
   
    employee_id:  int
    holiday_id:   int
    reason:       Optional[str] = None


class OptionalHolidayApplicationUpdate(BaseModel):
    
    status:            Optional[OptionalAppStatus] = None
    approved_by:       Optional[int] = None
    rejection_reason:  Optional[str] = None


class OptionalHolidayApplicationOut(BaseModel):
    id:               int
    employee_id:      int
    holiday_id:       int
    holiday_name:     Optional[str]
    holiday_date:     date
    applied_on:       datetime
    status:           OptionalAppStatus
    reason:            Optional[str]
    approved_by:       Optional[int]
    approved_on:       Optional[datetime]
    rejection_reason:  Optional[str]

    model_config = ConfigDict(from_attributes=True)




class HolidayCalendarCreate(BaseModel):
    
    calendar_name:   str = Field(..., example="India - National Calendar")
    location:        Optional[str] = "All"
    employee_groups: Optional[str] = "All Groups"
    is_default:      Optional[bool] = False
    description:     Optional[str] = None
    holiday_ids:      Optional[List[int]] = None    


class HolidayCalendarUpdate(BaseModel):
    calendar_name:   Optional[str] = None
    location:        Optional[str] = None
    employee_groups: Optional[str] = None
    status:          Optional[CalendarStatus] = None
    is_default:      Optional[bool] = None
    description:     Optional[str] = None


class HolidayCalendarOut(BaseModel):
    id:              int
    calendar_name:   str
    location:        Optional[str]
    employee_groups: Optional[str]
    status:          CalendarStatus
    is_default:      bool
    description:     Optional[str]
    holiday_count:   int = 0          
    created_at:      datetime

    model_config = ConfigDict(from_attributes=True)


class CalendarHolidayLink(BaseModel):
    
    calendar_id: int
    holiday_id:  int




class HolidaySwapRequestCreate(BaseModel):
    
    employee_id:  int
    holiday_id:   Optional[int] = None
    holiday_date: date
    work_date:    date
    reason:       Optional[str] = None


class HolidaySwapRequestUpdate(BaseModel):
    
    status:            Optional[SwapRequestStatus] = None
    approved_by:       Optional[int] = None
    rejection_reason:  Optional[str] = None


class HolidaySwapRequestOut(BaseModel):
    id:                int
    employee_id:       int
    employee_name:     Optional[str] = None   
    holiday_id:        Optional[int]
    holiday_date:      date
    work_date:         date
    reason:             Optional[str]
    status:             SwapRequestStatus
    approved_by:        Optional[int]
    approved_on:        Optional[datetime]
    rejection_reason:   Optional[str]
    created_at:          datetime

    model_config = ConfigDict(from_attributes=True)




class HolidayCarryForwardCreate(BaseModel):
    
    employee_id:    int
    from_year:      int
    to_year:        int
    holidays_count: int = 0
    remarks:         Optional[str] = None


class ProcessCarryForwardRequest(BaseModel):
   
    from_year:     int
    to_year:       int
    employee_ids:  Optional[List[int]] = None   
    max_carry_forward: Optional[int] = Field(
        default=None, description="Cap on number of holidays that can be carried forward"
    )


class HolidayCarryForwardOut(BaseModel):
    id:             int
    employee_id:    int
    employee_name:  Optional[str] = None
    from_year:      int
    to_year:        int
    holidays_count: int
    status:         CarryForwardStatus
    processed_by:   Optional[int]
    processed_on:   Optional[datetime]
    remarks:         Optional[str]
    created_at:       datetime

    model_config = ConfigDict(from_attributes=True)




class HolidayCalendarTabSummary(BaseModel):
    
    holiday_master_count:  int
    optional_apps_count:   int
    calendars_count:       int
    holiday_swap_count:    int
    carry_forward_count:   int