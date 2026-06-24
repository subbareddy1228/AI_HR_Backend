
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



class PayrollReportCustom(Base):


    __tablename__ = "payroll_report_custom"

    id = Column(Integer, primary_key=True, index=True)
    report_name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(ReportCategory), nullable=False, default=ReportCategory.SALARY)
    data_source = Column(Enum(DataSource), nullable=False, default=DataSource.PAYROLL_DATA)
    department_filter = Column(Text, nullable=True)      
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)
    min_salary = Column(Numeric(12, 2), nullable=True, default=0)
    max_salary = Column(Numeric(12, 2), nullable=True, default=500000)
    sort_column = Column(String(100), nullable=True)
    sort_direction = Column(String(5), nullable=True, default="asc")
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



class PayrollReportCustomCol(Base):

    __tablename__ = "payroll_report_custom_col"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(
        Integer,
        ForeignKey("payroll_report_custom.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    column_key = Column(String(100), nullable=False)      
    column_label = Column(String(255), nullable=False)    
    column_group = Column(Enum(ColumnGroup), nullable=False, default=ColumnGroup.BASIC)
    data_type = Column(String(20), nullable=False, default="text")  
    sort_order = Column(Integer, nullable=False, default=0)
    is_selected = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("report_id", "column_key", name="uq_payroll_rpt_col"),
    )

    def __repr__(self):
        return f"<PayrollReportCustomCol report={self.report_id} key={self.column_key}>"


class PayrollReportSchedule(Base):


    __tablename__ = "payroll_report_schedule"

    id = Column(Integer, primary_key=True, index=True)

    report_name = Column(String(255), nullable=False, index=True)
    custom_report_id = Column(
        Integer, ForeignKey("payroll_report_custom.id"), nullable=True
    )

    frequency = Column(
        Enum(ReportFrequency), nullable=False, default=ReportFrequency.MONTHLY
    )
    day_of_month = Column(Integer, nullable=True)   
    day_of_week = Column(Integer, nullable=True)    
    time_of_day = Column(String(10), nullable=True)  
    recipients = Column(Text, nullable=False)        
    export_format = Column(Text, nullable=False, default='["PDF","Excel"]')  
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


class PayrollReportGenerated(Base):


    __tablename__ = "payroll_report_generated"

    id = Column(Integer, primary_key=True, index=True)

    report_name = Column(String(255), nullable=False, index=True)
    custom_report_id = Column(
        Integer, ForeignKey("payroll_report_custom.id"), nullable=True
    )
    schedule_id = Column(
        Integer, ForeignKey("payroll_report_schedule.id"), nullable=True
    )

    period_label = Column(String(100), nullable=True)   
    period_month = Column(Integer, nullable=True)
    period_year = Column(Integer, nullable=True)

    format = Column(Enum(ReportFormat), nullable=False, default=ReportFormat.PDF)
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    download_count = Column(Integer, nullable=False, default=0)

    generated_by_label = Column(String(255), nullable=True) 
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



class PayrollAIInsight(Base):


    __tablename__ = "payroll_ai_insight"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(InsightSeverity), nullable=False, default=InsightSeverity.MEDIUM)

    department = Column(String(255), nullable=True)
    metric_value = Column(String(100), nullable=True)   
    insight_type = Column(String(100), nullable=True)   

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


class PayrollReportConfig(Base):

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



class PayrollComplianceReport(Base):


    __tablename__ = "payroll_compliance_report"

    id = Column(Integer, primary_key=True, index=True)

    report_name = Column(String(255), nullable=False, index=True)
    compliance_type = Column(Enum(ComplianceType), nullable=False)
    frequency = Column(Enum(ReportFrequency), nullable=False)
    period_label = Column(String(100), nullable=True)   
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



class PayrollAnalyticsDashboard(Base):


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