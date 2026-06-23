"""
models/attendance_reports.py
SQLAlchemy ORM models for Attendance Reports & Analytics module.

Covers all 5 tabs:
  Tab 1 — Dashboard   : (queries from existing attendance/leave tables)
  Tab 2 — Reports     : ReportDefinition, GeneratedReport
  Tab 3 — Analytics   : AttendanceAnomaly
  Tab 4 — Exceptions  : AttendanceException
  Tab 5 — Alerts      : AttendanceAlert, AlertRule
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    ForeignKey, Text, Enum as SAEnum, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import enum

from core.database import Base


# ─────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────

class ReportTypeEnum(str, enum.Enum):
    standard  = "standard"
    exception = "exception"
    analytics = "analytics"


class ReportFrequencyEnum(str, enum.Enum):
    daily     = "daily"
    weekly    = "weekly"
    monthly   = "monthly"
    quarterly = "quarterly"


class ReportFormatEnum(str, enum.Enum):
    pdf   = "pdf"
    excel = "excel"
    csv   = "csv"


class SeverityEnum(str, enum.Enum):
    high   = "high"
    medium = "medium"
    low    = "low"


class AnomalyTypeEnum(str, enum.Enum):
    consecutive_late    = "consecutive_late"
    high_absenteeism    = "high_absenteeism"
    frequent_late       = "frequent_late"
    excessive_overtime  = "excessive_overtime"
    consecutive_absent  = "consecutive_absent"
    pattern_detection   = "pattern_detection"
    severe_lateness     = "severe_lateness"


class ExceptionTypeEnum(str, enum.Enum):
    late_arrival         = "late_arrival"
    absent_without_leave = "absent_without_leave"
    excessive_overtime   = "excessive_overtime"


class ExceptionStatusEnum(str, enum.Enum):
    pending_review    = "Pending Review"
    in_review         = "In Review"
    requires_approval = "Requires Approval"
    resolved          = "Resolved"


class AlertTypeEnum(str, enum.Enum):
    anomaly    = "anomaly"
    pattern    = "pattern"
    threshold  = "threshold"
    predictive = "predictive"
    overtime   = "overtime"


# ─────────────────────────────────────────────────────────
# TAB 2 — REPORT DEFINITIONS  (the 12 report cards)
# ─────────────────────────────────────────────────────────

class ReportDefinition(Base):
    """
    Static report definitions shown in the Standard Reports Library.
    Each card: name · type badge · description · frequency · lastGenerated · download icon
    """
    __tablename__ = "report_definitions"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(200), nullable=False)
    report_type   = Column(SAEnum(ReportTypeEnum), nullable=False, index=True)
    frequency     = Column(SAEnum(ReportFrequencyEnum), nullable=False)
    description   = Column(Text, nullable=False)
    columns       = Column(JSONB, default=[])          # list of column names
    is_active     = Column(Boolean, default=True)
    last_generated= Column(Date, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ReportDefinition {self.name} [{self.report_type}]>"


class GeneratedReport(Base):
    """
    Audit record for every report that has been generated/downloaded.
    """
    __tablename__ = "generated_reports"

    id                = Column(Integer, primary_key=True, index=True)
    report_def_id     = Column(Integer,
                                ForeignKey("report_definitions.id", ondelete="SET NULL"),
                                nullable=True)
    report_name       = Column(String(200), nullable=False)
    report_type       = Column(SAEnum(ReportTypeEnum), nullable=False)
    format            = Column(SAEnum(ReportFormatEnum), default=ReportFormatEnum.pdf)
    file_name         = Column(String(255), nullable=False)
    filters_applied   = Column(JSONB, default={})     # date/dept/location/employee
    total_records     = Column(Integer, default=0)
    generated_at      = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    generated_by      = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    generated_by_name = Column(String(100), default="")

    __table_args__ = (
        Index("ix_gen_report_type", "report_type"),
    )


# ─────────────────────────────────────────────────────────
# TAB 3 — ATTENDANCE ANOMALIES
# ─────────────────────────────────────────────────────────

class AttendanceAnomaly(Base):
    """
    Computed anomaly record per employee.
    Shown in Analytics tab → Attendance Anomaly Detection section.
    Columns: Employee · Anomaly Type · Metric · Severity badge
    """
    __tablename__ = "attendance_anomalies"

    id            = Column(Integer, primary_key=True, index=True)
    employee_id   = Column(String(20),
                            ForeignKey("employees.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    anomaly_type  = Column(SAEnum(AnomalyTypeEnum), nullable=False, index=True)
    severity      = Column(SAEnum(SeverityEnum), nullable=False, default=SeverityEnum.medium)
    metric        = Column(String(200), nullable=False)   # "4 consecutive late arrivals"
    description   = Column(Text, nullable=False)
    metric_value  = Column(Float, nullable=True)
    detection_date= Column(Date, nullable=False, default=func.current_date(), index=True)
    is_active     = Column(Boolean, default=True)
    resolved_at   = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_anomaly_severity", "severity"),
        Index("ix_anomaly_emp_type", "employee_id", "anomaly_type"),
    )

    def __repr__(self):
        return (
            f"<AttendanceAnomaly emp={self.employee_id} "
            f"{self.anomaly_type} [{self.severity}]>"
        )


# ─────────────────────────────────────────────────────────
# TAB 4 — ATTENDANCE EXCEPTIONS
# ─────────────────────────────────────────────────────────

class AttendanceException(Base):
    """
    Exception record per employee per day.
    Table: Employee · Department · Exception Type · Date & Time · Duration · Status · Actions
    Summary cards: Total · Late Arrivals · Absent Records · Overtime Violations
    """
    __tablename__ = "attendance_exceptions"

    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(String(20),
                              ForeignKey("employees.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    department      = Column(String(100), default="")
    exception_type  = Column(SAEnum(ExceptionTypeEnum), nullable=False, index=True)
    exception_date  = Column(Date, nullable=False, index=True)
    in_time         = Column(String(10), nullable=True)   # "09:11"
    out_time        = Column(String(10), nullable=True)   # "18:23"
    duration_minutes= Column(Integer, default=0)          # late minutes / overtime hours
    status          = Column(SAEnum(ExceptionStatusEnum),
                              default=ExceptionStatusEnum.in_review, index=True)
    notes           = Column(Text, default="")
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now())

    __table_args__ = (
        Index("ix_exception_date_type", "exception_date", "exception_type"),
        Index("ix_exception_emp_date",  "employee_id", "exception_date"),
    )

    def __repr__(self):
        return (
            f"<AttendanceException emp={self.employee_id} "
            f"{self.exception_type} {self.exception_date}>"
        )


# ─────────────────────────────────────────────────────────
# TAB 5 — ALERTS
# ─────────────────────────────────────────────────────────

class AttendanceAlert(Base):
    """
    Predictive alert record.
    Cards: ANOMALY ALERT · PATTERN ALERT · THRESHOLD ALERT · PREDICTIVE ALERT · OVERTIME ALERT
    Each card: Acknowledge button · View Pattern button
    Stats: High Priority · Medium Priority · Unacknowledged · Acknowledged
    """
    __tablename__ = "attendance_alerts"

    id               = Column(Integer, primary_key=True, index=True)
    alert_type       = Column(SAEnum(AlertTypeEnum), nullable=False, index=True)
    severity         = Column(SAEnum(SeverityEnum), nullable=False, default=SeverityEnum.medium)
    employee_id      = Column(String(20), nullable=True, index=True)
    employee_name    = Column(String(100), default="")   # denormalized
    department       = Column(String(100), default="")
    message          = Column(Text, nullable=False)
    pattern_data     = Column(JSONB, default={
        "days": [], "times": [], "pattern": ""
    })
    acknowledged     = Column(Boolean, default=False, index=True)
    acknowledged_at  = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by  = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    alert_date       = Column(Date, nullable=False, default=func.current_date())
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_alert_ack_severity", "acknowledged", "severity"),
    )

    def __repr__(self):
        return (
            f"<AttendanceAlert {self.alert_type} "
            f"{'ACK' if self.acknowledged else 'UNACK'} [{self.severity}]>"
        )


class AlertRule(Base):
    """
    Anomaly Detection Rules shown at the bottom of the Alerts tab.
    Rows: Consecutive Late Arrivals · Frequent Absence Pattern
          Excessive Overtime · Department Threshold
    Each row: Rule · Trigger · Count (this month)
    """
    __tablename__ = "alert_rules"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(200), nullable=False)
    trigger       = Column(String(200), nullable=False)   # e.g. "3 consecutive days"
    icon          = Column(String(50), default="bi-clock-history")
    color         = Column(String(20), default="#ef4444")
    is_active     = Column(Boolean, default=True)
    threshold     = Column(Integer, default=3)
    count_this_month = Column(Integer, default=0)
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(),
                            onupdate=func.now())

    def __repr__(self):
        return f"<AlertRule {self.name}>"
