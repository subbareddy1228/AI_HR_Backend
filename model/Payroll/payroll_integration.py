from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text, JSON, func
)
from core.database import Base


class IntegrationSettings(Base):
    """
    Single-row settings table for Attendance-Payroll Integration.
    Covers Settings tab: Security, Sync, Notification, and Calculation Settings.
    """
    __tablename__ = "integration_settings"

    id                        = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ── Security Settings ─────────────────────────────────────────────────────
    two_factor_auth           = Column(String(20), nullable=False, default="Enabled")
    session_timeout           = Column(String(20), nullable=False, default="15 minutes")

    # ── Sync Settings ─────────────────────────────────────────────────────────
    attendance_sync_frequency = Column(String(20), nullable=False, default="15 minutes")
    payroll_sync_frequency    = Column(String(20), nullable=False, default="30 minutes")
    retry_failed_syncs        = Column(String(20), nullable=False, default="3 times")

    # ── Notification Settings ─────────────────────────────────────────────────
    email_notifications       = Column(Boolean, nullable=False, default=True)
    push_notifications        = Column(Boolean, nullable=False, default=True)
    sms_notifications         = Column(Boolean, nullable=False, default=False)
    alert_threshold           = Column(String(50), nullable=False, default="High: Any error")

    # ── Calculation Settings ──────────────────────────────────────────────────
    overtime_multiplier       = Column(Float, nullable=False, default=1.5)
    holiday_pay_multiplier    = Column(Float, nullable=False, default=2.0)
    monthly_working_days      = Column(Integer, nullable=False, default=30)
    daily_hours               = Column(Integer, nullable=False, default=8)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)


class AttendanceSyncLog(Base):
    """
    Tracks every attendance-to-payroll sync event.
    Powers: Dashboard sync status cards, Integration tab real-time data flow.
    """
    __tablename__ = "attendance_sync_logs"

    id             = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sync_type      = Column(String(50), nullable=False)          # attendance / payroll
    status         = Column(String(20), nullable=False)          # success / failed / in_progress
    synced_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    records_synced = Column(Integer, default=0)
    error_message  = Column(Text, nullable=True)
    duration_ms    = Column(Integer, nullable=True)              # sync duration in ms
    triggered_by   = Column(String(50), default="auto")         # auto / manual


class AttendanceFreeze(Base):
    """
    Records when attendance data is frozen for payroll processing.
    Powers: Integration tab Attendance Freeze card, Dashboard freeze status.
    """
    __tablename__ = "attendance_freezes"

    id             = Column(Integer, primary_key=True, index=True, autoincrement=True)
    period_start   = Column(Date, nullable=False)
    period_end     = Column(Date, nullable=False)
    freeze_status  = Column(String(20), nullable=False, default="UNFROZEN")  # FROZEN / UNFROZEN
    freeze_window  = Column(Integer, nullable=False, default=3)              # days before payroll
    next_freeze    = Column(Date, nullable=True)
    frozen_at      = Column(DateTime(timezone=True), nullable=True)
    frozen_by      = Column(String(100), nullable=True)
    unfrozen_at    = Column(DateTime(timezone=True), nullable=True)
    unfrozen_by    = Column(String(100), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmployeeAttendancePayroll(Base):
    """
    Per-employee attendance+payroll data for the current payroll period.
    Powers: Payroll Calculation tab table (employee rows with attendance & pay columns).
    """
    __tablename__ = "employee_attendance_payroll"

    id               = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id      = Column(String(20), nullable=False, index=True)
    employee_name    = Column(String(200), nullable=False)
    department       = Column(String(100), nullable=False)
    period_month     = Column(String(20), nullable=False)            # e.g. "2024-01"
    present_days     = Column(Integer, nullable=False, default=0)
    absent_days      = Column(Integer, nullable=False, default=0)
    overtime_hours   = Column(Float, nullable=False, default=0.0)
    holiday_work_days= Column(Integer, nullable=False, default=0)
    basic_salary     = Column(Float, nullable=False, default=0.0)
    loss_of_pay      = Column(Float, nullable=False, default=0.0)
    overtime_pay     = Column(Float, nullable=False, default=0.0)
    holiday_pay      = Column(Float, nullable=False, default=0.0)
    lwp_days         = Column(Integer, nullable=False, default=0)    # leave without pay
    net_pay          = Column(Float, nullable=False, default=0.0)
    payroll_status   = Column(String(30), nullable=False, default="pending")  # pending / calculated / approved
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now(), nullable=False)


