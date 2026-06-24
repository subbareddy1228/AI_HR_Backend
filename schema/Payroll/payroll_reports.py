"""
schema/Payroll/payroll_reports.py
-----------------------------------
Pydantic v2 schemas for the Payroll Reports & Analytics module.
Follows naming and style from schema/Payroll/payroll_run.py, salary_structure.py etc.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from model.Payroll.payroll_reports import (
    ChartType,
    ColumnGroup,
    ComplianceType,
    DataSource,
    InsightSeverity,
    ReportCategory,
    ReportFormat,
    ReportFrequency,
    ReportStatus,
)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard KPI cards
# ─────────────────────────────────────────────────────────────────────────────


class PayrollReportKPIResponse(BaseModel):
    total_payroll_cost: Decimal
    payroll_cost_change_pct: float          # +2.3% from last month
    statutory_deductions: Decimal
    statutory_deductions_pct: float         # 0.0% of total
    average_salary: Decimal
    average_salary_yoy_pct: float           # +5.2% year-on-year
    compliance_status_pct: float            # 100.0
    compliance_label: str                   # "All compliant"


# ─────────────────────────────────────────────────────────────────────────────
# AI Insights
# ─────────────────────────────────────────────────────────────────────────────


class AIInsightCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    severity: InsightSeverity = InsightSeverity.MEDIUM
    department: Optional[str] = None
    metric_value: Optional[str] = None
    insight_type: Optional[str] = None
    valid_until: Optional[datetime] = None


class AIInsightDismiss(BaseModel):
    dismissed_by: int


class AIInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    severity: InsightSeverity
    department: Optional[str]
    metric_value: Optional[str]
    insight_type: Optional[str]
    is_active: bool
    is_dismissed: bool
    dismissed_at: Optional[datetime]
    generated_at: datetime
    valid_until: Optional[datetime]
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Standard Reports
# ─────────────────────────────────────────────────────────────────────────────


class StandardReportItem(BaseModel):
    report_name: str
    description: str
    category: ReportCategory
    report_type: str
    frequency: ReportFrequency
    department: Optional[str] = None
    status: ReportStatus
    last_generated_at: Optional[datetime] = None


class StandardReportsResponse(BaseModel):
    total: int
    reports: List[StandardReportItem]


# ─────────────────────────────────────────────────────────────────────────────
# Compliance Reports
# ─────────────────────────────────────────────────────────────────────────────


class ComplianceReportCreate(BaseModel):
    report_name: str = Field(..., max_length=255)
    compliance_type: ComplianceType
    frequency: ReportFrequency
    period_label: Optional[str] = None
    period_month: Optional[int] = Field(None, ge=1, le=12)
    period_year: Optional[int] = None
    due_date: Optional[datetime] = None
    auto_generate: bool = True


class ComplianceReportUpdate(BaseModel):
    status: Optional[ReportStatus] = None
    file_path: Optional[str] = None
    generated_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[int] = None
    is_overdue: Optional[bool] = None
    period_label: Optional[str] = None


class ComplianceReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_name: str
    compliance_type: ComplianceType
    frequency: ReportFrequency
    period_label: Optional[str]
    period_month: Optional[int]
    period_year: Optional[int]
    due_date: Optional[datetime]
    is_overdue: bool
    status: ReportStatus
    auto_generate: bool
    file_path: Optional[str]
    generated_at: Optional[datetime]
    submitted_at: Optional[datetime]
    submitted_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]


# ─────────────────────────────────────────────────────────────────────────────
# Analytics Dashboard Cards
# ─────────────────────────────────────────────────────────────────────────────


class AnalyticsDashboardCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    chart_type: ChartType = ChartType.BAR
    frequency: ReportFrequency = ReportFrequency.MONTHLY
    metrics: Optional[List[str]] = None
    access_level: Optional[str] = None
    sort_order: int = 0
    is_real_time: bool = False
    created_by: Optional[int] = None


class AnalyticsDashboardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    chart_type: Optional[ChartType] = None
    frequency: Optional[ReportFrequency] = None
    metrics: Optional[List[str]] = None
    access_level: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    is_real_time: Optional[bool] = None


class AnalyticsDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str]
    chart_type: ChartType
    frequency: ReportFrequency
    metrics: Optional[str]          # raw JSON string
    access_level: Optional[str]
    sort_order: int
    is_active: bool
    is_real_time: bool
    last_refreshed_at: Optional[datetime]
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]


# ─────────────────────────────────────────────────────────────────────────────
# Generated Reports
# ─────────────────────────────────────────────────────────────────────────────


class GeneratedReportCreate(BaseModel):
    report_name: str = Field(..., max_length=255)
    custom_report_id: Optional[int] = None
    schedule_id: Optional[int] = None
    period_label: Optional[str] = None
    period_month: Optional[int] = Field(None, ge=1, le=12)
    period_year: Optional[int] = None
    format: ReportFormat = ReportFormat.PDF
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    generated_by_label: Optional[str] = None
    generated_by: Optional[int] = None
    expires_at: Optional[datetime] = None


class GeneratedReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_name: str
    custom_report_id: Optional[int]
    schedule_id: Optional[int]
    period_label: Optional[str]
    period_month: Optional[int]
    period_year: Optional[int]
    format: ReportFormat
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    file_size_display: Optional[str]    # computed: "2.4 MB"
    download_count: int
    generated_by_label: Optional[str]
    generated_by: Optional[int]
    generated_at: datetime
    expires_at: Optional[datetime]
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Scheduled Reports
# ─────────────────────────────────────────────────────────────────────────────


class ReportScheduleCreate(BaseModel):
    report_name: str = Field(..., max_length=255)
    custom_report_id: Optional[int] = None
    frequency: ReportFrequency
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    time_of_day: Optional[str] = None
    recipients: List[str] = Field(..., min_length=1)
    export_formats: List[ReportFormat] = Field(default_factory=lambda: [ReportFormat.PDF])
    created_by: Optional[int] = None


class ReportScheduleUpdate(BaseModel):
    frequency: Optional[ReportFrequency] = None
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    recipients: Optional[List[str]] = None
    export_formats: Optional[List[ReportFormat]] = None
    is_active: Optional[bool] = None
    next_run_at: Optional[datetime] = None


class ReportScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_name: str
    custom_report_id: Optional[int]
    frequency: ReportFrequency
    day_of_month: Optional[int]
    day_of_week: Optional[int]
    time_of_day: Optional[str]
    recipients: str          # JSON string
    export_format: str       # JSON string
    is_active: bool
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]


# ─────────────────────────────────────────────────────────────────────────────
# Report Configuration
# ─────────────────────────────────────────────────────────────────────────────


class ReportConfigUpsert(BaseModel):
    default_format: str = Field(default="PDF", pattern="^(PDF|Excel|CSV)$")
    retention_months: int = Field(default=12, ge=1, le=120)
    auto_generate_scheduled: bool = True
    email_notifications: bool = True
    updated_by: Optional[int] = None


class ReportConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    default_format: str
    retention_months: int
    auto_generate_scheduled: bool
    email_notifications: bool
    updated_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]


# ─────────────────────────────────────────────────────────────────────────────
# Custom Report Builder
# ─────────────────────────────────────────────────────────────────────────────


class CustomReportColumnIn(BaseModel):
    column_key: str = Field(..., max_length=100)
    column_label: str = Field(..., max_length=255)
    column_group: ColumnGroup
    data_type: str = "text"
    sort_order: int = 0
    is_selected: bool = True


class CustomReportColumnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    column_key: str
    column_label: str
    column_group: ColumnGroup
    data_type: str
    sort_order: int
    is_selected: bool


class CustomReportCreate(BaseModel):
    """Full payload from the 4-step Report Builder wizard (Create Report button)."""
    # Step 1
    report_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    category: ReportCategory = ReportCategory.SALARY
    data_source: DataSource = DataSource.PAYROLL_DATA
    # Step 2
    columns: List[CustomReportColumnIn] = Field(default_factory=list)
    # Step 3
    department_filter: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_salary: Optional[Decimal] = Field(None, ge=0)
    max_salary: Optional[Decimal] = Field(None, ge=0)
    sort_column: Optional[str] = None
    sort_direction: Optional[str] = Field(None, pattern="^(asc|desc)$")
    # Step 4
    export_pdf: bool = True
    export_excel: bool = True
    export_csv: bool = False
    schedule_frequency: ReportFrequency = ReportFrequency.DONT_SCHEDULE
    add_as_dashboard_widget: bool = False
    created_by: Optional[int] = None


class CustomReportUpdate(BaseModel):
    report_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ReportCategory] = None
    data_source: Optional[DataSource] = None
    department_filter: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_salary: Optional[Decimal] = None
    max_salary: Optional[Decimal] = None
    export_pdf: Optional[bool] = None
    export_excel: Optional[bool] = None
    export_csv: Optional[bool] = None
    schedule_frequency: Optional[ReportFrequency] = None
    add_as_dashboard_widget: Optional[bool] = None
    is_active: Optional[bool] = None
    updated_by: Optional[int] = None


class CustomReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_name: str
    description: Optional[str]
    category: ReportCategory
    data_source: DataSource
    department_filter: Optional[str]   # JSON string
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    min_salary: Optional[Decimal]
    max_salary: Optional[Decimal]
    sort_column: Optional[str]
    sort_direction: Optional[str]
    export_pdf: bool
    export_excel: bool
    export_csv: bool
    schedule_frequency: ReportFrequency
    add_as_dashboard_widget: bool
    is_active: bool
    created_by: Optional[int]
    columns: Optional[List[CustomReportColumnResponse]] = None
    created_at: datetime
    updated_at: Optional[datetime]


# ─────────────────────────────────────────────────────────────────────────────
# Live data sub-report response schemas
# ─────────────────────────────────────────────────────────────────────────────


class MonthlyPayrollSummaryItem(BaseModel):
    run_id: int
    month: int
    month_name: str
    year: int
    total_employees: int
    total_gross: Decimal
    total_deductions: Decimal
    total_net_pay: Decimal
    status: str
    run_date: str


class DeptPayrollItem(BaseModel):
    department: Optional[str]
    headcount: int
    total_gross: Decimal
    total_deductions: Decimal
    total_net_pay: Decimal
    avg_net_pay: Decimal
    pct_of_total: Optional[float] = None


class LocationPayrollItem(BaseModel):
    location: Optional[str]
    headcount: int
    total_gross: Decimal
    total_net_pay: Decimal
    pct_of_total: Optional[float] = None


class GradeSalaryItem(BaseModel):
    grade: Optional[str]
    headcount: int
    avg_monthly_salary: Decimal
    min_monthly_salary: Decimal
    max_monthly_salary: Decimal


class SalaryComponentBreakdown(BaseModel):
    total_basic: Decimal
    total_hra: Decimal
    total_special_allowance: Decimal
    total_gross: Decimal
    total_pf_employee: Decimal
    total_pf_employer: Decimal
    total_esi_employee: Decimal
    total_esi_employer: Decimal
    total_professional_tax: Decimal
    total_tds: Decimal
    total_deductions: Decimal
    total_net_pay: Decimal


class BankTransferSummaryItem(BaseModel):
    bank_name: str
    transaction_count: int
    total_amount: Decimal
    failed_count: int
    success_rate: float


class PFRemittanceItem(BaseModel):
    employee_id: int
    employee_code: Optional[str]
    employee_name: str
    department: Optional[str]
    basic: Decimal
    pf_employee: Decimal
    pf_employer: Decimal
    total_pf: Decimal


class ESIRemittanceItem(BaseModel):
    employee_id: int
    employee_name: str
    department: Optional[str]
    gross_salary: Decimal
    esi_employee: Decimal
    esi_employer: Decimal
    total_esi: Decimal


class TDSReportItem(BaseModel):
    employee_id: int
    employee_code: Optional[str]
    employee_name: str
    department: Optional[str]
    designation: Optional[str]
    gross_salary: Decimal
    tds_deducted: Decimal


class PTDeductionItem(BaseModel):
    employee_id: int
    employee_name: str
    department: Optional[str]
    gross_salary: Decimal
    professional_tax: Decimal


class PayrollVarianceItem(BaseModel):
    month: int
    month_name: str
    year: int
    total_gross: Decimal
    total_net_pay: Decimal
    gross_variance: Decimal
    net_variance: Decimal
    gross_variance_pct: float
    net_variance_pct: float


class CostCenterItem(BaseModel):
    cost_center: Optional[str]
    department: Optional[str]
    headcount: int
    total_gross: Decimal
    total_net_pay: Decimal


class HeadcountTrendItem(BaseModel):
    month: int
    month_name: str
    year: int
    headcount: int
    total_payroll_cost: Decimal
    avg_cost_per_head: Decimal


# ─────────────────────────────────────────────────────────────────────────────
# Misc request/response helpers
# ─────────────────────────────────────────────────────────────────────────────


class ExportDataRequest(BaseModel):
    format: ReportFormat = ReportFormat.PDF
    report_name: Optional[str] = None
    period_month: Optional[int] = Field(None, ge=1, le=12)
    period_year: Optional[int] = None
    department: Optional[str] = None


class CategorySummaryItem(BaseModel):
    category: str
    description: str
    count: int