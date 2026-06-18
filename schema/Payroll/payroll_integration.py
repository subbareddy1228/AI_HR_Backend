from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


# ── Integration Settings ──────────────────────────────────────────────────────

class IntegrationSettingsUpdate(BaseModel):
    two_factor_auth: str = "Enabled"
    session_timeout: str = "15 minutes"
    attendance_sync_frequency: str = "15 minutes"
    payroll_sync_frequency: str = "30 minutes"
    retry_failed_syncs: str = "3 times"
    email_notifications: bool = True
    push_notifications: bool = True
    sms_notifications: bool = False
    alert_threshold: str = "High: Any error"
    overtime_multiplier: float = 1.5
    holiday_pay_multiplier: float = 2.0
    monthly_working_days: int = 30
    daily_hours: int = 8

class IntegrationSettingsOut(IntegrationSettingsUpdate):
    id: int
    updated_at: datetime
    class Config: from_attributes = True


# ── Attendance Sync Log ───────────────────────────────────────────────────────

class SyncTriggerRequest(BaseModel):
    sync_type: str = "attendance"    # attendance / payroll

class AttendanceSyncLogOut(BaseModel):
    id: int
    sync_type: str
    status: str
    synced_at: datetime
    records_synced: int
    error_message: Optional[str]
    duration_ms: Optional[int]
    triggered_by: str
    class Config: from_attributes = True


# ── Attendance Freeze ─────────────────────────────────────────────────────────

class AttendanceFreezeCreate(BaseModel):
    period_start: date
    period_end: date
    freeze_window: int = 3

class AttendanceFreezeOut(BaseModel):
    id: int
    period_start: date
    period_end: date
    freeze_status: str
    freeze_window: int
    next_freeze: Optional[date]
    frozen_at: Optional[datetime]
    frozen_by: Optional[str]
    unfrozen_at: Optional[datetime]
    class Config: from_attributes = True


# ── Employee Attendance Payroll ───────────────────────────────────────────────

class EmployeeAttendancePayrollOut(BaseModel):
    id: int
    employee_id: str
    employee_name: str
    department: str
    period_month: str
    present_days: int
    absent_days: int
    overtime_hours: float
    holiday_work_days: int
    basic_salary: float
    loss_of_pay: float
    overtime_pay: float
    holiday_pay: float
    lwp_days: int
    net_pay: float
    payroll_status: str
    class Config: from_attributes = True

class RunPayrollRequest(BaseModel):
    period_month: str
    department: Optional[str] = None     # None = all departments


# ── Calculation Rules ─────────────────────────────────────────────────────────

class CalculationRuleCreate(BaseModel):
    rule_name: str
    description: Optional[str] = None
    formula: str
    multiplier: float = 1.0
    is_active: bool = True
    rule_type: str                       # deduction / addition
    display_order: int = 0

class CalculationRuleUpdate(CalculationRuleCreate):
    pass

class CalculationRuleOut(CalculationRuleCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True


# ── Attendance Corrections ────────────────────────────────────────────────────

class AttendanceCorrectionCreate(BaseModel):
    employee_id: str
    employee_name: str
    original_date: date
    correction_type: str               # Overtime Update / Status Change / Time Correction / Post-Payroll Adjustment
    original_value: str
    corrected_value: str
    payroll_impact: float = 0.0
    impact_type: str = "none"          # addition / deduction / none
    requested_by: str
    requested_role: str

class CorrectionReviewRequest(BaseModel):
    status: str                        # APPROVED / REJECTED
    reviewed_by: str
    review_remarks: Optional[str] = None

class AttendanceCorrectionOut(BaseModel):
    id: int
    employee_id: str
    employee_name: str
    original_date: date
    correction_type: str
    original_value: str
    corrected_value: str
    payroll_impact: float
    impact_type: str
    status: str
    requested_by: str
    requested_role: str
    requested_at: datetime
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_remarks: Optional[str]
    class Config: from_attributes = True


# ── System Alerts ─────────────────────────────────────────────────────────────

class SystemAlertOut(BaseModel):
    id: int
    alert_type: str
    message: str
    severity: str
    is_resolved: bool
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    class Config: from_attributes = True

class ResolveAlertRequest(BaseModel):
    resolved_by: str


# ── Dashboard Summary ─────────────────────────────────────────────────────────

class DashboardSummaryOut(BaseModel):
    real_time_sync_hours: float
    data_status: str
    total_loss_of_pay: float
    lop_affected_employees: int
    overtime_pay: float
    overtime_avg_hours: float
    holiday_pay: float
    leave_without_pay_days: int
    lwp_deduction: float
    pending_corrections: int
    processed_payroll: float
    processed_payroll_employees: int


# ── Integration Report ────────────────────────────────────────────────────────

class IntegrationReportOut(BaseModel):
    id: int
    report_name: str
    report_category: str
    description: Optional[str]
    frequency: str
    formats: List[str]
    column_count: int
    last_generated: Optional[date]
    class Config: from_attributes = True
