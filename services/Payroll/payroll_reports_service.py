"""
services/Payroll/payroll_reports_service.py
--------------------------------------------
Business-logic layer for Payroll Reports & Analytics.
Follows conventions from services/Payroll/payroll_service.py,
statutory_service.py, salary_service.py etc.

Service classes:
  - PayrollReportKPIService         : Dashboard KPI cards
  - PayrollAIInsightService         : AI Insights CRUD + dismiss + seed
  - StandardReportService           : Static standard report catalogue
  - PayrollComplianceService        : Compliance report CRUD + overdue detection
  - PayrollAnalyticsDashboardService: Analytics cards CRUD + seed
  - PayrollGeneratedReportService   : Generated report file history
  - PayrollReportScheduleService    : Schedule CRUD + toggle
  - PayrollReportConfigService      : Org-wide config upsert + export + reset
  - PayrollCustomReportService      : Report Builder CRUD + CSV export runner
  - PayrollDataReportService        : Live data queries (dept, PF, TDS, etc.)
"""

from __future__ import annotations

import csv
import io
import json
import logging
from calendar import month_name as MONTH_NAMES
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from model.Payroll.bank_transfer import BankTransfer, TransferStatus
from model.Payroll.payroll_reports import (
    ChartType,
    ComplianceType,
    InsightSeverity,
    PayrollAIInsight,
    PayrollAnalyticsDashboard,
    PayrollComplianceReport,
    PayrollReportConfig,
    PayrollReportCustom,
    PayrollReportCustomCol,
    PayrollReportGenerated,
    PayrollReportSchedule,
    ReportCategory,
    ReportFormat,
    ReportFrequency,
    ReportStatus,
)
from model.Payroll.payroll_run import PayrollRun, PayrollRunDetail
from model.Payroll.salary_structure import EmployeeSalaryMapping
from model.onboarding.employee import Employee
from schema.Payroll.payroll_reports import (
    AIInsightCreate,
    AIInsightDismiss,
    AnalyticsDashboardCreate,
    AnalyticsDashboardUpdate,
    BankTransferSummaryItem,
    ComplianceReportCreate,
    ComplianceReportUpdate,
    CostCenterItem,
    CustomReportCreate,
    CustomReportUpdate,
    DeptPayrollItem,
    ESIRemittanceItem,
    ExportDataRequest,
    GeneratedReportCreate,
    GradeSalaryItem,
    HeadcountTrendItem,
    LocationPayrollItem,
    MonthlyPayrollSummaryItem,
    PTDeductionItem,
    PFRemittanceItem,
    PayrollReportKPIResponse,
    PayrollVarianceItem,
    ReportConfigUpsert,
    ReportScheduleCreate,
    ReportScheduleUpdate,
    SalaryComponentBreakdown,
    StandardReportItem,
    TDSReportItem,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Seed data constants
# ─────────────────────────────────────────────────────────────────────────────

STANDARD_REPORTS: List[Dict] = [
    {"report_name": "Monthly Payroll Register",                  "category": ReportCategory.SALARY,        "report_type": "Summary",   "frequency": ReportFrequency.MONTHLY,   "department": "All",     "description": "Comprehensive monthly payroll register with all earnings and deductions"},
    {"report_name": "Department-wise Payroll Summary",           "category": ReportCategory.SALARY,        "report_type": "Summary",   "frequency": ReportFrequency.MONTHLY,   "department": "All",     "description": "Payroll expenses summarised per department"},
    {"report_name": "Location-wise Payroll Summary",             "category": ReportCategory.SALARY,        "report_type": "Analysis",  "frequency": ReportFrequency.MONTHLY,   "department": "All",     "description": "Payroll breakdown by geographical work location"},
    {"report_name": "Grade-wise Salary Analysis",                "category": ReportCategory.SALARY,        "report_type": "Analysis",  "frequency": ReportFrequency.QUARTERLY, "department": "All",     "description": "Salary analysis grouped by employee grade"},
    {"report_name": "Bank Transfer Summary",                     "category": ReportCategory.BANK_TRANSFER, "report_type": "Summary",   "frequency": ReportFrequency.MONTHLY,   "department": "All",     "description": "Bank-wise payment summary with success/fail rates"},
    {"report_name": "Statutory Reports (PF, ESI, PT, TDS)",     "category": ReportCategory.STATUTORY,     "report_type": "Statutory", "frequency": ReportFrequency.MONTHLY,   "department": "Finance", "description": "Combined statutory deductions report"},
    {"report_name": "Cost Center Wise Payroll",                  "category": ReportCategory.SALARY,        "report_type": "Analysis",  "frequency": ReportFrequency.MONTHLY,   "department": "Finance", "description": "Payroll costs allocated by cost center"},
    {"report_name": "Arrear Register",                           "category": ReportCategory.DEDUCTION,     "report_type": "Detailed",  "frequency": ReportFrequency.MONTHLY,   "department": "Finance", "description": "Arrear salary payments and adjustments ledger"},
    {"report_name": "Payroll Variance Report (Month-over-Month)","category": ReportCategory.SALARY,        "report_type": "Analysis",  "frequency": ReportFrequency.MONTHLY,   "department": "All",     "description": "Month-over-month payroll cost variance analysis"},
    {"report_name": "Headcount and Payroll Cost Trends",         "category": ReportCategory.SALARY,        "report_type": "Trend",     "frequency": ReportFrequency.MONTHLY,   "department": "HR",      "description": "Headcount and total payroll cost trend over time"},
]

COMPLIANCE_SEED: List[Dict] = [
    {"report_name": "Form 24Q (TDS quarterly return)",  "compliance_type": ComplianceType.TDS,         "frequency": ReportFrequency.QUARTERLY},
    {"report_name": "ECR (PF monthly return)",           "compliance_type": ComplianceType.PF,          "frequency": ReportFrequency.MONTHLY},
    {"report_name": "ESI Monthly Return",                "compliance_type": ComplianceType.ESI,         "frequency": ReportFrequency.MONTHLY},
    {"report_name": "PT Challan Reports",                "compliance_type": ComplianceType.PT,          "frequency": ReportFrequency.MONTHLY},
    {"report_name": "Form 16 (Annual TDS certificate)", "compliance_type": ComplianceType.TDS,         "frequency": ReportFrequency.ANNUAL},
    {"report_name": "Salary Certificate",                "compliance_type": ComplianceType.CERTIFICATE, "frequency": ReportFrequency.ON_DEMAND},
    {"report_name": "PF Annual Return (Form 3A, 6A)",  "compliance_type": ComplianceType.PF,          "frequency": ReportFrequency.ANNUAL},
]

ANALYTICS_SEED: List[Dict] = [
    {"title": "Total Payroll Cost Visualization",     "description": "Interactive visualization of total payroll costs",        "chart_type": ChartType.BAR,       "frequency": ReportFrequency.MONTHLY,   "is_real_time": True,  "access_level": "Manager+",  "metrics": ["Total Cost", "Cost per Employee", "Department Breakdown"]},
    {"title": "Average Salary by Department/Grade",   "description": "Average salary analysis across departments and grades",   "chart_type": ChartType.COMBO,     "frequency": ReportFrequency.DAILY,     "is_real_time": True,  "access_level": "HR+",       "metrics": ["Average Salary", "Median Salary", "Salary Range"]},
    {"title": "Salary Distribution Analysis",         "description": "Analysis of salary distribution across organization",     "chart_type": ChartType.HISTOGRAM, "frequency": ReportFrequency.MONTHLY,   "is_real_time": False, "access_level": "HR+",       "metrics": ["Distribution Curve", "Percentiles", "Outliers"]},
    {"title": "Statutory Contribution Trends",        "description": "Trend analysis of statutory contributions (PF, ESI, PT)", "chart_type": ChartType.LINE,      "frequency": ReportFrequency.MONTHLY,   "is_real_time": False, "access_level": "Finance+",  "metrics": ["PF Trends", "ESI Trends", "PT Trends"]},
    {"title": "Payroll Cost Forecasting",             "description": "Forecast future payroll costs based on trends",            "chart_type": ChartType.LINE,      "frequency": ReportFrequency.MONTHLY,   "is_real_time": False, "access_level": "Executive", "metrics": ["3-Month Forecast", "6-Month Forecast", "Variance Analysis"]},
    {"title": "Budget vs Actual Payroll Comparison",  "description": "Comparison of budgeted vs actual payroll costs",          "chart_type": ChartType.COMBO,     "frequency": ReportFrequency.MONTHLY,   "is_real_time": False, "access_level": "Manager+",  "metrics": ["Variance %", "Budget Utilization", "Department Performance"]},
    {"title": "Attrition Impact on Payroll Costs",   "description": "Analysis of attrition impact on payroll",                 "chart_type": ChartType.BAR,       "frequency": ReportFrequency.QUARTERLY, "is_real_time": False, "access_level": "HR+",       "metrics": ["Attrition Rate", "Cost Impact", "Replacement Cost"]},
]

AVAILABLE_COLUMNS = [
    {"column_key": "employee_id",     "column_label": "Employee ID",     "description": "Unique employee identifier",       "column_group": "Basic",      "data_type": "text"},
    {"column_key": "name",            "column_label": "Name",            "description": "Employee full name",               "column_group": "Basic",      "data_type": "text"},
    {"column_key": "department",      "column_label": "Department",      "description": "Department assignment",            "column_group": "Basic",      "data_type": "text"},
    {"column_key": "designation",     "column_label": "Designation",     "description": "Job title/position",              "column_group": "Basic",      "data_type": "text"},
    {"column_key": "location",        "column_label": "Location",        "description": "Work location",                   "column_group": "Basic",      "data_type": "text"},
    {"column_key": "grade",           "column_label": "Grade",           "description": "Employee grade/level",            "column_group": "Basic",      "data_type": "text"},
    {"column_key": "basic_salary",    "column_label": "Basic Salary",    "description": "Basic salary component",          "column_group": "Salary",     "data_type": "currency"},
    {"column_key": "gross_salary",    "column_label": "Gross Salary",    "description": "Total earnings before deductions", "column_group": "Salary",     "data_type": "currency"},
    {"column_key": "net_salary",      "column_label": "Net Salary",      "description": "Take-home salary",               "column_group": "Salary",     "data_type": "currency"},
    {"column_key": "pf_employee",     "column_label": "PF (Employee)",   "description": "Employee PF contribution",        "column_group": "Deductions", "data_type": "currency"},
    {"column_key": "pf_employer",     "column_label": "PF (Employer)",   "description": "Employer PF contribution",        "column_group": "Deductions", "data_type": "currency"},
    {"column_key": "esi_employee",    "column_label": "ESI (Employee)",  "description": "Employee ESI contribution",       "column_group": "Deductions", "data_type": "currency"},
    {"column_key": "esi_employer",    "column_label": "ESI (Employer)",  "description": "Employer ESI contribution",       "column_group": "Deductions", "data_type": "currency"},
    {"column_key": "tds",             "column_label": "TDS",             "description": "Tax deducted at source",          "column_group": "Deductions", "data_type": "currency"},
    {"column_key": "professional_tax","column_label": "Professional Tax","description": "State professional tax",          "column_group": "Deductions", "data_type": "currency"},
    {"column_key": "leave_balance",   "column_label": "Leave Balance",   "description": "Available leave balance",         "column_group": "Attendance", "data_type": "number"},
    {"column_key": "attendance_days", "column_label": "Attendance Days", "description": "Number of days present",          "column_group": "Attendance", "data_type": "number"},
    {"column_key": "overtime_hours",  "column_label": "Overtime Hours",  "description": "Total overtime worked",           "column_group": "Attendance", "data_type": "number"},
]


def _404(label: str):
    raise HTTPException(status_code=404, detail=f"{label} not found")


def _get_or_404(db: Session, model, pk: int, label: str):
    obj = db.get(model, pk)
    if not obj:
        _404(label)
    return obj


def _size_display(size_bytes: Optional[int]) -> Optional[str]:
    if not size_bytes:
        return None
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


# ─────────────────────────────────────────────────────────────────────────────
# PayrollReportKPIService
# ─────────────────────────────────────────────────────────────────────────────


class PayrollReportKPIService:

    @staticmethod
    def get_kpi(db: Session) -> PayrollReportKPIResponse:
        now = datetime.utcnow()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

        def _run_totals(year: int, month: int):
            run = db.execute(
                select(PayrollRun).where(
                    PayrollRun.run_year == year, PayrollRun.run_month == month
                )
            ).scalar_one_or_none()
            if not run:
                return Decimal(0), Decimal(0)
            return Decimal(str(run.total_gross or 0)), Decimal(str(run.total_deductions or 0))

        gross, deductions = _run_totals(now.year, now.month)
        prev_gross, _ = _run_totals(last_month_start.year, last_month_start.month)

        change_pct = (
            round(float((gross - prev_gross) / prev_gross * 100), 1)
            if prev_gross else 0.0
        )

        avg_ctc_row = db.execute(
            select(func.avg(EmployeeSalaryMapping.annual_ctc))
        ).scalar_one() or 0
        avg_monthly = Decimal(str(round(float(avg_ctc_row) / 12, 2)))

        total_compliance = db.execute(
            select(func.count(PayrollComplianceReport.id))
        ).scalar_one()
        compliant = db.execute(
            select(func.count(PayrollComplianceReport.id)).where(
                PayrollComplianceReport.is_overdue == False
            )
        ).scalar_one()
        compliance_pct = round(compliant / total_compliance * 100, 1) if total_compliance else 100.0

        stat_pct = round(float(deductions) / float(gross) * 100, 1) if gross else 0.0

        return PayrollReportKPIResponse(
            total_payroll_cost=gross,
            payroll_cost_change_pct=change_pct,
            statutory_deductions=deductions,
            statutory_deductions_pct=stat_pct,
            average_salary=avg_monthly,
            average_salary_yoy_pct=5.2,
            compliance_status_pct=compliance_pct,
            compliance_label="All compliant" if compliance_pct == 100.0 else f"{compliance_pct}% compliant",
        )


# ─────────────────────────────────────────────────────────────────────────────
# PayrollAIInsightService
# ─────────────────────────────────────────────────────────────────────────────


class PayrollAIInsightService:

    @staticmethod
    def seed_defaults(db: Session) -> None:
        count = db.execute(select(func.count(PayrollAIInsight.id))).scalar_one()
        if count:
            return
        for obj in [
            PayrollAIInsight(title="Unusual Overtime Pattern",   description="Sales department showing 300% overtime increase",        severity=InsightSeverity.HIGH,   department="Sales",       metric_value="300%",         insight_type="overtime"),
            PayrollAIInsight(title="Attrition Risk Alert",       description="5 employees in Engineering show high flight risk",       severity=InsightSeverity.MEDIUM, department="Engineering", metric_value="5 employees",  insight_type="attrition"),
            PayrollAIInsight(title="Salary Benchmarking",        description="Market parity suggests 8-12% salary adjustment for Grade B", severity=InsightSeverity.LOW, department=None,       metric_value="8-12%",        insight_type="benchmarking"),
        ]:
            db.add(obj)
        db.commit()

    @staticmethod
    def list_active(db: Session) -> List[PayrollAIInsight]:
        return db.execute(
            select(PayrollAIInsight)
            .where(PayrollAIInsight.is_active == True, PayrollAIInsight.is_dismissed == False)
            .order_by(
                case(
                    (PayrollAIInsight.severity == InsightSeverity.HIGH, 0),
                    (PayrollAIInsight.severity == InsightSeverity.MEDIUM, 1),
                    else_=2,
                )
            )
        ).scalars().all()

    @staticmethod
    def create(db: Session, payload: AIInsightCreate) -> PayrollAIInsight:
        obj = PayrollAIInsight(**payload.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def dismiss(db: Session, insight_id: int, payload: AIInsightDismiss) -> PayrollAIInsight:
        obj = _get_or_404(db, PayrollAIInsight, insight_id, "AI Insight")
        obj.is_dismissed = True
        obj.dismissed_by = payload.dismissed_by
        obj.dismissed_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# StandardReportService
# ─────────────────────────────────────────────────────────────────────────────


class StandardReportService:

    @staticmethod
    def list_reports(
        search: Optional[str] = None,
        category: Optional[str] = None,
        department: Optional[str] = None,
        frequency: Optional[str] = None,
    ) -> List[StandardReportItem]:
        result = []
        for r in STANDARD_REPORTS:
            if search and search.lower() not in r["report_name"].lower():
                continue
            if category and r["category"].value != category:
                continue
            if department and r.get("department") not in (department, "All"):
                continue
            if frequency and r["frequency"].value != frequency:
                continue
            result.append(
                StandardReportItem(
                    report_name=r["report_name"],
                    description=r["description"],
                    category=r["category"],
                    report_type=r["report_type"],
                    frequency=r["frequency"],
                    department=r.get("department"),
                    status=ReportStatus.GENERATED,
                    last_generated_at=datetime(2024, 4, 1),
                )
            )
        return result


# ─────────────────────────────────────────────────────────────────────────────
# PayrollComplianceService
# ─────────────────────────────────────────────────────────────────────────────


class PayrollComplianceService:

    @staticmethod
    def seed_defaults(db: Session) -> None:
        if db.execute(select(func.count(PayrollComplianceReport.id))).scalar_one():
            return
        for seed in COMPLIANCE_SEED:
            db.add(PayrollComplianceReport(**seed, status=ReportStatus.PENDING))
        db.commit()

    @staticmethod
    def list_all(
        db: Session, compliance_type: Optional[ComplianceType] = None
    ) -> List[PayrollComplianceReport]:
        stmt = select(PayrollComplianceReport)
        if compliance_type:
            stmt = stmt.where(PayrollComplianceReport.compliance_type == compliance_type)
        return db.execute(stmt.order_by(PayrollComplianceReport.due_date)).scalars().all()

    @staticmethod
    def get_overdue(db: Session) -> List[PayrollComplianceReport]:
        return db.execute(
            select(PayrollComplianceReport).where(PayrollComplianceReport.is_overdue == True)
        ).scalars().all()

    @staticmethod
    def create(db: Session, payload: ComplianceReportCreate) -> PayrollComplianceReport:
        obj = PayrollComplianceReport(**payload.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(
        db: Session, report_id: int, payload: ComplianceReportUpdate
    ) -> PayrollComplianceReport:
        obj = _get_or_404(db, PayrollComplianceReport, report_id, "Compliance report")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        if obj.due_date and obj.due_date < datetime.utcnow() and obj.status not in (
            ReportStatus.SUBMITTED, ReportStatus.AVAILABLE
        ):
            obj.is_overdue = True
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def generate(db: Session, report_id: int) -> PayrollComplianceReport:
        obj = _get_or_404(db, PayrollComplianceReport, report_id, "Compliance report")
        obj.status = ReportStatus.GENERATED
        obj.generated_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, report_id: int) -> None:
        obj = _get_or_404(db, PayrollComplianceReport, report_id, "Compliance report")
        db.delete(obj)
        db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# PayrollAnalyticsDashboardService
# ─────────────────────────────────────────────────────────────────────────────


class PayrollAnalyticsDashboardService:

    @staticmethod
    def seed_defaults(db: Session) -> None:
        if db.execute(select(func.count(PayrollAnalyticsDashboard.id))).scalar_one():
            return
        for i, seed in enumerate(ANALYTICS_SEED):
            metrics = seed.pop("metrics", [])
            db.add(
                PayrollAnalyticsDashboard(
                    **seed,
                    metrics=json.dumps(metrics),
                    sort_order=i,
                    last_refreshed_at=datetime(2024, 3, 31),
                )
            )
        db.commit()

    @staticmethod
    def list_all(db: Session) -> List[PayrollAnalyticsDashboard]:
        return db.execute(
            select(PayrollAnalyticsDashboard)
            .where(PayrollAnalyticsDashboard.is_active == True)
            .order_by(PayrollAnalyticsDashboard.sort_order)
        ).scalars().all()

    @staticmethod
    def create(db: Session, payload: AnalyticsDashboardCreate) -> PayrollAnalyticsDashboard:
        data = payload.model_dump()
        metrics = data.pop("metrics", None)
        obj = PayrollAnalyticsDashboard(**data, metrics=json.dumps(metrics) if metrics else None)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(
        db: Session, dashboard_id: int, payload: AnalyticsDashboardUpdate
    ) -> PayrollAnalyticsDashboard:
        obj = _get_or_404(db, PayrollAnalyticsDashboard, dashboard_id, "Analytics dashboard")
        data = payload.model_dump(exclude_unset=True)
        metrics = data.pop("metrics", None)
        for k, v in data.items():
            setattr(obj, k, v)
        if metrics is not None:
            obj.metrics = json.dumps(metrics)
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, dashboard_id: int) -> None:
        obj = _get_or_404(db, PayrollAnalyticsDashboard, dashboard_id, "Analytics dashboard")
        db.delete(obj)
        db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# PayrollGeneratedReportService
# ─────────────────────────────────────────────────────────────────────────────


class PayrollGeneratedReportService:

    @staticmethod
    def list_all(
        db: Session,
        report_name: Optional[str] = None,
        format: Optional[ReportFormat] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PayrollReportGenerated], int]:
        stmt = select(PayrollReportGenerated)
        if report_name:
            stmt = stmt.where(PayrollReportGenerated.report_name.ilike(f"%{report_name}%"))
        if format:
            stmt = stmt.where(PayrollReportGenerated.format == format)
        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = db.execute(
            stmt.order_by(PayrollReportGenerated.generated_at.desc()).offset(skip).limit(limit)
        ).scalars().all()
        return rows, total

    @staticmethod
    def create(db: Session, payload: GeneratedReportCreate) -> PayrollReportGenerated:
        obj = PayrollReportGenerated(**payload.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def increment_download(db: Session, report_id: int) -> PayrollReportGenerated:
        obj = _get_or_404(db, PayrollReportGenerated, report_id, "Generated report")
        obj.download_count += 1
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, report_id: int) -> None:
        obj = _get_or_404(db, PayrollReportGenerated, report_id, "Generated report")
        db.delete(obj)
        db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# PayrollReportScheduleService
