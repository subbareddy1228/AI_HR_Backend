"""
model/Payroll/payroll_reports.py
---------------------------------
ORM models for the Payroll Reports & Analytics page.
Follows project conventions from payroll_run.py, statutory_compliance.py, etc.

Tables:
  - payroll_report_custom        : Report Builder saved definitions
  - payroll_report_custom_col    : Selected columns per custom report
  - payroll_report_schedule      : Scheduled reports (Scheduled tab)
  - payroll_report_generated     : Generated report file history (Generated tab)
  - payroll_ai_insight           : AI-Driven Insights (dashboard header)
  - payroll_report_config        : Org-wide report settings (Configuration tab)
  - payroll_compliance_report    : Statutory compliance reports (Compliance tab)
  - payroll_analytics_dashboard  : Analytics dashboard cards (Analytics tab)
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from core.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────


class ReportCategory(str, enum.Enum):
    SALARY = "Salary"
    STATUTORY = "Statutory"
    DEDUCTION = "Deduction"
    BANK_TRANSFER = "Bank Transfer"
    ATTENDANCE = "Attendance"
    CUSTOM = "Custom"


class ReportFormat(str, enum.Enum):
    PDF = "PDF"
    EXCEL = "Excel"
    CSV = "CSV"


class ReportFrequency(str, enum.Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    ANNUAL = "Annual"
    ON_DEMAND = "On Demand"
    DONT_SCHEDULE = "Don't schedule"


class ReportStatus(str, enum.Enum):
    GENERATED = "generated"
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    SUBMITTED = "submitted"
    AVAILABLE = "available"
    FAILED = "failed"
    OVERDUE = "overdue"


class InsightSeverity(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ComplianceType(str, enum.Enum):
    TDS = "TDS"
    PF = "PF"
    ESI = "ESI"
    PT = "PT"
    CERTIFICATE = "Certificate"


class ChartType(str, enum.Enum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    HISTOGRAM = "histogram"
    COMBO = "combo"


class ColumnGroup(str, enum.Enum):
    BASIC = "Basic"
    SALARY = "Salary"
    DEDUCTIONS = "Deductions"
    ATTENDANCE = "Attendance"


class DataSource(str, enum.Enum):
    PAYROLL_DATA = "Payroll Data"
    ATTENDANCE_DATA = "Attendance Data"
    EMPLOYEE_DATA = "Employee Data"
    BANK_DATA = "Bank Data"
    STATUTORY_DATA = "Statutory Data"


# ─────────────────────────────────────────────────────────────────────────────
# PayrollReportCustom  — Report Builder saved definitions
# ─────────────────────────────────────────────────────────────────────────────


class PayrollReportCustom(Base):
    """
    Stores a saved Custom Report created via the Report Builder wizard
    (4 steps: Report Details → Columns & Data → Filters & Sorting → Format & Schedule).
    Shown in Configuration tab → Custom Reports table.
    """

    __tablename__ = "payroll_report_custom"

    id = Column(Integer, primary_key=True, index=True)

    # Step 1 – Report Details
    report_name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(ReportCategory), nullable=False, default=ReportCategory.SALARY)
    data_source = Column(Enum(DataSource), nullable=False, default=DataSource.PAYROLL_DATA)

    # Step 3 – Filters & Sorting
    department_filter = Column(Text, nullable=True)      # JSON: ["Engineering", "HR"]
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)
    min_salary = Column(Numeric(12, 2), nullable=True, default=0)
    max_salary = Column(Numeric(12, 2), nullable=True, default=500000)
    sort_column = Column(String(100), nullable=True)
    sort_direction = Column(String(5), nullable=True, default="asc")

    # Step 4 – Format & Schedule
    export_pdf = Column(Boolean, nullable=False, default=True)
    export_excel = Column(Boolean, nullable=False, default=True)
    export_csv = Column(Boolean, nullable=False, default=False)
    schedule_frequency = Column(
        Enum(ReportFrequency), nullable=False, default=ReportFrequency.DONT_SCHEDULE
    )
    add_as_dashboard_widget = Column(Boolean, nullable=False, default=False)

    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PayrollReportCustom id={self.id} name={self.report_name!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# PayrollReportCustomCol  — Selected columns per custom report
# ─────────────────────────────────────────────────────────────────────────────


class PayrollReportCustomCol(Base):
    """
    Each row = one selected column for a PayrollReportCustom.
    Maps to the 'Select Data Columns' step — Basic, Salary, Deductions, Attendance groups.
    """

    __tablename__ = "payroll_report_custom_col"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(
        Integer,
        ForeignKey("payroll_report_custom.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    column_key = Column(String(100), nullable=False)      # e.g. "basic_salary", "pf_employee"
    column_label = Column(String(255), nullable=False)     # display label
    column_group = Column(Enum(ColumnGroup), nullable=False, default=ColumnGroup.BASIC)
    data_type = Column(String(20), nullable=False, default="text")  # text|currency|number|date
    sort_order = Column(Integer, nullable=False, default=0)
    is_selected = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("report_id", "column_key", name="uq_payroll_rpt_col"),
    )

    def __repr__(self):
        return f"<PayrollReportCustomCol report={self.report_id} key={self.column_key}>"


# ─────────────────────────────────────────────────────────────────────────────
# PayrollReportSchedule  — Scheduled tab
# ─────────────────────────────────────────────────────────────────────────────


class PayrollReportSchedule(Base):
    """
    Scheduled report delivery. Shown in Scheduled Reports tab:
    Report Name | Schedule | Next Run | Recipients | Format | Status | Actions
    """

    __tablename__ = "payroll_report_schedule"

    id = Column(Integer, primary_key=True, index=True)

    report_name = Column(String(255), nullable=False, index=True)
    custom_report_id = Column(
        Integer, ForeignKey("payroll_report_custom.id"), nullable=True
    )

    frequency = Column(
        Enum(ReportFrequency), nullable=False, default=ReportFrequency.MONTHLY
    )
    day_of_month = Column(Integer, nullable=True)   # 1-31; e.g. 1 = "1st of every month"
    day_of_week = Column(Integer, nullable=True)    # 0=Mon…6=Sun (weekly)
    time_of_day = Column(String(10), nullable=True)  # "HH:MM"

    recipients = Column(Text, nullable=False)        # JSON: ["hr@co.com", "finance@co.com"]
    export_format = Column(Text, nullable=False, default='["PDF","Excel"]')  # JSON list

    is_active = Column(Boolean, nullable=False, default=True)
    next_run_at = Column(DateTime, nullable=True)
    last_run_at = Column(DateTime, nullable=True)

    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_prs_active_next_run", "is_active", "next_run_at"),
    )

    def __repr__(self):
        return f"<PayrollReportSchedule id={self.id} name={self.report_name!r} freq={self.frequency}>"


# ─────────────────────────────────────────────────────────────────────────────
# PayrollReportGenerated  — Generated tab (report file history)
# ─────────────────────────────────────────────────────────────────────────────


class PayrollReportGenerated(Base):
    """
    Every generated report file. Shown in Generated Reports tab:
    Report Name | Period | Generated Date | Generated By | Format | Size | Downloads | Actions
    """

    __tablename__ = "payroll_report_generated"

    id = Column(Integer, primary_key=True, index=True)

    report_name = Column(String(255), nullable=False, index=True)
    custom_report_id = Column(
        Integer, ForeignKey("payroll_report_custom.id"), nullable=True
    )
    schedule_id = Column(
        Integer, ForeignKey("payroll_report_schedule.id"), nullable=True
    )

    period_label = Column(String(100), nullable=True)   # "March 2024", "Q4 FY 2023-24"
    period_month = Column(Integer, nullable=True)
    period_year = Column(Integer, nullable=True)

    format = Column(Enum(ReportFormat), nullable=False, default=ReportFormat.PDF)
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    download_count = Column(Integer, nullable=False, default=0)

    generated_by_label = Column(String(255), nullable=True)  # "System", "HR Manager", "Finance"
    generated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_prg_report_name", "report_name"),
        Index("ix_prg_generated_at", "generated_at"),
    )

    def __repr__(self):
        return f"<PayrollReportGenerated id={self.id} name={self.report_name!r} format={self.format}>"


# ─────────────────────────────────────────────────────────────────────────────
# PayrollAIInsight  — AI-Driven Insights section
# ─────────────────────────────────────────────────────────────────────────────


class PayrollAIInsight(Base):
    """
    AI-generated payroll insights shown on the Reports dashboard header.
    e.g. "Unusual Overtime Pattern" (HIGH), "Attrition Risk Alert" (MEDIUM), "Salary Benchmarking" (LOW).
    """

    __tablename__ = "payroll_ai_insight"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(InsightSeverity), nullable=False, default=InsightSeverity.MEDIUM)

    department = Column(String(255), nullable=True)
    metric_value = Column(String(100), nullable=True)   # "300% increase", "5 employees"
    insight_type = Column(String(100), nullable=True)   # "overtime", "attrition", "benchmarking"

    is_active = Column(Boolean, nullable=False, default=True)
    is_dismissed = Column(Boolean, nullable=False, default=False)
    dismissed_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_pai_severity_active", "severity", "is_active"),
    )

    def __repr__(self):
        return f"<PayrollAIInsight id={self.id} severity={self.severity} title={self.title!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# PayrollReportConfig  — Configuration tab (singleton)
# ─────────────────────────────────────────────────────────────────────────────


class PayrollReportConfig(Base):
    """
    Org-wide report settings shown in Configuration tab → Report Configuration section:
    Default Report Format | Retention Period | Auto-generate scheduled | Email notifications
    """

    __tablename__ = "payroll_report_config"

    id = Column(Integer, primary_key=True, index=True)

    default_format = Column(String(10), nullable=False, default="PDF")   # PDF | Excel | CSV
    retention_months = Column(Integer, nullable=False, default=12)
    auto_generate_scheduled = Column(Boolean, nullable=False, default=True)
    email_notifications = Column(Boolean, nullable=False, default=True)

    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PayrollReportConfig default_format={self.default_format}>"


# ─────────────────────────────────────────────────────────────────────────────
# PayrollComplianceReport  — Compliance tab
# ─────────────────────────────────────────────────────────────────────────────


class PayrollComplianceReport(Base):
    """
    Statutory compliance reports shown in the Compliance tab:
    Form 24Q | ECR | ESI Monthly Return | PT Challan | Form 16 | Salary Certificate | PF Annual Return
    Columns: Report Name | Type | Frequency | Due Date | Status | Period | Auto | Actions
    """

    __tablename__ = "payroll_compliance_report"

    id = Column(Integer, primary_key=True, index=True)

    report_name = Column(String(255), nullable=False, index=True)
    compliance_type = Column(Enum(ComplianceType), nullable=False)
    frequency = Column(Enum(ReportFrequency), nullable=False)

    period_label = Column(String(100), nullable=True)   # "2023-24", "March 2024"
    period_month = Column(Integer, nullable=True)
    period_year = Column(Integer, nullable=True)

    due_date = Column(DateTime, nullable=True)
    is_overdue = Column(Boolean, nullable=False, default=False)

    status = Column(Enum(ReportStatus), nullable=False, default=ReportStatus.PENDING)
    auto_generate = Column(Boolean, nullable=False, default=True)

    file_path = Column(String(500), nullable=True)
    generated_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    submitted_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_pcr_type_status", "compliance_type", "status"),
        Index("ix_pcr_due_date", "due_date"),
    )

    def __repr__(self):
        return (
            f"<PayrollComplianceReport id={self.id} "
            f"name={self.report_name!r} status={self.status}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PayrollAnalyticsDashboard  — Analytics tab cards
# ─────────────────────────────────────────────────────────────────────────────


class PayrollAnalyticsDashboard(Base):
    """
    Dashboard cards shown in the Payroll Analytics Dashboards (Analytics tab):
    Total Payroll Cost Visualization | Average Salary by Dept/Grade |
    Salary Distribution Analysis | Statutory Contribution Trends |
    Payroll Cost Forecasting | Budget vs Actual | Attrition Impact
    """

    __tablename__ = "payroll_analytics_dashboard"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    chart_type = Column(Enum(ChartType), nullable=False, default=ChartType.BAR)
    frequency = Column(Enum(ReportFrequency), nullable=False, default=ReportFrequency.MONTHLY)
    metrics = Column(Text, nullable=True)         # JSON: ["Total Cost", "Cost per Employee"]
    access_level = Column(String(50), nullable=True)  # "Manager+", "HR+", "Executive"
    is_real_time = Column(Boolean, nullable=False, default=False)

    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    last_refreshed_at = Column(DateTime, nullable=True)

    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_pad_active_order", "is_active", "sort_order"),
    )

    def __repr__(self):
        return f"<PayrollAnalyticsDashboard id={self.id} title={self.title!r}>"