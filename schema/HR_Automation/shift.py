from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import time, date, datetime




class ShiftBase(BaseModel):
    shift_name: str                     
    shift_code: str                     
    shift_type: str                     
    description: Optional[str] = None  
    start_time: time                    
    end_time: time                     
    duration_hours: float = 9.0        
    week_offs: str = "Sunday"         
    differential_pay: float = 1.0      
    break_duration_minutes: int = 30
    grace_period_minutes: int = 10
    is_night_shift: bool = False
    is_active: bool = True


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(BaseModel):
    shift_name: Optional[str] = None
    shift_code: Optional[str] = None
    shift_type: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: Optional[float] = None
    week_offs: Optional[str] = None
    differential_pay: Optional[float] = None
    break_duration_minutes: Optional[int] = None
    grace_period_minutes: Optional[int] = None
    is_night_shift: Optional[bool] = None
    is_active: Optional[bool] = None


class ShiftResponse(ShiftBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




class ShiftAssignmentCreate(BaseModel):
    
    employee_id: int
    shift_id: int
    start_date: date
    end_date: Optional[date] = None     


class BulkShiftAssignmentCreate(BaseModel):
    
    shift_id: int
    employee_ids: List[int]
    start_date: date
    end_date: Optional[date] = None


class ShiftAssignmentResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    shift_id: int
    shift_name: str
    shift_code: str
    start_date: date
    end_date: Optional[date]
    status: str                         

    model_config = ConfigDict(from_attributes=True)


class ShiftAssignmentUpdate(BaseModel):
    shift_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None




class RosterCreate(BaseModel):
    
    shift_id: int
    period: str                         
    start_date: date


class RosterResponse(BaseModel):
    id: int
    roster_name: str
    shift_id: int
    shift_name: str
    period: str                         
    start_date: date
    end_date: date
    status: str                         
    published: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RosterUpdate(BaseModel):
    status: Optional[str] = None
    published: Optional[bool] = None




class ShiftSwapCreate(BaseModel):
    """New Swap Request."""
    employee_id: int
    current_shift_id: int
    requested_shift_id: int
    swap_date: date
    reason: Optional[str] = None


class ShiftSwapResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    current_shift: str
    requested_shift: str
    swap_date: date
    reason: Optional[str]
    status: str                        
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShiftSwapUpdate(BaseModel):
    status: str                         
    remarks: Optional[str] = None




class FlexibleArrangementCreate(BaseModel):
    
    employee_id: int
    arrangement_type: str              
    core_hours: str                     
    flexible_window: str                
    remote_days: str                    
    status: str = "active"


class FlexibleArrangementResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    arrangement_type: str
    core_hours: str
    flexible_window: str
    remote_days: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlexibleArrangementUpdate(BaseModel):
    arrangement_type: Optional[str] = None
    core_hours: Optional[str] = None
    flexible_window: Optional[str] = None
    remote_days: Optional[str] = None
    status: Optional[str] = None


 

class AttendanceRulesSchema(BaseModel):
    
    late_arrival_grace_period: int = 15         
    minimum_work_hours: int = 8
    half_day_threshold: float = 4.0            
    weekend_working_requires_approval: bool = True
    holiday_working_requires_approval: bool = True


class OvertimeRulesSchema(BaseModel):
    
    weekday_overtime_rate: float = 1.5
    weekend_overtime_rate: float = 2.0
    holiday_overtime_rate: float = 3.0
    daily_overtime_cap: float = 4.0            
    weekly_overtime_cap: float = 20.0          


class BreakManagementSchema(BaseModel):
    
    allow_multiple_breaks: bool = True
    break_punch_required: bool = False
    max_break_duration: int = 120               
    unpaid_break_threshold: int = 30            


class WorkHourRulesConfig(BaseModel):
    
    attendance: AttendanceRulesSchema = AttendanceRulesSchema()
    overtime: OvertimeRulesSchema = OvertimeRulesSchema()
    breaks: BreakManagementSchema = BreakManagementSchema()




class NotificationOut(BaseModel):
    id: int
    message: str
    type: str                           
    is_read: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)