# ─────────────────────────────────────────────────────────────────────────────


class PayrollReportScheduleService:

    @staticmethod
    def list_all(
        db: Session, is_active: Optional[bool] = None
    ) -> List[PayrollReportSchedule]:
        stmt = select(PayrollReportSchedule)
        if is_active is not None:
            stmt = stmt.where(PayrollReportSchedule.is_active == is_active)
        return db.execute(stmt.order_by(PayrollReportSchedule.report_name)).scalars().all()

    @staticmethod
    def create(db: Session, payload: ReportScheduleCreate) -> PayrollReportSchedule:
        data = payload.model_dump()
        recipients = data.pop("recipients")
        export_formats = data.pop("export_formats")
        obj = PayrollReportSchedule(
            **data,
            recipients=json.dumps(recipients),
            export_format=json.dumps([f.value if hasattr(f, "value") else f for f in export_formats]),
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(
        db: Session, schedule_id: int, payload: ReportScheduleUpdate
    ) -> PayrollReportSchedule:
        obj = _get_or_404(db, PayrollReportSchedule, schedule_id, "Report schedule")
        data = payload.model_dump(exclude_unset=True)
        recipients = data.pop("recipients", None)
        export_formats = data.pop("export_formats", None)
        for k, v in data.items():
            setattr(obj, k, v)
        if recipients is not None:
            obj.recipients = json.dumps(recipients)
        if export_formats is not None:
            obj.export_format = json.dumps([f.value if hasattr(f, "value") else f for f in export_formats])
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def toggle_active(db: Session, schedule_id: int) -> PayrollReportSchedule:
        obj = _get_or_404(db, PayrollReportSchedule, schedule_id, "Report schedule")
        obj.is_active = not obj.is_active
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, schedule_id: int) -> None:
        obj = _get_or_404(db, PayrollReportSchedule, schedule_id, "Report schedule")
        db.delete(obj)
        db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# PayrollReportConfigService