class CalculationRule(Base):
    """
    Configurable calculation rules for pay components.
    Powers: Integration tab - Calculation Rules & Configuration section.
    Rules: Loss of Pay, Overtime, Holiday Pay, Leave Without Pay.
    """
    __tablename__ = "calculation_rules"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_name    = Column(String(100), nullable=False)        # Loss of Pay Calculation / Overtime Hours Feed
    description  = Column(String(255), nullable=True)        # Automatic deduction based on absence days
    formula      = Column(String(255), nullable=False)        # Daily Rate x Absent Days
    multiplier   = Column(Float, nullable=False, default=1.0) # 1x / 1.5x / 2x
    is_active    = Column(Boolean, nullable=False, default=True)
    rule_type    = Column(String(50), nullable=False)         # deduction / addition
    display_order= Column(Integer, nullable=False, default=0)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(),
                          onupdate=func.now(), nullable=False)


class AttendanceCorrection(Base):
    """
    Attendance corrections and post-payroll adjustments.
    Powers: Corrections tab table with approve/reject workflow.
    Types: Overtime Update / Status Change / Time Correction / Post-Payroll Adjustment
    """
    __tablename__ = "attendance_corrections"

    id               = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id      = Column(String(20), nullable=False, index=True)
    employee_name    = Column(String(200), nullable=False)
    original_date    = Column(Date, nullable=False)
    correction_type  = Column(String(50), nullable=False)   # Overtime Update / Status Change / Time Correction / Post-Payroll Adjustment
    original_value   = Column(String(100), nullable=False)  # stored as string to cover hours, status, time
    corrected_value  = Column(String(100), nullable=False)
    payroll_impact   = Column(Float, nullable=False, default=0.0)  # +75.00 / -140.00 / 0
    impact_type      = Column(String(20), nullable=False, default="none")  # addition / deduction / none
    status           = Column(String(20), nullable=False, default="PENDING")  # PENDING / APPROVED / REJECTED
    requested_by     = Column(String(100), nullable=False)
    requested_role   = Column(String(50), nullable=False)   # Manager / HR / Employee / Payroll Admin
    requested_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_by      = Column(String(100), nullable=True)
    reviewed_at      = Column(DateTime(timezone=True), nullable=True)
    review_remarks   = Column(Text, nullable=True)


class SystemAlert(Base):
    """
    Integration system alerts and action-required notifications.
    Powers: Dashboard - Action Required section, System Health indicators.
    Types: SYNC / CALCULATION / FREEZE / CORRECTION
    """
    __tablename__ = "system_alerts"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_type   = Column(String(30), nullable=False)   # SYNC / CALCULATION / FREEZE / CORRECTION
    message      = Column(Text, nullable=False)
    severity     = Column(String(20), nullable=False, default="INFO")  # INFO / WARNING / ERROR
    is_resolved  = Column(Boolean, nullable=False, default=False)
    resolved_by  = Column(String(100), nullable=True)
    resolved_at  = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IntegrationReport(Base):
    """
    Integration-specific report definitions.
    Powers: Reports tab cards (Payroll-Attendance Reconciliation, Loss of Pay Report,
    Overtime Payment Summary, Holiday Working Compensation, Leave Without Pay Report,
    Post-Payroll Correction Log, Attendance Freeze Log, Integration Health Report).
    """
    __tablename__ = "integration_reports"

    id             = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_name    = Column(String(200), nullable=False)
    report_category= Column(String(50), nullable=False)   # RECONCILIATION / DEDUCTION / ADDITION / AUDIT / SYSTEM
    description    = Column(Text, nullable=True)
    frequency      = Column(String(20), nullable=False)   # monthly / quarterly / weekly
    formats        = Column(JSON, default=list)            # ["PDF", "Excel"] / ["Excel", "CSV"]
    column_count   = Column(Integer, nullable=False, default=5)
    last_generated = Column(Date, nullable=True)
    file_path      = Column(String(500), nullable=True)
    is_active      = Column(Boolean, nullable=False, default=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
