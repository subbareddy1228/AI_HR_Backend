# schema/Reports/attendance_reports.py

from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date, datetime, time


# ── Top stat cards ────────────────────────────────────────────────────────────

class AttendanceReportStats(BaseModel):
    generated_reports: int
    pending_reports: int
    todays_reports: int
    compliance_ready: int


# ── Report Type Summary (bar chart right side) ────────────────────────────────

class ReportTypeSummary(BaseModel):
    daily_reports_total: int
    daily_reports_generated: int
    monthly_reports_total: int
    monthly_reports_generated: int
    exception_reports_total: int
    exception_reports_generated: int
    compliance_reports_total: int
    compliance_reports_generated: int


# ── Report list table ─────────────────────────────────────────────────────────

class AttendanceReportItem(BaseModel):
    report_name: str
    category: str           # Daily | Monthly | Exception | Compliance
    date: Optional[datetime] = None
    generated_at: Optional[str] = None
    department: Optional[str] = None
    details: Optional[str] = None
    status: str             # generated | pending | failed


# ── Report Generation History ─────────────────────────────────────────────────

class ReportGenerationHistoryItem(BaseModel):
    report_type: str
    from_date: date
    to_date: date
    generated_by: str
    file_size: Optional[str] = None
    status: str             # Generated | Generating | Failed


# ── Daily Attendance Summary ──────────────────────────────────────────────────

class DailyAttendanceSummaryItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    status: str             # PRESENT | ABSENT | LATE | HALF_DAY | ON_LEAVE | HOLIDAY
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    remarks: Optional[str] = None


# ── Late Arrivals ─────────────────────────────────────────────────────────────

class LateArrivalItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    check_in: Optional[time]
    late_by_minutes: int


# ── Early Departures ──────────────────────────────────────────────────────────

class EarlyDepartureItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    check_out: Optional[time]
    early_by_minutes: int


# ── Missing Punch ─────────────────────────────────────────────────────────────

class MissingPunchItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    punch_type: str         # CHECK_IN | CHECK_OUT | BOTH


# ── Monthly Attendance Register ───────────────────────────────────────────────

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


# ── Department-wise Attendance Summary ───────────────────────────────────────

class DeptAttendanceSummaryItem(BaseModel):
    department: str
    total_employees: int
    present: int
    absent: int
    on_leave: int
    attendance_pct: float


# ── Loss of Pay ───────────────────────────────────────────────────────────────

class LossOfPayItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    absent_days: int
    lop_days: int
    lop_amount: float


# ── Overtime Summary ──────────────────────────────────────────────────────────

class OvertimeSummaryItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    month: int
    year: int
    total_overtime_hours: float


# ── WFH Tracking ─────────────────────────────────────────────────────────────

class WFHTrackingItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    month: int
    year: int
    wfh_days: int


# ── Exception Report ─────────────────────────────────────────────────────────

class ExceptionReportItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    exception_type: str     # LATE | EARLY_DEPARTURE | MISSING_PUNCH | CONTINUOUS_ABSENCE | UNAPPROVED_OT


# ── Compliance Reports ────────────────────────────────────────────────────────

class ComplianceMusterRollItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    date: date
    status: str
    format: str             # Factory Act format


class AttendanceRegisterItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str]
    month: int
    year: int
    attendance_record: str  # e.g. P,P,A,P,H,...