# ─────────────────────────────────────────────────────────────────────────────


class PayrollReportConfigService:

    @staticmethod
    def get(db: Session) -> PayrollReportConfig:
        obj = db.execute(select(PayrollReportConfig)).scalar_one_or_none()
        if not obj:
            obj = PayrollReportConfig()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj

    @staticmethod
    def upsert(db: Session, payload: ReportConfigUpsert) -> PayrollReportConfig:
        obj = db.execute(select(PayrollReportConfig)).scalar_one_or_none()
        if obj:
            for k, v in payload.model_dump(exclude_unset=True).items():
                setattr(obj, k, v)
            obj.updated_at = datetime.utcnow()
        else:
            obj = PayrollReportConfig(**payload.model_dump())
            db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def export_csv(db: Session) -> str:
        obj = PayrollReportConfigService.get(db)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Setting", "Value"])
        writer.writerow(["Default Report Format", obj.default_format])
        writer.writerow(["Retention Period (months)", obj.retention_months])
        writer.writerow(["Auto-generate Scheduled Reports", obj.auto_generate_scheduled])
        writer.writerow(["Email Notifications for Completed Reports", obj.email_notifications])
        return output.getvalue()

    @staticmethod
    def reset_defaults(db: Session, updated_by: Optional[int] = None) -> PayrollReportConfig:
        return PayrollReportConfigService.upsert(db, ReportConfigUpsert(updated_by=updated_by))


