
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date, datetime, time


class AttendanceReportStats(BaseModel):
    generated_reports: int
    pending_reports: int
    todays_reports: int
    compliance_ready: int

class ReportTypeSummary(BaseModel):
    daily_reports_total: int
    daily_reports_generated: int
    monthly_reports_total: int
    monthly_reports_generated: int
    exception_reports_total: int
    exception_reports_generated: int
    compliance_reports_total: int
    compliance_reports_generated: int


class AttendanceReportItem(BaseModel):
    report_name: str
    category: str          
    date: Optional[datetime] = None
    generated_at: Optional[str] = None
    department: Optional[str] = None
    details: Optional[str] = None
    status: str            


class ReportGenerationHistoryItem(BaseModel):
    report_type: str
    from_date: date
    to_date: date
    generated_by: str
    file_size: Optional[str] = None
    status: str           

class DailyAttendanceSummaryItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    status: str           
    check_out: Optional[time] = None
    remarks: Optional[str] = None


class LateArrivalItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    check_in: Optional[time]
    late_by_minutes: int


class EarlyDepartureItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    check_out: Optional[time]
    early_by_minutes: int


class MissingPunchItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    punch_type: str       


class MonthlyAttendanceItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    month: int
    year: int
    present_days: int
    absent_days: int
    late_days: int
    half_days: int
    leave_days: int
    holidays: int
    total_working_days: int

class DeptAttendanceSummaryItem(BaseModel):
    department: str
    total_employees: int
    present: int
    absent: int
    on_leave: int
    attendance_pct: float


class LossOfPayItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    absent_days: int
    lop_days: int
    lop_amount: float


class OvertimeSummaryItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    month: int
    year: int
    total_overtime_hours: float


class WFHTrackingItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    month: int
    year: int
    wfh_days: int


class ExceptionReportItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    exception_type: str    




class ComplianceMusterRollItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    status: str
    format: str            


class AttendanceRegisterItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    month: int
    year: int
    attendance_record: str  
