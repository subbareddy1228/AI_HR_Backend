from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
#from dependencies import get_db
from core.database import get_db

from schema.Payroll.payroll_reports import (
    SummaryMetricOut, AIInsightOut,
    StandardReportCreate, StandardReportUpdate, StandardReportOut,
    GenerateStandardReportRequest, ScheduleStandardReportRequest,
    ComplianceReportCreate, ComplianceReportOut,
    AnalyticsDashboardOut, AnalyticsDataRequest,
    GeneratedReportOut,
    ScheduledReportCreate, ScheduledReportUpdate, ScheduledReportOut,
    ReportConfigurationOut, ReportConfigurationUpdate,
    ReportColumnDefinitionOut,
    CustomReportCreate, CustomReportUpdate, CustomReportOut,
    ExportConfigOut,
)
#from services.payroll_reports_service import PayrollReportsService

router = APIRouter(
    prefix="/payroll-reports",
    tags=["Payroll Reports"],
)


# ── Dashboard (top summary cards + AI insights, shown on all tabs) ───────────

@router.get("/summary", response_model=List[SummaryMetricOut])
def get_summary_metrics(period: Optional[str] = None, db: Session = Depends(get_db)):
    return PayrollReportsService(db).get_summary_metrics(period)

@router.get("/insights", response_model=List[AIInsightOut])
def get_ai_insights(db: Session = Depends(get_db)):
    return PayrollReportsService(db).get_ai_insights()

@router.post("/insights/{insight_id}/dismiss")
def dismiss_insight(insight_id: int, db: Session = Depends(get_db)):
    return PayrollReportsService(db).dismiss_insight(insight_id)


# ── Tab 1: Standard Reports ───────────────────────────────────────────────────