# ─────────────────────────────────────────────────────────────────────────────
# PayrollCustomReportService
# ─────────────────────────────────────────────────────────────────────────────


class PayrollCustomReportService:

    @staticmethod
    def get_available_columns() -> List[Dict]:
        return AVAILABLE_COLUMNS

    @staticmethod
    def create(db: Session, payload: CustomReportCreate) -> PayrollReportCustom:
        data = payload.model_dump(exclude={"columns"})
        dept_filter = data.pop("department_filter", None)
        data["department_filter"] = json.dumps(dept_filter) if dept_filter else None
        obj = PayrollReportCustom(**data)
        db.add(obj)
        db.flush()
        for col in payload.columns:
            db.add(PayrollReportCustomCol(report_id=obj.id, **col.model_dump()))
        db.commit()
        db.refresh(obj)
        logger.info("PayrollReportCustom created id=%s name=%s", obj.id, obj.report_name)
        return obj

    @staticmethod
    def list_all(
        db: Session,
        is_active: Optional[bool] = True,
        category: Optional[ReportCategory] = None,
    ) -> List[PayrollReportCustom]:
        stmt = select(PayrollReportCustom)
        if is_active is not None:
            stmt = stmt.where(PayrollReportCustom.is_active == is_active)
        if category:
            stmt = stmt.where(PayrollReportCustom.category == category)
        return db.execute(stmt.order_by(PayrollReportCustom.created_at.desc())).scalars().all()

    @staticmethod
    def get_by_id(db: Session, report_id: int) -> PayrollReportCustom:
        return _get_or_404(db, PayrollReportCustom, report_id, "Custom report")

    @staticmethod
    def update(
        db: Session, report_id: int, payload: CustomReportUpdate
    ) -> PayrollReportCustom:
        obj = _get_or_404(db, PayrollReportCustom, report_id, "Custom report")
        data = payload.model_dump(exclude_unset=True)
        dept_filter = data.pop("department_filter", None)
        for k, v in data.items():
            setattr(obj, k, v)
        if dept_filter is not None:
            obj.department_filter = json.dumps(dept_filter)
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, report_id: int) -> None:
        obj = _get_or_404(db, PayrollReportCustom, report_id, "Custom report")
        db.delete(obj)
        db.commit()

    @staticmethod
    def get_columns(db: Session, report_id: int) -> List[PayrollReportCustomCol]:
        return db.execute(
            select(PayrollReportCustomCol)
            .where(PayrollReportCustomCol.report_id == report_id)
            .order_by(PayrollReportCustomCol.sort_order)
        ).scalars().all()

    @staticmethod
    def export_csv(db: Session, report_id: int) -> str:
        obj = _get_or_404(db, PayrollReportCustom, report_id, "Custom report")
        columns = db.execute(
            select(PayrollReportCustomCol)
            .where(
                PayrollReportCustomCol.report_id == report_id,
                PayrollReportCustomCol.is_selected == True,
            )
            .order_by(PayrollReportCustomCol.sort_order)
        ).scalars().all()

        stmt = (
            select(
                Employee.id.label("employee_id"),
                Employee.first_name,
                Employee.last_name,
                Employee.department,
                Employee.designation,
                Employee.location,
                Employee.grade,
                PayrollRunDetail.basic,
                PayrollRunDetail.gross_salary,
                PayrollRunDetail.net_pay,
                PayrollRunDetail.pf_employee,
                PayrollRunDetail.esi_employee,
                PayrollRunDetail.tds,
                PayrollRunDetail.professional_tax,
            ).join(
                PayrollRunDetail, PayrollRunDetail.employee_id == Employee.id, isouter=True
            )
        )
        if obj.department_filter:
            depts = json.loads(obj.department_filter)
            if depts:
                stmt = stmt.where(Employee.department.in_(depts))

        rows = db.execute(stmt).all()
        col_keys = [c.column_key for c in columns]
        col_labels = [c.column_label for c in columns]

        KEY_MAP: Dict[str, Any] = {
            "employee_id": lambda r: r.employee_id,
            "name": lambda r: f"{r.first_name} {r.last_name}",
            "department": lambda r: r.department or "",
            "designation": lambda r: r.designation or "",
            "location": lambda r: r.location or "",
            "grade": lambda r: r.grade or "",
            "basic_salary": lambda r: float(r.basic or 0),
            "gross_salary": lambda r: float(r.gross_salary or 0),
            "net_salary": lambda r: float(r.net_pay or 0),
            "pf_employee": lambda r: float(r.pf_employee or 0),
            "esi_employee": lambda r: float(r.esi_employee or 0),
            "tds": lambda r: float(r.tds or 0),
            "professional_tax": lambda r: float(r.professional_tax or 0),
        }

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(col_labels)
        for row in rows:
            writer.writerow([KEY_MAP.get(k, lambda _: "")(row) for k in col_keys])
        return output.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PayrollDataReportService  — all live data sub-reports
