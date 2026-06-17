from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Date, Text, JSON, func
)
from database import Base


# ── Dashboard Summary (top cards: Total Payroll Cost, Statutory Deductions,
#     Average Salary, Compliance Status) ──────────────────────────────────────
class PayrollSummaryMetric(Base):
    __tablename__ = "payroll_summary_metrics"

    id                  = Column(Integer, primary_key=True, index=True)
    metric_key          = Column(String(50), nullable=False)   # total_payroll_cost / statutory_deductions / average_salary / compliance_status
    period              = Column(String(20), nullable=False)   # e.g. "2024-03"
    value               = Column(Float, nullable=False, default=0.0)
    change_percent      = Column(Float, nullable=True)         # e.g. 2.3 (vs last month)
    change_label        = Column(String(100), nullable=True)   # "from last month" / "year-on-year"
    extra               = Column(JSON, default=dict)           # e.g. {"of_total": 0.0}

    created_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── AI-Driven Insights (Unusual Overtime Pattern, Attrition Risk Alert,
#     Salary Benchmarking) ────────────────────────────────────────────────────
class AIInsight(Base):
    __tablename__ = "ai_insights"

    id              = Column(Integer, primary_key=True, index=True)
    title           = Column(String(200), nullable=False)
    description     = Column(Text, nullable=False)
    severity        = Column(String(20), nullable=False, default="LOW")  # HIGH | MEDIUM | LOW
    category        = Column(String(50), nullable=True)   # overtime / attrition / benchmarking / other
    is_dismissed    = Column(Boolean, default=False)

    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── Standard Reports (Monthly Payroll Register, Dept-wise Summary,
#     Bank Transfer Summary, Statutory Reports, etc.) ────────────────────────
class StandardReport(Base):
    __tablename__ = "standard_reports"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(200), nullable=False)         # "Monthly Payroll Register"
    description      = Column(Text, nullable=True)                 # "Detailed monthly payroll register..."
    department       = Column(String(100), nullable=False, default="All")  # All / Finance / HR
    frequency        = Column(String(50), nullable=False)          # Monthly / Quarterly / Monthly/Quarterly / On Demand
    status           = Column(String(20), nullable=False, default="pending")  # generated / pending
    formats          = Column(JSON, default=list)                  # ["pdf", "excel"]
    last_generated   = Column(Date, nullable=True)
    is_active        = Column(Boolean, default=True)
    display_order    = Column(Integer, default=0)

    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now(), nullable=False)


# ── Compliance Reports (Form 24Q, ECR, ESI Monthly Return, PT Challan,
#     Form 16, Salary Certificate, PF Annual Return) ─────────────────────────
class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(200), nullable=False)     # "Form 24Q (TDS quarterly return)"
    type             = Column(String(20), nullable=False)      # TDS / PF / ESI / PT / Certificate
    frequency        = Column(String(50), nullable=False)      # Quarterly / Monthly / Annual / On Demand
    due_date         = Column(Date, nullable=True)
    is_overdue       = Column(Boolean, default=False)
    status           = Column(String(20), nullable=False, default="pending")  # generated / submitted / in-progress / pending / available
    period           = Column(String(50), nullable=True)       # "March 2024" / "2023-24" / "N/A"
    auto_generate    = Column(Boolean, default=True)
    file_path        = Column(String(500), nullable=True)

    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now(), nullable=False)


# ── Analytics Dashboards (Total Payroll Cost Viz, Avg Salary by Dept/Grade,
#     Salary Distribution, Statutory Contribution Trends, Forecasting,
#     Budget vs Actual, Attrition Impact) ─────────────────────────────────────
class AnalyticsDashboard(Base):
    __tablename__ = "analytics_dashboards"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(200), nullable=False)     # "Total Payroll Cost Visualization"
    description      = Column(Text, nullable=True)
    chart_type       = Column(String(50), nullable=False)      # bar / combo / histogram / line
    refresh_cycle    = Column(String(50), nullable=False)       # Real-time / Daily / Monthly / Quarterly
    access_level     = Column(String(50), nullable=False)       # Manager+ / HR+ / Finance+ / Executive
    metrics          = Column(JSON, default=list)              # ["Total Cost", "Cost per Employee", ...]
    last_updated     = Column(Date, nullable=True)
    color_theme      = Column(String(30), nullable=True)        # for UI accent (blue/green/purple/etc.)
    display_order    = Column(Integer, default=0)
    is_active        = Column(Boolean, default=True)