@router.get("/standard", response_model=List[StandardReportOut])
def list_standard_reports(
    search: Optional[str] = None,
    department: Optional[str] = None,
    frequency: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return PayrollReportsService(db).list_standard_reports(search, department, frequency)

@router.post("/standard", response_model=StandardReportOut, status_code=201)
def create_standard_report(data: StandardReportCreate, db: Session = Depends(get_db)):
    return PayrollReportsService(db).create_standard_report(data)

@router.put("/standard/{report_id}", response_model=StandardReportOut)
def update_standard_report(report_id: int, data: StandardReportUpdate, db: Session = Depends(get_db)):
    return PayrollReportsService(db).update_standard_report(report_id, data)

@router.delete("/standard/{report_id}", status_code=204)
def delete_standard_report(report_id: int, db: Session = Depends(get_db)):
    PayrollReportsService(db).delete_standard_report(report_id)

@router.post("/standard/{report_id}/generate", response_model=GeneratedReportOut, status_code=201)
def generate_standard_report(report_id: int, data: GenerateStandardReportRequest, db: Session = Depends(get_db)):
    return PayrollReportsService(db).generate_standard_report(report_id, data)

@router.post("/standard/{report_id}/schedule", response_model=ScheduledReportOut, status_code=201)
def schedule_standard_report(report_id: int, data: ScheduleStandardReportRequest, db: Session = Depends(get_db)):
    return PayrollReportsService(db).schedule_standard_report(report_id, data)

@router.get("/standard/export")
def export_standard_reports(format: str = "excel", db: Session = Depends(get_db)):
    file_path, filename = PayrollReportsService(db).export_standard_reports(format)
    return FileResponse(file_path, filename=filename)


# ── Tab 2: Compliance ─────────────────────────────────────────────────────────

@router.get("/compliance", response_model=List[ComplianceReportOut])
def list_compliance_reports(type: Optional[str] = None, db: Session = Depends(get_db)):
    return PayrollReportsService(db).list_compliance_reports(type)

@router.get("/compliance/overdue-count")
def get_overdue_count(db: Session = Depends(get_db)):
    return PayrollReportsService(db).get_overdue_compliance_count()

@router.post("/compliance", response_model=ComplianceReportOut, status_code=201)
def create_compliance_report(data: ComplianceReportCreate, db: Session = Depends(get_db)):
    return PayrollReportsService(db).create_compliance_report(data)

@router.get("/compliance/{report_id}/download")
def download_compliance_report(report_id: int, db: Session = Depends(get_db)):
    file_path, filename = PayrollReportsService(db).get_compliance_file(report_id)
    return FileResponse(file_path, filename=filename)

@router.delete("/compliance/{report_id}", status_code=204)
def delete_compliance_report(report_id: int, db: Session = Depends(get_db)):
    PayrollReportsService(db).delete_compliance_report(report_id)


# ── Tab 3: Analytics ──────────────────────────────────────────────────────────

@router.get("/analytics", response_model=List[AnalyticsDashboardOut])
def list_analytics_dashboards(db: Session = Depends(get_db)):
    return PayrollReportsService(db).list_analytics_dashboards()

@router.post("/analytics/{dashboard_id}/data")
def get_analytics_data(dashboard_id: int, data: AnalyticsDataRequest, db: Session = Depends(get_db)):
    """Returns chart-ready data points for a given analytics dashboard."""
    return PayrollReportsService(db).get_analytics_data(dashboard_id, data)


# ── Tab 4: Generated ──────────────────────────────────────────────────────────

@router.get("/generated", response_model=List[GeneratedReportOut])
def list_generated_reports(db: Session = Depends(get_db)):
    return PayrollReportsService(db).list_generated_reports()

@router.get("/generated/{report_id}/download")
def download_generated_report(report_id: int, db: Session = Depends(get_db)):
    file_path, filename = PayrollReportsService(db).get_generated_report_file(report_id)
    return FileResponse(file_path, filename=filename)

@router.delete("/generated/{report_id}", status_code=204)
def delete_generated_report(report_id: int, db: Session = Depends(get_db)):
    PayrollReportsService(db).delete_generated_report(report_id)


# ── Tab 5: Scheduled ──────────────────────────────────────────────────────────

@router.get("/scheduled", response_model=List[ScheduledReportOut])
def list_scheduled_reports(db: Session = Depends(get_db)):
    return PayrollReportsService(db).list_scheduled_reports()

@router.post("/scheduled", response_model=ScheduledReportOut, status_code=201)
def create_scheduled_report(data: ScheduledReportCreate, db: Session = Depends(get_db)):
    return PayrollReportsService(db).create_scheduled_report(data)

@router.put("/scheduled/{schedule_id}", response_model=ScheduledReportOut)
def update_scheduled_report(schedule_id: int, data: ScheduledReportUpdate, db: Session = Depends(get_db)):
    return PayrollReportsService(db).update_scheduled_report(schedule_id, data)

@router.post("/scheduled/{schedule_id}/pause")
def pause_scheduled_report(schedule_id: int, db: Session = Depends(get_db)):
    return PayrollReportsService(db).pause_scheduled_report(schedule_id)

@router.post("/scheduled/{schedule_id}/resume")
def resume_scheduled_report(schedule_id: int, db: Session = Depends(get_db)):
    return PayrollReportsService(db).resume_scheduled_report(schedule_id)

@router.delete("/scheduled/{schedule_id}", status_code=204)
def delete_scheduled_report(schedule_id: int, db: Session = Depends(get_db)):
    PayrollReportsService(db).delete_scheduled_report(schedule_id)


# ── Tab 6: Configuration ──────────────────────────────────────────────────────

@router.get("/configuration", response_model=ReportConfigurationOut)
def get_configuration(db: Session = Depends(get_db)):
    return PayrollReportsService(db).get_configuration()

@router.put("/configuration", response_model=ReportConfigurationOut)
def update_configuration(data: ReportConfigurationUpdate, db: Session = Depends(get_db)):
    return PayrollReportsService(db).update_configuration(data)

@router.post("/configuration/reset", response_model=ReportConfigurationOut)
def reset_configuration(db: Session = Depends(get_db)):
    return PayrollReportsService(db).reset_configuration()

@router.get("/configuration/export", response_model=ExportConfigOut)
def export_configuration(db: Session = Depends(get_db)):
    return PayrollReportsService(db).export_configuration()

@router.get("/configuration/export/download")
def download_configuration_export(db: Session = Depends(get_db)):
    file_path, filename = PayrollReportsService(db).get_configuration_export_file()
    return FileResponse(file_path, filename=filename)

# Custom Reports listed under Configuration tab
@router.get("/custom", response_model=List[CustomReportOut])
def list_custom_reports(db: Session = Depends(get_db)):
    return PayrollReportsService(db).list_custom_reports()

@router.delete("/custom/{report_id}", status_code=204)
def delete_custom_report(report_id: int, db: Session = Depends(get_db)):
    PayrollReportsService(db).delete_custom_report(report_id)


# ── Tab 7: Report Builder ─────────────────────────────────────────────────────

@router.get("/builder/columns", response_model=List[ReportColumnDefinitionOut])
def list_column_definitions(group: Optional[str] = None, db: Session = Depends(get_db)):
    return PayrollReportsService(db).list_column_definitions(group)

@router.post("/builder", response_model=CustomReportOut, status_code=201)
def create_custom_report(data: CustomReportCreate, db: Session = Depends(get_db)):
    """Final 'Create Report' submission from the 4-step Report Builder wizard."""
    return PayrollReportsService(db).create_custom_report(data)

@router.get("/builder/{report_id}", response_model=CustomReportOut)
def get_custom_report(report_id: int, db: Session = Depends(get_db)):
    return PayrollReportsService(db).get_custom_report(report_id)

@router.put("/builder/{report_id}", response_model=CustomReportOut)
def update_custom_report(report_id: int, data: CustomReportUpdate, db: Session = Depends(get_db)):
    return PayrollReportsService(db).update_custom_report(report_id, data)

@router.post("/builder/{report_id}/run", response_model=GeneratedReportOut, status_code=201)
def run_custom_report(report_id: int, db: Session = Depends(get_db)):
    """Generates output for a saved custom report on demand."""
    return PayrollReportsService(db).run_custom_report(report_id)