# ─────────────────────────────────────────────────────────────────────────────


class PayrollDataReportService:

    @staticmethod
    def monthly_summary(
        db: Session, month: Optional[int] = None, year: Optional[int] = None
    ) -> List[MonthlyPayrollSummaryItem]:
        stmt = select(PayrollRun)
        if month:
            stmt = stmt.where(PayrollRun.run_month == month)
        if year:
            stmt = stmt.where(PayrollRun.run_year == year)
        runs = db.execute(stmt.order_by(PayrollRun.run_year.desc(), PayrollRun.run_month.desc())).scalars().all()
        return [
            MonthlyPayrollSummaryItem(
                run_id=r.id,
                month=r.run_month,
                month_name=MONTH_NAMES[r.run_month],
                year=r.run_year,
                total_employees=r.total_employees,
                total_gross=Decimal(str(r.total_gross or 0)),
                total_deductions=Decimal(str(r.total_deductions or 0)),
                total_net_pay=Decimal(str(r.total_net_pay or 0)),
                status=r.status,
                run_date=str(r.run_date),
            )
            for r in runs
        ]

    @staticmethod
    def department_wise(db: Session) -> List[DeptPayrollItem]:
        rows = db.execute(
            select(
                PayrollRunDetail.department,
                func.count(PayrollRunDetail.employee_id).label("headcount"),
                func.sum(PayrollRunDetail.gross_salary).label("total_gross"),
                func.sum(PayrollRunDetail.total_deductions).label("total_deductions"),
                func.sum(PayrollRunDetail.net_pay).label("total_net_pay"),
                func.avg(PayrollRunDetail.net_pay).label("avg_net_pay"),
            ).group_by(PayrollRunDetail.department)
        ).all()
        grand = sum(float(r.total_gross or 0) for r in rows)
        return [
            DeptPayrollItem(
                department=r.department,
                headcount=r.headcount,
                total_gross=Decimal(str(r.total_gross or 0)),
                total_deductions=Decimal(str(r.total_deductions or 0)),
                total_net_pay=Decimal(str(r.total_net_pay or 0)),
                avg_net_pay=Decimal(str(round(float(r.avg_net_pay or 0), 2))),
                pct_of_total=round(float(r.total_gross or 0) / grand * 100, 1) if grand else None,
            )
            for r in rows
        ]

    @staticmethod
    def location_wise(db: Session) -> List[LocationPayrollItem]:
        rows = db.execute(
            select(
                Employee.location,
                func.count(Employee.id).label("headcount"),
                func.sum(PayrollRunDetail.gross_salary).label("total_gross"),
                func.sum(PayrollRunDetail.net_pay).label("total_net_pay"),
            )
            .join(PayrollRunDetail, PayrollRunDetail.employee_id == Employee.id, isouter=True)
            .group_by(Employee.location)
        ).all()
        grand = sum(float(r.total_gross or 0) for r in rows)
        return [
            LocationPayrollItem(
                location=r.location,
                headcount=r.headcount,
                total_gross=Decimal(str(r.total_gross or 0)),
                total_net_pay=Decimal(str(r.total_net_pay or 0)),
                pct_of_total=round(float(r.total_gross or 0) / grand * 100, 1) if grand else None,
            )
            for r in rows
        ]

    @staticmethod
    def grade_wise(db: Session) -> List[GradeSalaryItem]:
        rows = db.execute(
            select(
                Employee.grade,
                func.count(Employee.id).label("headcount"),
                func.avg(EmployeeSalaryMapping.annual_ctc).label("avg_ctc"),
                func.min(EmployeeSalaryMapping.annual_ctc).label("min_ctc"),
                func.max(EmployeeSalaryMapping.annual_ctc).label("max_ctc"),
            )
            .join(EmployeeSalaryMapping, EmployeeSalaryMapping.employee_id == Employee.id, isouter=True)
            .group_by(Employee.grade)
        ).all()
        return [
            GradeSalaryItem(
                grade=r.grade,
                headcount=r.headcount,
                avg_monthly_salary=Decimal(str(round(float(r.avg_ctc or 0) / 12, 2))),
                min_monthly_salary=Decimal(str(round(float(r.min_ctc or 0) / 12, 2))),
                max_monthly_salary=Decimal(str(round(float(r.max_ctc or 0) / 12, 2))),
            )
            for r in rows
        ]

    @staticmethod
    def salary_components(
        db: Session,
        payroll_run_id: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> SalaryComponentBreakdown:
        stmt = select(PayrollRunDetail)
        if payroll_run_id:
            stmt = stmt.where(PayrollRunDetail.payroll_run_id == payroll_run_id)
        elif month or year:
            stmt = stmt.join(PayrollRun, PayrollRun.id == PayrollRunDetail.payroll_run_id)
            if month:
                stmt = stmt.where(PayrollRun.run_month == month)
            if year:
                stmt = stmt.where(PayrollRun.run_year == year)
        details = db.execute(stmt).scalars().all()

        def _s(attr): return Decimal(str(round(sum(float(getattr(d, attr) or 0) for d in details), 2)))

        return SalaryComponentBreakdown(
            total_basic=_s("basic"),
            total_hra=_s("hra"),
            total_special_allowance=_s("special_allowance"),
            total_gross=_s("gross_salary"),
            total_pf_employee=_s("pf_employee"),
            total_pf_employer=_s("pf_employee"),
            total_esi_employee=_s("esi_employee"),
            total_esi_employer=_s("esi_employee"),
            total_professional_tax=_s("professional_tax"),
            total_tds=_s("tds"),
            total_deductions=_s("total_deductions"),
            total_net_pay=_s("net_pay"),
        )

    @staticmethod
    def bank_transfer_summary(db: Session) -> List[BankTransferSummaryItem]:
        rows = db.execute(
            select(
                BankTransfer.bank_name,
                func.count(BankTransfer.id).label("cnt"),
                func.sum(BankTransfer.transfer_amount).label("total"),
                func.sum(case((BankTransfer.status == TransferStatus.FAILED, 1), else_=0)).label("failed"),
                func.sum(case((BankTransfer.status == TransferStatus.SUCCESS, 1), else_=0)).label("success"),
            ).group_by(BankTransfer.bank_name)
        ).all()
        return [
            BankTransferSummaryItem(
                bank_name=r.bank_name,
                transaction_count=r.cnt,
                total_amount=Decimal(str(r.total or 0)),
                failed_count=r.failed,
                success_rate=round(float(r.success) / r.cnt * 100, 1) if r.cnt else 0.0,
            )
            for r in rows
        ]

    @staticmethod
    def pf_remittance(
        db: Session, month: Optional[int] = None, year: Optional[int] = None
    ) -> List[PFRemittanceItem]:
        stmt = select(PayrollRunDetail)
        if month or year:
            stmt = stmt.join(PayrollRun, PayrollRun.id == PayrollRunDetail.payroll_run_id)
            if month:
                stmt = stmt.where(PayrollRun.run_month == month)
            if year:
                stmt = stmt.where(PayrollRun.run_year == year)
        details = db.execute(stmt).scalars().all()
        return [
            PFRemittanceItem(
                employee_id=d.employee_id,
                employee_code=d.employee_code,
                employee_name=d.employee_name,
                department=d.department,
                basic=Decimal(str(d.basic)),
                pf_employee=Decimal(str(d.pf_employee)),
                pf_employer=Decimal(str(d.pf_employee)),
                total_pf=Decimal(str(round(float(d.pf_employee) * 2, 2))),
            )
            for d in details
        ]

    @staticmethod
    def esi_remittance(
        db: Session, month: Optional[int] = None, year: Optional[int] = None
    ) -> List[ESIRemittanceItem]:
        stmt = select(PayrollRunDetail)
        if month or year:
            stmt = stmt.join(PayrollRun, PayrollRun.id == PayrollRunDetail.payroll_run_id)
            if month:
                stmt = stmt.where(PayrollRun.run_month == month)
            if year:
                stmt = stmt.where(PayrollRun.run_year == year)
        details = db.execute(stmt).scalars().all()
        return [
            ESIRemittanceItem(
                employee_id=d.employee_id,
                employee_name=d.employee_name,
                department=d.department,
                gross_salary=Decimal(str(d.gross_salary)),
                esi_employee=Decimal(str(d.esi_employee)),
                esi_employer=Decimal(str(d.esi_employee)),
                total_esi=Decimal(str(round(float(d.esi_employee) * 2, 2))),
            )
            for d in details
        ]

    @staticmethod
    def tds_report(
        db: Session, month: Optional[int] = None, year: Optional[int] = None
    ) -> List[TDSReportItem]:
        stmt = select(PayrollRunDetail)
        if month or year:
            stmt = stmt.join(PayrollRun, PayrollRun.id == PayrollRunDetail.payroll_run_id)
            if month:
                stmt = stmt.where(PayrollRun.run_month == month)
            if year:
                stmt = stmt.where(PayrollRun.run_year == year)
        details = db.execute(stmt).scalars().all()
        return [
            TDSReportItem(
                employee_id=d.employee_id,
                employee_code=d.employee_code,
                employee_name=d.employee_name,
                department=d.department,
                designation=d.designation,
                gross_salary=Decimal(str(d.gross_salary)),
                tds_deducted=Decimal(str(d.tds)),
            )
            for d in details
        ]

    @staticmethod
    def pt_deduction(
        db: Session, month: Optional[int] = None, year: Optional[int] = None
    ) -> List[PTDeductionItem]:
        stmt = select(PayrollRunDetail)
        if month or year:
            stmt = stmt.join(PayrollRun, PayrollRun.id == PayrollRunDetail.payroll_run_id)
            if month:
                stmt = stmt.where(PayrollRun.run_month == month)
            if year:
                stmt = stmt.where(PayrollRun.run_year == year)
        details = db.execute(stmt).scalars().all()
        return [
            PTDeductionItem(
                employee_id=d.employee_id,
                employee_name=d.employee_name,
                department=d.department,
                gross_salary=Decimal(str(d.gross_salary)),
                professional_tax=Decimal(str(d.professional_tax)),
            )
            for d in details
        ]

    @staticmethod
    def payroll_variance(db: Session) -> List[PayrollVarianceItem]:
        runs = db.execute(
            select(PayrollRun).order_by(PayrollRun.run_year, PayrollRun.run_month)
        ).scalars().all()
        result = []
        for i, run in enumerate(runs):
            prev = runs[i - 1] if i > 0 else None
            pg = float(run.total_gross or 0)
            pn = float(run.total_net_pay or 0)
            prev_g = float(prev.total_gross or 0) if prev else 0
            prev_n = float(prev.total_net_pay or 0) if prev else 0
            result.append(
                PayrollVarianceItem(
                    month=run.run_month,
                    month_name=MONTH_NAMES[run.run_month],
                    year=run.run_year,
                    total_gross=Decimal(str(pg)),
                    total_net_pay=Decimal(str(pn)),
                    gross_variance=Decimal(str(round(pg - prev_g, 2))),
                    net_variance=Decimal(str(round(pn - prev_n, 2))),
                    gross_variance_pct=round((pg - prev_g) / prev_g * 100, 2) if prev_g else 0.0,
                    net_variance_pct=round((pn - prev_n) / prev_n * 100, 2) if prev_n else 0.0,
                )
            )
        return result

    @staticmethod
    def cost_center(db: Session) -> List[CostCenterItem]:
        rows = db.execute(
            select(
                PayrollRunDetail.department,
                func.count(PayrollRunDetail.employee_id).label("headcount"),
                func.sum(PayrollRunDetail.gross_salary).label("total_gross"),
                func.sum(PayrollRunDetail.net_pay).label("total_net_pay"),
            ).group_by(PayrollRunDetail.department)
        ).all()
        return [
            CostCenterItem(
                cost_center=r.department,
                department=r.department,
                headcount=r.headcount,
                total_gross=Decimal(str(r.total_gross or 0)),
                total_net_pay=Decimal(str(r.total_net_pay or 0)),
            )
            for r in rows
        ]

    @staticmethod
    def headcount_trends(db: Session) -> List[HeadcountTrendItem]:
        runs = db.execute(
            select(PayrollRun).order_by(PayrollRun.run_year, PayrollRun.run_month)
        ).scalars().all()
        return [
            HeadcountTrendItem(
                month=r.run_month,
                month_name=MONTH_NAMES[r.run_month],
                year=r.run_year,
                headcount=r.total_employees,
                total_payroll_cost=Decimal(str(r.total_gross or 0)),
                avg_cost_per_head=Decimal(str(round(float(r.total_gross or 0) / r.total_employees, 2))) if r.total_employees else Decimal(0),
            )
            for r in runs
        ]

    @staticmethod
    def export_as_csv(headers: List[str], rows: List[List[Any]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        return output.getvalue()