
from __future__ import annotations

import io
import logging
from calendar import month_name
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.database import get_db
from model.Payroll.payroll_reports import (
    ComplianceType,
    ReportCategory,
    ReportFormat,
)
from model.Payroll.payroll_run import PayrollRun, PayrollRunDetail
from model.Payroll.salary_slip import SalarySlip
from schema.Payroll.payroll_reports import (
    AIInsightCreate,
    AIInsightDismiss,
    AIInsightResponse,
    AnalyticsDashboardCreate,
    AnalyticsDashboardResponse,
    AnalyticsDashboardUpdate,
    BankTransferSummaryItem,
    CategorySummaryItem,
    ComplianceReportCreate,
    ComplianceReportResponse,
    ComplianceReportUpdate,
    CostCenterItem,
    CustomReportColumnResponse,
    CustomReportCreate,
    CustomReportResponse,
    CustomReportUpdate,
    DeptPayrollItem,
    ESIRemittanceItem,
    ExportDataRequest,
    GeneratedReportCreate,
    GeneratedReportResponse,
    GradeSalaryItem,
    HeadcountTrendItem,
    LocationPayrollItem,
    MonthlyPayrollSummaryItem,
    PTDeductionItem,
    PFRemittanceItem,
    PayrollReportKPIResponse,
    PayrollVarianceItem,
    ReportConfigResponse,
    ReportConfigUpsert,
    ReportScheduleCreate,
    ReportScheduleResponse,
    ReportScheduleUpdate,
    SalaryComponentBreakdown,
    StandardReportItem,
    StandardReportsResponse,
    TDSReportItem,
)
from services.Payroll.payroll_reports_service import (
    PayrollAIInsightService,
    PayrollAnalyticsDashboardService,
    PayrollComplianceService,
    PayrollCustomReportService,
    PayrollDataReportService,
    PayrollGeneratedReportService,
    PayrollReportConfigService,
    PayrollReportKPIService,
    PayrollReportScheduleService,
    StandardReportService,
    _size_display,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payroll-reports", tags=["Payroll"])


@router.get("/summary")
def payroll_summary(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Original endpoint — total gross/deductions/net grouped by dept."""
    run = db.execute(
        select(PayrollRun).where(
            PayrollRun.run_year == year,
            PayrollRun.run_month == month,
        )
    ).scalar_one_or_none()

    if not run:
        return {
            "year": year, "month": month,
            "month_name": month_name[month],
            "total_gross": 0, "total_deductions": 0, "total_net_pay": 0,
            "department_breakdown": [],
            "note": "No payroll run found for this period",
        }

    details = db.execute(
        select(PayrollRunDetail).where(PayrollRunDetail.payroll_run_id == run.id)
    ).scalars().all()

    dept_map: dict = {}
    for d in details:
        dept = d.department or "Unknown"
        if dept not in dept_map:
            dept_map[dept] = {"department": dept, "employee_count": 0,
                              "total_gross": 0.0, "total_deductions": 0.0, "total_net_pay": 0.0}
        dept_map[dept]["employee_count"] += 1
        dept_map[dept]["total_gross"] += float(d.gross_salary or 0)
        dept_map[dept]["total_deductions"] += float(d.total_deductions or 0)
        dept_map[dept]["total_net_pay"] += float(d.net_pay or 0)

    for v in dept_map.values():
        v["total_gross"] = round(v["total_gross"], 2)
        v["total_deductions"] = round(v["total_deductions"], 2)
        v["total_net_pay"] = round(v["total_net_pay"], 2)

    return {
        "year": year, "month": month, "month_name": month_name[month],
        "payroll_run_id": run.id, "status": run.status,
        "total_employees": run.total_employees,
        "total_gross": float(run.total_gross or 0),
        "total_deductions": float(run.total_deductions or 0),
        "total_net_pay": float(run.total_net_pay or 0),
        "department_breakdown": list(dept_map.values()),
    }


@router.get("/employee/{employee_id}")
def employee_payroll_history(employee_id: int, db: Session = Depends(get_db)):

    slips = db.execute(
        select(SalarySlip)
        .where(SalarySlip.employee_id == employee_id)
        .order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())
    ).scalars().all()

    run_details = db.execute(
        select(PayrollRunDetail).where(PayrollRunDetail.employee_id == employee_id)
    ).scalars().all()
    detail_index = {d.payroll_run_id: d for d in run_details}

    history = []
    for s in slips:
        detail = detail_index.get(s.payroll_run_id)
        entry: dict = {
            "slip_id": s.id,
            "slip_month": s.slip_month,
            "month_name": month_name[s.slip_month],
            "slip_year": s.slip_year,
            "gross_salary": float(s.gross_salary or 0),
            "total_deductions": float(s.total_deductions or 0),
            "net_pay": float(s.net_pay or 0),
            "is_published": s.is_published,
        }
        if detail:
            entry.update({
                "days_worked": detail.days_worked,
                "days_absent": detail.days_absent,
                "basic": float(detail.basic or 0),
                "hra": float(detail.hra or 0),
                "pf_employee": float(detail.pf_employee or 0),
                "tds": float(detail.tds or 0),
            })
        history.append(entry)

    return {"employee_id": employee_id, "total_slips": len(history), "history": history}


@router.get("/cost-breakdown/{run_id}")
def cost_breakdown(run_id: int, db: Session = Depends(get_db)):

    run = db.execute(select(PayrollRun).where(PayrollRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")

    details = db.execute(
        select(PayrollRunDetail).where(PayrollRunDetail.payroll_run_id == run_id)
    ).scalars().all()

    return {
        "payroll_run_id": run_id,
        "run_month": run.run_month, "month_name": month_name[run.run_month],
        "run_year": run.run_year, "status": run.status,
        "total_employees": run.total_employees,
        "earnings_breakdown": {
            "total_basic": round(sum(float(d.basic or 0) for d in details), 2),
            "total_hra": round(sum(float(d.hra or 0) for d in details), 2),
            "total_special_allowance": round(sum(float(d.special_allowance or 0) for d in details), 2),
            "total_gross": float(run.total_gross or 0),
        },
        "deductions_breakdown": {
            "total_pf_employee": round(sum(float(d.pf_employee or 0) for d in details), 2),
            "total_esi_employee": round(sum(float(d.esi_employee or 0) for d in details), 2),
            "total_professional_tax": round(sum(float(d.professional_tax or 0) for d in details), 2),
            "total_tds": round(sum(float(d.tds or 0) for d in details), 2),
            "total_deductions": float(run.total_deductions or 0),
        },
        "total_net_pay": float(run.total_net_pay or 0),
        "employee_details": [
            {
                "employee_id": d.employee_id, "employee_code": d.employee_code,
                "employee_name": d.employee_name, "department": d.department,
                "days_worked": d.days_worked, "gross_salary": float(d.gross_salary or 0),
                "total_deductions": float(d.total_deductions or 0), "net_pay": float(d.net_pay or 0),
            }
            for d in details
        ],
    }



@router.get(
    "/dashboard/kpi",
    response_model=PayrollReportKPIResponse,
    summary="KPI cards — Total Payroll Cost, Statutory Deductions, Avg Salary, Compliance",
)
def get_dashboard_kpi(db: Session = Depends(get_db)):
    PayrollComplianceService.seed_defaults(db)
    return PayrollReportKPIService.get_kpi(db)


@router.get(
    "/dashboard/insights",
    response_model=List[AIInsightResponse],
    summary="AI-Driven Insights — active, ordered HIGH → MEDIUM → LOW",
)
def get_ai_insights(db: Session = Depends(get_db)):
    PayrollAIInsightService.seed_defaults(db)
    return PayrollAIInsightService.list_active(db)


@router.post(
    "/dashboard/insights",
    response_model=AIInsightResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an AI Insight",
)
def create_ai_insight(payload: AIInsightCreate, db: Session = Depends(get_db)):
    return PayrollAIInsightService.create(db, payload)


@router.patch(
    "/dashboard/insights/{insight_id}/dismiss",
    response_model=AIInsightResponse,
    summary="Dismiss an AI Insight (hide from dashboard)",
)
def dismiss_insight(
    insight_id: int,
    payload: AIInsightDismiss,
    db: Session = Depends(get_db),
):
    return PayrollAIInsightService.dismiss(db, insight_id, payload)


@router.get(
    "/standard/",
    response_model=StandardReportsResponse,
    summary="Standard Reports tab — pre-defined payroll report catalogue",
)
def list_standard_reports(
    search: Optional[str] = Query(None, description="Search by report name"),
    category: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    frequency: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    reports = StandardReportService.list_reports(
        search=search, category=category,
        department=department, frequency=frequency,
    )
    return StandardReportsResponse(total=len(reports), reports=reports)


@router.get(
    "/standard/categories",
    response_model=List[CategorySummaryItem],
    summary="Report category counts for sidebar/filter",
)
def get_categories():
    return [
        CategorySummaryItem(category="Salary Reports",    description="Monthly payroll, cost analysis, salary breakdowns", count=9),
        CategorySummaryItem(category="Statutory Reports", description="PF, ESI, PT, TDS returns and compliance forms",       count=7),
        CategorySummaryItem(category="Deduction Reports", description="Loan, advances, arrears and other deductions",       count=4),
        CategorySummaryItem(category="Bank Transfers",    description="Payment summaries, reconciliation, failed payments", count=4),
    ]


@router.post(
    "/standard/export",
    summary="Trigger generation of a standard report (Export Data / Add Report buttons)",
)
def export_standard_report(
    payload: ExportDataRequest,
    db: Session = Depends(get_db),
):
    record = PayrollGeneratedReportService.create(
        db,
        GeneratedReportCreate(
            report_name=payload.report_name or "Payroll Export",
            period_month=payload.period_month,
            period_year=payload.period_year,
            format=payload.format,
            generated_by_label="System",
        ),
    )
    return {"message": "Report generation initiated", "generated_report_id": record.id}



@router.get(
    "/compliance/",
    response_model=List[ComplianceReportResponse],
    summary="Compliance tab — Statutory Compliance Reports (Form 24Q, ECR, ESI, PT, Form 16…)",
)
def list_compliance_reports(
    compliance_type: Optional[ComplianceType] = Query(None),
    db: Session = Depends(get_db),
):
    PayrollComplianceService.seed_defaults(db)
    return PayrollComplianceService.list_all(db, compliance_type=compliance_type)


@router.get(
    "/compliance/overdue",
    response_model=List[ComplianceReportResponse],
    summary="Overdue compliance reports (0 Overdue badge in UI)",
)
def get_overdue_compliance(db: Session = Depends(get_db)):
    PayrollComplianceService.seed_defaults(db)
    return PayrollComplianceService.get_overdue(db)


@router.post(
    "/compliance/",
    response_model=ComplianceReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new compliance report entry",
)
def create_compliance_report(
    payload: ComplianceReportCreate,
    db: Session = Depends(get_db),
):
    return PayrollComplianceService.create(db, payload)


@router.patch(
    "/compliance/{report_id}",
    response_model=ComplianceReportResponse,
    summary="Update compliance report status / file path",
)
def update_compliance_report(
    report_id: int,
    payload: ComplianceReportUpdate,
    db: Session = Depends(get_db),
):
    return PayrollComplianceService.update(db, report_id, payload)


@router.patch(
    "/compliance/{report_id}/generate",
    response_model=ComplianceReportResponse,
    summary="Mark compliance report as Generated (action button on each row)",
)
def generate_compliance_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    return PayrollComplianceService.generate(db, report_id)


@router.delete(
    "/compliance/{report_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a compliance report entry",
)
def delete_compliance_report(report_id: int, db: Session = Depends(get_db)):
    PayrollComplianceService.delete(db, report_id)



@router.get(
    "/analytics/",
    response_model=List[AnalyticsDashboardResponse],
    summary="Analytics tab — Payroll Analytics Dashboard cards",
)
def list_analytics_dashboards(db: Session = Depends(get_db)):
    PayrollAnalyticsDashboardService.seed_defaults(db)
    return PayrollAnalyticsDashboardService.list_all(db)


@router.post(
    "/analytics/",
    response_model=AnalyticsDashboardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new analytics dashboard card",
)
def create_analytics_dashboard(
    payload: AnalyticsDashboardCreate,
    db: Session = Depends(get_db),
):
    return PayrollAnalyticsDashboardService.create(db, payload)


@router.patch(
    "/analytics/{dashboard_id}",
    response_model=AnalyticsDashboardResponse,
    summary="Update an analytics dashboard card (⋮ menu actions)",
)
def update_analytics_dashboard(
    dashboard_id: int,
    payload: AnalyticsDashboardUpdate,
    db: Session = Depends(get_db),
):
    return PayrollAnalyticsDashboardService.update(db, dashboard_id, payload)


@router.delete(
    "/analytics/{dashboard_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an analytics dashboard card",
)
def delete_analytics_dashboard(dashboard_id: int, db: Session = Depends(get_db)):
    PayrollAnalyticsDashboardService.delete(db, dashboard_id)


@router.get(
    "/generated/",
    response_model=List[GeneratedReportResponse],
    summary="Generated tab — Report Name, Period, Date, Generated By, Format, Size, Downloads",
)
def list_generated_reports(
    report_name: Optional[str] = Query(None),
    format: Optional[ReportFormat] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows, _total = PayrollGeneratedReportService.list_all(
        db, report_name=report_name, format=format, skip=skip, limit=limit
    )
    result = []
    for r in rows:
        d = {c.key: getattr(r, c.key) for c in r.__table__.columns}
        d["file_size_display"] = _size_display(r.file_size_bytes)
        result.append(GeneratedReportResponse.model_validate(d))
    return result


@router.post(
    "/generated/",
    response_model=GeneratedReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a generated report file",
)
def record_generated_report(
    payload: GeneratedReportCreate,
    db: Session = Depends(get_db),
):
    obj = PayrollGeneratedReportService.create(db, payload)
    d = {c.key: getattr(obj, c.key) for c in obj.__table__.columns}
    d["file_size_display"] = _size_display(obj.file_size_bytes)
    return GeneratedReportResponse.model_validate(d)


@router.get(
    "/generated/{report_id}/download",
    summary="Download a generated report — increments download_count (↓ action button)",
)
def download_generated_report(report_id: int, db: Session = Depends(get_db)):
    obj = PayrollGeneratedReportService.increment_download(db, report_id)
    return {
        "report_id": obj.id,
        "report_name": obj.report_name,
        "format": obj.format,
        "file_path": obj.file_path,
        "download_count": obj.download_count,
        "message": "File ready for download",
    }


@router.delete(
    "/generated/{report_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a generated report record",
)
def delete_generated_report(report_id: int, db: Session = Depends(get_db)):
    PayrollGeneratedReportService.delete(db, report_id)


@router.get(
    "/scheduled/",
    response_model=List[ReportScheduleResponse],
    summary="Scheduled tab — Report Name, Schedule, Next Run, Recipients, Format, Status",
)
def list_scheduled_reports(
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    return PayrollReportScheduleService.list_all(db, is_active=is_active)


@router.post(
    "/scheduled/",
    response_model=ReportScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scheduled report",
)
def create_report_schedule(
    payload: ReportScheduleCreate,
    db: Session = Depends(get_db),
):
    return PayrollReportScheduleService.create(db, payload)


@router.put(
    "/scheduled/{schedule_id}",
    response_model=ReportScheduleResponse,
    summary="Update a scheduled report",
)
def update_report_schedule(
    schedule_id: int,
    payload: ReportScheduleUpdate,
    db: Session = Depends(get_db),
):
    return PayrollReportScheduleService.update(db, schedule_id, payload)


@router.patch(
    "/scheduled/{schedule_id}/toggle",
    response_model=ReportScheduleResponse,
    summary="Toggle active/paused — edit (✎) button on Scheduled tab rows",
)
def toggle_schedule_active(schedule_id: int, db: Session = Depends(get_db)):
    return PayrollReportScheduleService.toggle_active(db, schedule_id)


@router.delete(
    "/scheduled/{schedule_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a scheduled report (🗑 button)",
)
def delete_report_schedule(schedule_id: int, db: Session = Depends(get_db)):
    PayrollReportScheduleService.delete(db, schedule_id)


@router.get(
    "/config/",
    response_model=ReportConfigResponse,
    summary="Configuration tab — Default Format, Retention Period, Auto-generate, Email notifications",
)
def get_report_config(db: Session = Depends(get_db)):
    return PayrollReportConfigService.get(db)


@router.put(
    "/config/",
    response_model=ReportConfigResponse,
    summary="Save report configuration (Report Configuration section)",
)
def save_report_config(
    payload: ReportConfigUpsert,
    db: Session = Depends(get_db),
):
    return PayrollReportConfigService.upsert(db, payload)


@router.get(
    "/config/export",
    summary="Export Config — download all configurations as Excel/CSV (Quick Action button)",
)
def export_report_config(db: Session = Depends(get_db)):
    csv_content = PayrollReportConfigService.export_csv(db)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="report_config.csv"'},
    )


@router.post(
    "/config/reset",
    response_model=ReportConfigResponse,
    summary="Reset Settings — restore default configuration values (Quick Action button)",
)
def reset_report_config(
    updated_by: int = Query(0),
    db: Session = Depends(get_db),
):
    return PayrollReportConfigService.reset_defaults(db, updated_by=updated_by)



@router.get(
    "/builder/available-columns",
    summary="Step 2 — Select Data Columns: return available columns (Basic, Salary, Deductions, Attendance)",
)
def get_available_columns():
    return PayrollCustomReportService.get_available_columns()


@router.post(
    "/builder/",
    response_model=CustomReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Report — final step of Report Builder wizard (✓ Create Report button)",
)
def create_custom_report(
    payload: CustomReportCreate,
    db: Session = Depends(get_db),
):
    return PayrollCustomReportService.create(db, payload)


@router.get(
    "/builder/",
    response_model=List[CustomReportResponse],
    summary="Custom Reports table in Configuration tab",
)
def list_custom_reports(
    is_active: Optional[bool] = Query(True),
    category: Optional[ReportCategory] = Query(None),
    db: Session = Depends(get_db),
):
    return PayrollCustomReportService.list_all(db, is_active=is_active, category=category)


@router.get(
    "/builder/{report_id}",
    response_model=CustomReportResponse,
    summary="Get a custom report by ID",
)
def get_custom_report(report_id: int, db: Session = Depends(get_db)):
    return PayrollCustomReportService.get_by_id(db, report_id)


@router.put(
    "/builder/{report_id}",
    response_model=CustomReportResponse,
    summary="Update a custom report definition",
)
def update_custom_report(
    report_id: int,
    payload: CustomReportUpdate,
    db: Session = Depends(get_db),
):
    return PayrollCustomReportService.update(db, report_id, payload)


@router.delete(
    "/builder/{report_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a custom report",
)
def delete_custom_report(report_id: int, db: Session = Depends(get_db)):
    PayrollCustomReportService.delete(db, report_id)


@router.get(
    "/builder/{report_id}/columns",
    response_model=List[CustomReportColumnResponse],
    summary="Get selected columns for a custom report",
)
def get_custom_report_columns(report_id: int, db: Session = Depends(get_db)):
    return PayrollCustomReportService.get_columns(db, report_id)


@router.get(
    "/builder/{report_id}/export/csv",
    summary="Run custom report and export as CSV",
)
def export_custom_report_csv(report_id: int, db: Session = Depends(get_db)):
    report = PayrollCustomReportService.get_by_id(db, report_id)
    csv_content = PayrollCustomReportService.export_csv(db, report_id)
    safe_name = report.report_name.replace(" ", "_")
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.csv"'},
    )



@router.get(
    "/data/monthly-summary",
    response_model=List[MonthlyPayrollSummaryItem],
    summary="Monthly Payroll Register — filter by month / year",
)
def data_monthly_summary(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return PayrollDataReportService.monthly_summary(db, month=month, year=year)


@router.get(
    "/data/department-wise",
    response_model=List[DeptPayrollItem],
    summary="Department-wise Payroll Summary",
)
def data_dept_wise(db: Session = Depends(get_db)):
    return PayrollDataReportService.department_wise(db)


@router.get(
    "/data/location-wise",
    response_model=List[LocationPayrollItem],
    summary="Location-wise Payroll Summary",
)
def data_location_wise(db: Session = Depends(get_db)):
    return PayrollDataReportService.location_wise(db)


@router.get(
    "/data/grade-wise",
    response_model=List[GradeSalaryItem],
    summary="Grade-wise Salary Analysis",
)
def data_grade_wise(db: Session = Depends(get_db)):
    return PayrollDataReportService.grade_wise(db)


@router.get(
    "/data/salary-components",
    response_model=SalaryComponentBreakdown,
    summary="Salary Component Breakdown — earnings vs deductions for a period",
)
def data_salary_components(
    payroll_run_id: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return PayrollDataReportService.salary_components(
        db, payroll_run_id=payroll_run_id, month=month, year=year
    )


@router.get(
    "/data/bank-transfer-summary",
    response_model=List[BankTransferSummaryItem],
    summary="Bank Transfer Summary",
)
def data_bank_transfer_summary(db: Session = Depends(get_db)):
    return PayrollDataReportService.bank_transfer_summary(db)


@router.get(
    "/data/pf-remittance",
    response_model=List[PFRemittanceItem],
    summary="PF Remittance Report",
)
def data_pf_remittance(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return PayrollDataReportService.pf_remittance(db, month=month, year=year)


@router.get(
    "/data/esi-remittance",
    response_model=List[ESIRemittanceItem],
    summary="ESI Remittance Report",
)
def data_esi_remittance(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return PayrollDataReportService.esi_remittance(db, month=month, year=year)


@router.get(
    "/data/tds",
    response_model=List[TDSReportItem],
    summary="TDS Deduction Report",
)
def data_tds(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return PayrollDataReportService.tds_report(db, month=month, year=year)


@router.get(
    "/data/professional-tax",
    response_model=List[PTDeductionItem],
    summary="Professional Tax (PT) Deduction Report",
)
def data_pt(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return PayrollDataReportService.pt_deduction(db, month=month, year=year)


@router.get(
    "/data/variance",
    response_model=List[PayrollVarianceItem],
    summary="Payroll Variance Report (Month-over-Month)",
)
def data_variance(db: Session = Depends(get_db)):
    return PayrollDataReportService.payroll_variance(db)


@router.get(
    "/data/cost-center",
    response_model=List[CostCenterItem],
    summary="Cost Center Wise Payroll",
)
def data_cost_center(db: Session = Depends(get_db)):
    return PayrollDataReportService.cost_center(db)


@router.get(
    "/data/headcount-trends",
    response_model=List[HeadcountTrendItem],
    summary="Headcount and Payroll Cost Trends",
)
def data_headcount_trends(db: Session = Depends(get_db)):
    return PayrollDataReportService.headcount_trends(db)


@router.get("/data/pf-remittance/export/csv", summary="Export PF Remittance as CSV")
def export_pf_csv(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    data = PayrollDataReportService.pf_remittance(db, month=month, year=year)
    headers = ["Emp ID", "Emp Code", "Name", "Dept", "Basic", "PF Employee", "PF Employer", "Total PF"]
    rows = [[d.employee_id, d.employee_code or "", d.employee_name, d.department or "",
             d.basic, d.pf_employee, d.pf_employer, d.total_pf] for d in data]
    csv_content = PayrollDataReportService.export_as_csv(headers, rows)
    return StreamingResponse(
        io.StringIO(csv_content), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="pf_remittance.csv"'},
    )


@router.get("/data/tds/export/csv", summary="Export TDS Report as CSV")
def export_tds_csv(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    data = PayrollDataReportService.tds_report(db, month=month, year=year)
    headers = ["Emp ID", "Emp Code", "Name", "Department", "Designation", "Gross Salary", "TDS Deducted"]
    rows = [[d.employee_id, d.employee_code or "", d.employee_name,
             d.department or "", d.designation or "", d.gross_salary, d.tds_deducted] for d in data]
    csv_content = PayrollDataReportService.export_as_csv(headers, rows)
    return StreamingResponse(
        io.StringIO(csv_content), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tds_report.csv"'},
    )


@router.get("/data/department-wise/export/csv", summary="Export Department-wise Payroll as CSV")
def export_dept_csv(db: Session = Depends(get_db)):
    data = PayrollDataReportService.department_wise(db)
    headers = ["Department", "Headcount", "Total Gross", "Total Deductions", "Total Net Pay", "Avg Net Pay", "% of Total"]
    rows = [[d.department, d.headcount, d.total_gross, d.total_deductions,
             d.total_net_pay, d.avg_net_pay, d.pct_of_total] for d in data]
    csv_content = PayrollDataReportService.export_as_csv(headers, rows)
    return StreamingResponse(
        io.StringIO(csv_content), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="department_wise_payroll.csv"'},
    )



@router.post(
    "/export-data",
    summary="Export Data — top-right button on Payroll Reports page",
)
def export_all_data(
    payload: ExportDataRequest,
    db: Session = Depends(get_db),
):
    record = PayrollGeneratedReportService.create(
        db,
        GeneratedReportCreate(
            report_name="Full Payroll Data Export",
            period_month=payload.period_month,
            period_year=payload.period_year,
            format=payload.format,
            generated_by_label="System",
        ),
    )
    return {
        "message": f"Full payroll export initiated in {payload.format.value} format",
        "generated_report_id": record.id,
    }