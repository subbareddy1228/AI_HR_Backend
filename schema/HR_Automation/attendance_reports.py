"""
schemas/attendance_reports.py
Pydantic v2 schemas for Attendance Reports & Analytics — all 5 tabs.
"""

from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from model.HR_Automation.attendance_reports import (
    ReportTypeEnum, ReportFrequencyEnum, ReportFormatEnum,
    SeverityEnum, AnomalyTypeEnum, ExceptionTypeEnum,
    ExceptionStatusEnum, AlertTypeEnum,
)


# ══════════════════════════════════════════════════════════
# GLOBAL FILTERS  (header row: period · dept · location · employee)
# ══════════════════════════════════════════════════════════

class GlobalFilterIn(BaseModel):
    period:      str            = "this_month"   # this_month|last_month|last_3m|last_6m|this_year|custom
    date_from:   Optional[date] = None
    date_to:     Optional[date] = None
    department:  Optional[str]  = None           # None = All Departments
    location:    Optional[str]  = None           # None = All Locations
    employee_id: Optional[str]  = None           # None = All Employees
    role:        str            = "Manager"      # Manager | HR | Admin (top-right dropdown)


# ══════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════

class KpiCardOut(BaseModel):
    """One stat card in the top KPI row."""
    label:        str
    value:        str    # "90.6%" | "107h" | "5"
    change:       Optional[str] = None   # "+2.1% from last month"
    changeType:   str = "neutral"        # positive | negative | warning | neutral
    subLabel:     Optional[str] = None   # "Requires attention" | "Target: 90%"
    subLabelType: str = "neutral"


class DailyTrendPoint(BaseModel):
    date:    date
    present: int
    absent:  int
    late:    int


class DepartmentPerformance(BaseModel):
    department:  str
    presentPct:  float
    absentPct:   float
    latePct:     float
    overtime:    str    # "45h"


class TopPerformer(BaseModel):
    employeeId:   str
    name:         str
    department:   str
    attendancePct:float
    avatar:       str   # first letter of name


class CalendarDayOut(BaseModel):
    day:      int
    date:     date
    present:  int
    absent:   int
    late:     int
    leave:    int
    records:  int
    isToday:  bool = False
    isWeekend:bool = False


class DashboardOut(BaseModel):
    kpiCards:            List[KpiCardOut]
    dailyTrends:         List[DailyTrendPoint]
    departmentPerformance:List[DepartmentPerformance]
    topPerformers:       List[TopPerformer]
    calendarData:        List[CalendarDayOut]


# ══════════════════════════════════════════════════════════
# TAB 2 — REPORTS
# ══════════════════════════════════════════════════════════

class ReportDefinitionOut(BaseModel):
    id:            int
    name:          str
    report_type:   ReportTypeEnum
    frequency:     ReportFrequencyEnum
    description:   str
    lastGenerated: Optional[date]
    typeDisplay:   str = ""    # "STANDARD" | "EXCEPTION" | "ANALYTICS" badge
    frequencyDisplay: str = "" # "Frequency: daily"

    model_config = {"from_attributes": True}


class GenerateReportIn(BaseModel):
    reportDefId:  int
    format:       ReportFormatEnum = ReportFormatEnum.pdf
    date_from:    Optional[date]   = None
    date_to:      Optional[date]   = None
    department:   Optional[str]    = None
    location:     Optional[str]    = None
    employee_id:  Optional[str]    = None


class GeneratedReportOut(BaseModel):
    id:            int
    report_name:   str
    report_type:   ReportTypeEnum
    format:        ReportFormatEnum
    file_name:     str
    total_records: int
    generated_at:  datetime
    generated_by_name: str

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# TAB 3 — ANALYTICS
# ══════════════════════════════════════════════════════════

class AnalyticsKpiOut(BaseModel):
    """6 analytics KPI cards: Absenteeism · Punctuality · Overtime · Leave · Consistency · Alerts"""
    label:       str
    value:       str
    benchmark:   str   # "Industry average: 3.5%" | "Target: 90%"
    description: str
    trend:       str   # "up" | "down" | "stable"
    trendLabel:  str


class LeavePatternOut(BaseModel):
    """Leave Pattern Analysis — by day of week + by month."""
    byDayOfWeek:  List[Dict[str, Any]]   # [{day: "Mon", count: 2}]
    byMonth:      List[Dict[str, Any]]   # [{month: "Jan", count: 11}]


