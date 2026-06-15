from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date



class AttendanceKPIStats(BaseModel):
   
    present_rate: float            
    absent_rate: float              
    late_rate: float                
    total_overtime_hours: float     
    avg_overtime_per_employee: float  
    punctuality_score: float       
    consistency_score: float        
    active_alerts: int              
    leave_utilization: float        
    total_records: int
    present_count: int
    absent_count: int
    leave_count: int
    late_count: int



class DailyTrendPoint(BaseModel):
    date: str          
    present: int
    absent: int
    late: int
    overtime: int


class DeptTrendItem(BaseModel):
    name: str           
    present: float      
    absent: float
    late: float
    overtime: float    


class LocationTrendItem(BaseModel):
    name: str           
    present: float
    absent: float
    late: float
    overtime: float


class AnalyticsMetrics(BaseModel):
    absenteeism_rate: float
    punctuality_score: float
    leave_utilization: float
    overtime_rate: float
    attendance_consistency: float
    peak_absence_days: List[str]
    peak_absence_periods: List[str]
    anomaly_threshold: int
    predictive_alerts: int


class AnalyticsTrends(BaseModel):
    daily: List[DailyTrendPoint]
    department: List[DeptTrendItem]
    location: List[LocationTrendItem]



class CalendarDayOut(BaseModel):
    date: str           
    status: str         
    employee_id: str
    employee_name: str
    department: Optional[str]
    location: Optional[str]
    in_time: Optional[str]
    out_time: Optional[str]
    late_minutes: int = 0
    overtime_hours: float = 0.0



class ReportItem(BaseModel):
    id: int
    name: str
    report_type: str       
    frequency: str          
    description: str
    last_generated: Optional[str]
    columns: List[str]


class ExceptionRecord(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    location: Optional[str]
    date: str
    exception_type: str     
    detail: str             
    late_minutes: int = 0
    overtime_hours: float = 0.0
    status: str = "open"   


class PatternData(BaseModel):
    days: List[str]
    times: List[str]
    pattern: str


class AlertOut(BaseModel):
    id: int
    alert_type: str         
    employee: Optional[str] = None
    department: Optional[str] = None
    message: str
    severity: str           
    date: str
    acknowledged: bool = False
    pattern_data: PatternData


class AlertAcknowledge(BaseModel):
    alert_id: int



class AttendanceFilters(BaseModel):
    date_range: str = "month"   
    department: str = "all"
    location: str = "all"
    employee_id: Optional[str] = None
    search: Optional[str] = None