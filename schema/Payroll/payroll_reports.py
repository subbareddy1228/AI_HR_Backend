from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date, datetime


# ── Dashboard Summary ──────────────────────────────────────────────────────
class SummaryMetricOut(BaseModel):
    id: int
    metric_key: str
    period: str
    value: float
    change_percent: Optional[float] = None
    change_label: Optional[str] = None
    extra: Dict[str, Any] = {}

    class Config:
        from_attributes = True


# ── AI Insights ─────────────────────────────────────────────────────────────
class AIInsightOut(BaseModel):
    id: int
    title: str
    description: str
    severity: str
    category: Optional[str] = None
    is_dismissed: bool

    class Config:
        from_attributes = True


# ── Standard Reports ─────────────────────────────────────────────────────────
class StandardReportBase(BaseModel):
    name: str
    description: Optional[str] = None
    department: str = "All"
    frequency: str
    formats: List[str] = []
    display_order: int = 0

class StandardReportCreate(StandardReportBase):
    pass

class StandardReportUpdate(StandardReportBase):
    pass

class StandardReportOut(StandardReportBase):
    id: int
    status: str
    last_generated: Optional[date] = None
    is_active: bool

    class Config:
        from_attributes = True


class GenerateStandardReportRequest(BaseModel):
    format: str = "pdf"   # pdf / excel
    period: Optional[str] = None
    department: Optional[str] = None


class ScheduleStandardReportRequest(BaseModel):
    schedule_text: str
    recipients: List[str] = []
    formats: List[str] = ["pdf"]


# ── Compliance Reports ───────────────────────────────────────────────────────
class ComplianceReportBase(BaseModel):
    name: str
    type: str
    frequency: str
    due_date: Optional[date] = None
    period: Optional[str] = None
    auto_generate: bool = True

class ComplianceReportCreate(ComplianceReportBase):
    pass

class ComplianceReportOut(ComplianceReportBase):
    id: int
    status: str
    is_overdue: bool
    file_path: Optional[str] = None

    class Config:
        from_attributes = True


# ── Analytics Dashboards ─────────────────────────────────────────────────────
class AnalyticsDashboardOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    chart_type: str
    refresh_cycle: str
    access_level: str
    metrics: List[str] = []
    last_updated: Optional[date] = None
    color_theme: Optional[str] = None
    display_order: int = 0
    is_active: bool

    class Config:
        from_attributes = True


class AnalyticsDataRequest(BaseModel):
    """Used for fetching actual chart data for a given dashboard."""
    period: Optional[str] = None
    department: Optional[str] = None


# ── Generated Reports ────────────────────────────────────────────────────────
class GeneratedReportOut(BaseModel):
    id: int
    source_type: str
    source_id: Optional[int] = None
    report_name: str
    period: Optional[str] = None
    department: Optional[str] = None
    format: str
    file_path: Optional[str] = None
    generated_by: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Scheduled Reports ────────────────────────────────────────────────────────
class ScheduledReportBase(BaseModel):
    source_type: str
    source_id: Optional[int] = None
    report_name: str
    schedule_text: str
    next_run: Optional[date] = None
    recipients: List[str] = []
    formats: List[str] = []

class ScheduledReportCreate(ScheduledReportBase):
    pass

class ScheduledReportUpdate(BaseModel):
    schedule_text: Optional[str] = None
    next_run: Optional[date] = None
    recipients: Optional[List[str]] = None
    formats: Optional[List[str]] = None
    status: Optional[str] = None

class ScheduledReportOut(ScheduledReportBase):
    id: int
    status: str
    is_active: bool

    class Config:
        from_attributes = True


# ── Report Configuration ─────────────────────────────────────────────────────
class ReportConfigurationOut(BaseModel):
    default_format: str
    retention_period_months: int
    auto_generate_scheduled_reports: bool
    email_notifications: bool

    class Config:
        from_attributes = True

class ReportConfigurationUpdate(BaseModel):
    default_format: Optional[str] = None
    retention_period_months: Optional[int] = None
    auto_generate_scheduled_reports: Optional[bool] = None
    email_notifications: Optional[bool] = None


# ── Report Column Definitions ────────────────────────────────────────────────
class ReportColumnDefinitionOut(BaseModel):
    id: int
    key: str
    label: str
    description: Optional[str] = None
    data_type: str
    group: str
    display_order: int

    class Config:
        from_attributes = True


# ── Custom Reports / Report Builder ──────────────────────────────────────────
class CustomReportCreate(BaseModel):
    # Step 1
    name: str
    description: Optional[str] = None
    category: str = "Payroll"
    data_source: str = "Payroll Data"

    # Step 2
    columns: List[str] = []

    # Step 3
    departments: List[str] = []
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    sort_by: Optional[str] = None
    sort_order: str = "asc"

    # Step 4
    formats: List[str] = ["pdf"]
    schedule_frequency: str = "Don't schedule"
    add_as_dashboard_widget: bool = False


class CustomReportUpdate(CustomReportCreate):
    pass


class CustomReportOut(CustomReportCreate):
    id: int
    created_date: Optional[date] = None

    class Config:
        from_attributes = True


# ── Export Config (Configuration tab Quick Action) ──────────────────────────
class ExportConfigOut(BaseModel):
    file_path: str
    filename: str
