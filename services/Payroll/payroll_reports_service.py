from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException
from datetime import datetime, timezone
import csv, io, json

from model.Payroll.payroll_reports import (
    PayrollSummaryMetric, AIInsight, StandardReport, ComplianceReport,
    AnalyticsDashboard, PayrollGeneratedReport, ScheduledReport,
    ReportConfiguration, ReportColumnDefinition, CustomReport,
)
from schema.Payroll.payroll_reports import (
    StandardReportCreate, StandardReportUpdate,
    ComplianceReportCreate, AnalyticsDataRequest,
    ScheduleStandardReportRequest, GenerateStandardReportRequest,
    CustomReportCreate, CustomReportUpdate,
    ReportConfigurationUpdate, ScheduledReportCreate, ScheduledReportUpdate,
)


class PayrollReportsService:
    def __init__(self, db: Session):
        self.db = db

    def _get_or_404(self, model, pk: int):
        obj = self.db.get(model, pk)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{model.__name__} {pk} not found")
        return obj

    def _get_config(self) -> ReportConfiguration:
        row = self.db.execute(select(ReportConfiguration)).scalar_one_or_none()
        if not row:
            row = ReportConfiguration()
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
        return row

    # ── Dashboard Summary ──────────────────────────────────────────────────
    def get_summary_metrics(self, period=None):
        q = select(PayrollSummaryMetric)
        if period:
            q = q.where(PayrollSummaryMetric.period == period)
        return self.db.execute(q).scalars().all()

    def get_ai_insights(self):
        return self.db.execute(
            select(AIInsight)
            .where(AIInsight.is_dismissed == False)
            .order_by(AIInsight.id.desc())
        ).scalars().all()

    def dismiss_insight(self, insight_id: int):
        row = self._get_or_404(AIInsight, insight_id)
        row.is_dismissed = True
        self.db.commit()

    # ── Standard Reports ─────────────────────────────────────────────────
    def list_standard_reports(self, search=None, department=None, frequency=None):
        q = select(StandardReport).where(StandardReport.is_active == True)
        if search:
            q = q.where(StandardReport.name.ilike(f"%{search}%"))
        if department:
            q = q.where(StandardReport.department == department)
        if frequency:
            q = q.where(StandardReport.frequency == frequency)
        return self.db.execute(q.order_by(StandardReport.display_order)).scalars().all()

    def create_standard_report(self, data: StandardReportCreate):
        row = StandardReport(**data.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_standard_report(self, report_id: int, data: StandardReportUpdate):
        row = self._get_or_404(StandardReport, report_id)
        for k, v in data.model_dump().items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_standard_report(self, report_id: int):
        row = self._get_or_404(StandardReport, report_id)
        row.is_active = False
        self.db.commit()

    def generate_standard_report(self, report_id: int, data: GenerateStandardReportRequest):
        row = self._get_or_404(StandardReport, report_id)
        file_path = f"/tmp/report_{report_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{data.format}"
        with open(file_path, "w") as f:
            f.write(f"Report: {row.name}\nPeriod: {data.period}\nDepartment: {data.department}")
        generated = PayrollGeneratedReport(
            source_type="standard",
            source_id=report_id,
            report_name=row.name,
            period=data.period,
            department=data.department,
            format=data.format,
            file_path=file_path,
            status="completed",
        )
        row.last_generated = datetime.now(timezone.utc).date()
        row.status = "generated"
        self.db.add(generated)
        self.db.commit()
        self.db.refresh(generated)
        return generated

    def schedule_standard_report(self, report_id: int, data: ScheduleStandardReportRequest):
        row = self._get_or_404(StandardReport, report_id)
        scheduled = ScheduledReport(
            source_type="standard",
            source_id=report_id,
            report_name=row.name,
            schedule_text=data.schedule_text,
            recipients=data.recipients,
            formats=data.formats,
            status="active",
        )
        self.db.add(scheduled)
        self.db.commit()
        self.db.refresh(scheduled)
        return scheduled

    def export_standard_reports(self, format: str):
        rows = self.db.execute(select(StandardReport).where(StandardReport.is_active == True)).scalars().all()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ID", "Name", "Department", "Frequency", "Status", "Last Generated"])
        for r in rows:
            writer.writerow([r.id, r.name, r.department, r.frequency, r.status, r.last_generated])
        file_path = "/tmp/standard_reports_export.csv"
        with open(file_path, "w") as f:
            f.write(buf.getvalue())
        return file_path, "standard_reports.csv"

    # ── Compliance ───────────────────────────────────────────────────────
    def list_compliance_reports(self, type=None):
        q = select(ComplianceReport)
        if type:
            q = q.where(ComplianceReport.type == type)
        return self.db.execute(q).scalars().all()

    def get_overdue_compliance_count(self):
        count = self.db.execute(
            select(func.count(ComplianceReport.id)).where(ComplianceReport.is_overdue == True)
        ).scalar() or 0
        return {"overdue_count": count}

    def create_compliance_report(self, data: ComplianceReportCreate):
        row = ComplianceReport(**data.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_compliance_file(self, report_id: int):
        row = self._get_or_404(ComplianceReport, report_id)
        file_path = row.file_path or f"/tmp/compliance_{report_id}.pdf"
        if not row.file_path:
            with open(file_path, "w") as f:
                f.write(f"Compliance Report: {row.name}")
        return file_path, f"{row.name}.pdf"

    def delete_compliance_report(self, report_id: int):
        row = self._get_or_404(ComplianceReport, report_id)
        self.db.delete(row)
        self.db.commit()

    # ── Analytics ─────────────────────────────────────────────────────────
    def list_analytics_dashboards(self):
        return self.db.execute(
            select(AnalyticsDashboard)
            .where(AnalyticsDashboard.is_active == True)
            .order_by(AnalyticsDashboard.display_order)
        ).scalars().all()

    def get_analytics_data(self, dashboard_id: int, data: AnalyticsDataRequest):
        row = self._get_or_404(AnalyticsDashboard, dashboard_id)
        # Return placeholder data — real implementation would query payroll tables
        return {
            "dashboard_id": dashboard_id,
            "name": row.name,
            "period": data.period,
            "department": data.department,
            "data": [],
        }

    # ── Generated Reports ─────────────────────────────────────────────────
    def list_generated_reports(self):
        return self.db.execute(
            select(PayrollGeneratedReport).order_by(PayrollGeneratedReport.created_at.desc())
        ).scalars().all()

    def get_generated_report_file(self, report_id: int):
        row = self._get_or_404(PayrollGeneratedReport, report_id)
        file_path = row.file_path or f"/tmp/generated_{report_id}.pdf"
        return file_path, f"{row.report_name}.{row.format}"

    def delete_generated_report(self, report_id: int):
        row = self._get_or_404(PayrollGeneratedReport, report_id)
        self.db.delete(row)
        self.db.commit()

    # ── Scheduled Reports ─────────────────────────────────────────────────
    def list_scheduled_reports(self):
        return self.db.execute(
            select(ScheduledReport).where(ScheduledReport.is_active == True)
        ).scalars().all()

    def create_scheduled_report(self, data: ScheduledReportCreate):
        row = ScheduledReport(**data.model_dump(), status="active")
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_scheduled_report(self, schedule_id: int, data: ScheduledReportUpdate):
        row = self._get_or_404(ScheduledReport, schedule_id)
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def pause_scheduled_report(self, schedule_id: int):
        row = self._get_or_404(ScheduledReport, schedule_id)
        row.status = "paused"
        self.db.commit()
        self.db.refresh(row)
        return row

    def resume_scheduled_report(self, schedule_id: int):
        row = self._get_or_404(ScheduledReport, schedule_id)
        row.status = "active"
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_scheduled_report(self, schedule_id: int):
        row = self._get_or_404(ScheduledReport, schedule_id)
        row.is_active = False
        self.db.commit()

    # ── Configuration ─────────────────────────────────────────────────────
    def get_configuration(self):
        return self._get_config()

    def update_configuration(self, data: ReportConfigurationUpdate):
        row = self._get_config()
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def reset_configuration(self):
        row = self._get_config()
        row.default_format = "pdf"
        row.retention_period_months = 12
        row.auto_generate_scheduled_reports = True
        row.email_notifications = True
        self.db.commit()
        self.db.refresh(row)
        return row

    def export_configuration(self):
        row = self._get_config()
        file_path = "/tmp/report_config.json"
        with open(file_path, "w") as f:
            json.dump({
                "default_format": row.default_format,
                "retention_period_months": row.retention_period_months,
                "auto_generate_scheduled_reports": row.auto_generate_scheduled_reports,
                "email_notifications": row.email_notifications,
            }, f, indent=2)
        return file_path, "report_configuration.json"

    def get_configuration_export_file(self):
        return self.export_configuration()

    # ── Custom Reports / Report Builder ──────────────────────────────────
    def list_custom_reports(self):
        return self.db.execute(select(CustomReport)).scalars().all()

    def delete_custom_report(self, report_id: int):
        row = self._get_or_404(CustomReport, report_id)
        self.db.delete(row)
        self.db.commit()

    def list_column_definitions(self, group=None):
        q = select(ReportColumnDefinition)
        if group:
            q = q.where(ReportColumnDefinition.group == group)
        return self.db.execute(q.order_by(ReportColumnDefinition.display_order)).scalars().all()

    def create_custom_report(self, data: CustomReportCreate):
        row = CustomReport(**data.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_custom_report(self, report_id: int):
        return self._get_or_404(CustomReport, report_id)

    def update_custom_report(self, report_id: int, data: CustomReportUpdate):
        row = self._get_or_404(CustomReport, report_id)
        for k, v in data.model_dump().items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def run_custom_report(self, report_id: int):
        row = self._get_or_404(CustomReport, report_id)
        generated = PayrollGeneratedReport(
            source_type="custom",
            source_id=report_id,
            report_name=row.name,
            format="pdf",
            status="completed",
        )
        self.db.add(generated)
        self.db.commit()
        self.db.refresh(generated)
        return generated