# ── Generated Reports (output instances) ──────────────────────────────────────
class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id               = Column(Integer, primary_key=True, index=True)
    source_type      = Column(String(20), nullable=False)      # standard / compliance / custom
    source_id        = Column(Integer, nullable=True)           # FK reference (no hard constraint to keep flexible)
    report_name      = Column(String(200), nullable=False)
    period           = Column(String(50), nullable=True)
    department       = Column(String(100), nullable=True)
    format           = Column(String(20), nullable=False)       # pdf / excel / csv
    file_path        = Column(String(500), nullable=True)
    generated_by     = Column(String(150), nullable=True)
    status           = Column(String(20), nullable=False, default="completed")

    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── Scheduled Reports (Monthly Payroll Register, Bank Transfer Summary etc.) ──
class ScheduledReport(Base):
    __tablename__ = "scheduled_reports"

    id               = Column(Integer, primary_key=True, index=True)
    source_type      = Column(String(20), nullable=False)      # standard / compliance / custom
    source_id        = Column(Integer, nullable=True)
    report_name      = Column(String(200), nullable=False)
    schedule_text    = Column(String(100), nullable=False)      # "1st of every month"
    next_run         = Column(Date, nullable=True)
    recipients       = Column(JSON, default=list)               # ["hr@company.com", ...]
    formats          = Column(JSON, default=list)               # ["pdf", "excel"]
    status           = Column(String(20), nullable=False, default="active")  # active / paused
    is_active        = Column(Boolean, default=True)

    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now(), nullable=False)


# ── Report Configuration (Configuration tab: system-wide settings) ───────────
class ReportConfiguration(Base):
    """Single-row table holding global report settings."""
    __tablename__ = "report_configuration"

    id                              = Column(Integer, primary_key=True, autoincrement=True)
    default_format                  = Column(String(10), nullable=False, default="PDF")    # PDF / Excel / CSV
    retention_period_months         = Column(Integer, nullable=False, default=12)
    auto_generate_scheduled_reports = Column(Boolean, nullable=False, default=True)
    email_notifications             = Column(Boolean, nullable=False, default=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)


# ── Custom Reports (created via Report Builder) ──────────────────────────────
class CustomReport(Base):
    __tablename__ = "custom_reports"

    id               = Column(Integer, primary_key=True, index=True)

    # Step 1: Report Details
    name             = Column(String(200), nullable=False)
    description      = Column(Text, nullable=True)
    category         = Column(String(100), nullable=False, default="Payroll")
    data_source      = Column(String(100), nullable=False, default="Payroll Data")

    # Step 2: Columns & Data — list of selected column keys
    columns          = Column(JSON, default=list)   # ["employee_id", "name", "basic_salary", ...]

    # Step 3: Filters & Sorting
    departments      = Column(JSON, default=list)   # ["Engineering", "Sales", ...]
    date_start       = Column(Date, nullable=True)
    date_end         = Column(Date, nullable=True)
    salary_min       = Column(Float, nullable=True)
    salary_max       = Column(Float, nullable=True)
    sort_by          = Column(String(100), nullable=True)
    sort_order       = Column(String(4), nullable=True, default="asc")  # asc / desc

    # Step 4: Format & Schedule
    formats          = Column(JSON, default=list)    # ["pdf", "excel", "csv"]
    schedule_frequency = Column(String(50), nullable=False, default="Don't schedule")
    add_as_dashboard_widget = Column(Boolean, default=False)

    created_date     = Column(Date, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now(), nullable=False)


# ── Report Column Definitions (master list shown in Report Builder
#     "Select Data Columns" step — Basic / Salary / Deductions groups) ────────
class ReportColumnDefinition(Base):
    __tablename__ = "report_column_definitions"

    id               = Column(Integer, primary_key=True, index=True)
    key              = Column(String(100), nullable=False, unique=True)   # "employee_id", "basic_salary"
    label            = Column(String(150), nullable=False)                # "Employee ID"
    description      = Column(String(255), nullable=True)                 # "Unique employee identifier"
    data_type        = Column(String(20), nullable=False, default="text") # text / currency / date / number
    group            = Column(String(50), nullable=False, default="Basic")# Basic / Salary / Deductions
    display_order    = Column(Integer, default=0)