class OvertimeAnalyticsOut(BaseModel):
    """Overtime Analytics section."""
    totalHours:           float
    avgPerEmployee:       float
    employeesWithOT:      int
    byDepartment:         List[Dict[str, Any]]  # [{dept, hours, pct}]


class PeakAbsenceOut(BaseModel):
    """Peak Absence Analysis section."""
    peakDays:    List[Dict[str, Any]]   # [{day: "Monday", rate: 68}]
    highPeriods: List[Dict[str, Any]]   # [{month: "January", comparison: "85% higher"}]


class AnomalyOut(BaseModel):
    id:            int
    employee_id:   str
    employeeName:  str = ""
    department:    str = ""
    anomaly_type:  AnomalyTypeEnum
    severity:      SeverityEnum
    metric:        str
    description:   str
    metric_value:  Optional[float]
    detection_date:date
    is_active:     bool

    model_config = {"from_attributes": True}


class AnomalyDetectionOut(BaseModel):
    totalAnomalies:    int
    highSeverity:      int
    mediumSeverity:    int
    affectedEmployees: int
    byType:            Dict[str, int]    # {"consecutive_late": 12, …}
    anomalies:         List[AnomalyOut]


class DeptAttendanceComparisonOut(BaseModel):
    """Department-wise Attendance Comparison table."""
    department:  str
    presentPct:  float
    absentPct:   float
    latePct:     float
    overtime:    str   # "45h"
    score:       float


class AnalyticsOut(BaseModel):
    kpiCards:           List[AnalyticsKpiOut]
    leavePattern:       LeavePatternOut
    overtimeAnalytics:  OvertimeAnalyticsOut
    peakAbsence:        PeakAbsenceOut
    anomalyDetection:   AnomalyDetectionOut
    deptComparison:     List[DeptAttendanceComparisonOut]


# ══════════════════════════════════════════════════════════
# TAB 4 — EXCEPTIONS
# ══════════════════════════════════════════════════════════

class ExceptionOut(BaseModel):
    id:             int
    employee_id:    str
    employeeName:   str = ""
    department:     str
    exception_type: ExceptionTypeEnum
    typeDisplay:    str = ""    # "Late by 22 mins" | "Absent"
    exception_date: date
    in_time:        Optional[str]
    out_time:       Optional[str]
    dateTimeDisplay:str = ""    # "2026-06-08  09:11 - 18:23"
    duration:       str = ""    # "22 mins" | "Full Day"
    status:         ExceptionStatusEnum
    notes:          str
    created_at:     datetime

    model_config = {"from_attributes": True}


class ExceptionSummaryOut(BaseModel):
    totalExceptions:     int
    lateArrivals:        int
    absentRecords:       int
    overtimeViolations:  int


class ExceptionListOut(BaseModel):
    summary: ExceptionSummaryOut
    items:   List[ExceptionOut]


# ══════════════════════════════════════════════════════════
# TAB 5 — ALERTS
# ══════════════════════════════════════════════════════════

class AlertOut(BaseModel):
    id:             int
    alert_type:     AlertTypeEnum
    severity:       SeverityEnum
    employee_id:    Optional[str]
    employee_name:  str = ""
    department:     str = ""
    message:        str
    pattern_data:   dict = {}
    acknowledged:   bool
    acknowledged_at:Optional[datetime]
    alert_date:     date
    created_at:     datetime
    # Display label matching card header
    typeDisplay:    str = ""    # "ANOMALY ALERT" | "PATTERN ALERT" …

    model_config = {"from_attributes": True}


class AlertSummaryOut(BaseModel):
    highPriority:    int
    mediumPriority:  int
    unacknowledged:  int
    acknowledged:    int


class AlertRuleOut(BaseModel):
    id:              int
    name:            str
    trigger:         str
    icon:            str
    color:           str
    is_active:       bool
    threshold:       int
    countThisMonth:  int

    model_config = {"from_attributes": True}


class AlertsPageOut(BaseModel):
    summary:        AlertSummaryOut
    alerts:         List[AlertOut]
    rules:          List[AlertRuleOut]


class AcknowledgeIn(BaseModel):
    alert_ids: Optional[List[int]] = None  # None = acknowledge all


class ConfigureAlertIn(BaseModel):
    rule_id:    int
    threshold:  Optional[int]  = None
    is_active:  Optional[bool] = None


# ══════════════════════════════════════════════════════════
# GENERIC
# ══════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    message: str
