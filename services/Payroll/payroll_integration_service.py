import io
import csv
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from fastapi import HTTPException
from passlib.hash import bcrypt

from model.Payroll.payroll_integration import (
    AttendanceFreeze, IntegrationSyncLog, SystemHealthIssue,
    PayrollCalculationRule, AttendanceCorrection,
    IntegrationActionItem, IntegrationSettings,
    PayrollIntegrationReport,
)
from model.onboarding.employee import Employee
from schema.Payroll.payroll_integration import (
    IntegrationFilter,
    DashboardSummary,
    PipelineStep, PayrollProcessingStatus,
    PayrollImpactAnalysis, ImpactAnalysisPoint,
    TopDeductionsAdditions, DeductionAdditionItem,
    IntegrationStatusOut, SyncStatusCard, DataFreshnessCard, SystemHealthCard,
    ActionItemOut, ActionResolve,
    RealtimeDataFlowOut, SyncNowRequest,
    CalculationRuleUpdate,
    PayrollCalculationRow, PayrollCalculationOut, RunPayrollRequest,
    CorrectionCreate, CorrectionUpdate,
    IntegrationSettingsUpdate,
)




def _get_or_create_settings(db: Session) -> IntegrationSettings:
    settings = db.query(IntegrationSettings).first()
    if not settings:
        settings = IntegrationSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def _get_or_create_freeze(db: Session, month: int, year: int) -> AttendanceFreeze:
    freeze = db.query(AttendanceFreeze).filter(
        AttendanceFreeze.run_month == month,
        AttendanceFreeze.run_year == year,
    ).first()
    if not freeze:
        freeze = AttendanceFreeze(run_month=month, run_year=year, status="UNFROZEN")
        db.add(freeze)
        db.commit()
        db.refresh(freeze)
    return freeze


def _current_month_year() -> tuple[int, int]:
    today = date.today()
    return today.month, today.year




class PayrollIntegrationService:

    

    def get_dashboard_summary(self, db: Session, filters: IntegrationFilter) -> DashboardSummary:
        month, year = filters.month, filters.year
        if not month or not year:
            month, year = _current_month_year()

        
        last_sync = db.query(IntegrationSyncLog).order_by(
            IntegrationSyncLog.synced_at.desc()
        ).first()
        sync_hours = 0.5
        sync_label = "Last sync: Just now"
        if last_sync:
            delta = datetime.utcnow() - last_sync.synced_at
            sync_hours = round(delta.total_seconds() / 3600, 1)
            sync_label = "Last sync: Just now" if sync_hours < 0.1 else f"Last sync: {sync_hours}h ago"

    
        q = db.query(AttendanceCorrection).filter(
            extract("month", AttendanceCorrection.original_date) == month,
            extract("year",  AttendanceCorrection.original_date) == year,
        )

        loss_of_pay = db.query(func.sum(AttendanceCorrection.payroll_impact)).filter(
            AttendanceCorrection.correction_type.in_(["Post-Payroll Adjustment"]),
            AttendanceCorrection.payroll_impact < 0,
            extract("month", AttendanceCorrection.original_date) == month,
            extract("year",  AttendanceCorrection.original_date) == year,
        ).scalar() or Decimal("0.00")

        overtime_pay = db.query(func.sum(AttendanceCorrection.payroll_impact)).filter(
            AttendanceCorrection.correction_type == "Overtime Update",
            extract("month", AttendanceCorrection.original_date) == month,
            extract("year",  AttendanceCorrection.original_date) == year,
        ).scalar() or Decimal("0.00")

        affected_count = q.filter(AttendanceCorrection.payroll_impact != 0).count()

        pending_corrections = db.query(func.count(AttendanceCorrection.id)).filter(
            AttendanceCorrection.status == "PENDING"
        ).scalar() or 0

        return DashboardSummary(
            real_time_sync_hours=sync_hours,
            last_sync_label=sync_label,
            data_status="Live",
            total_loss_of_pay=abs(loss_of_pay),
            loss_of_pay_employee_count=affected_count,
            overtime_pay=overtime_pay,
            overtime_avg_per_employee=0.0,
            holiday_pay=Decimal("0.00"),
            leave_without_pay_days=0,
            leave_without_pay_deduction=Decimal("0.00"),
            pending_corrections=pending_corrections,
            processed_payroll=Decimal("0.00"),
            processed_employee_count=0,
        )

    def get_processing_status(self, db: Session, month: int, year: int) -> PayrollProcessingStatus:
        
        freeze = _get_or_create_freeze(db, month, year)
        period_start = date(year, month, 1)
        next_month = month + 1 if month < 12 else 1
        next_year  = year if month < 12 else year + 1
        period_end = date(next_year, next_month, 1) - timedelta(days=1)

        steps = [
            PipelineStep(step_number=1, title="Data Collection",
                         subtitle="Gather attendance data",
                         status="completed"),
            PipelineStep(step_number=2, title="Attendance Freeze",
                         subtitle="Lock data for processing",
                         status="completed" if freeze.status == "FROZEN" else "in_progress"),
            PipelineStep(step_number=3, title="Calculations",
                         subtitle="Run payroll calculations",
                         status="pending" if freeze.status != "FROZEN" else "in_progress"),
            PipelineStep(step_number=4, title="Approval",
                         subtitle="Manager approval",
                         status="pending"),
            PipelineStep(step_number=5, title="Processing",
                         subtitle="Disburse salaries",
                         status="pending"),
        ]

        next_run = period_end + timedelta(days=5)

        return PayrollProcessingStatus(
            current_period_start=period_start,
            current_period_end=period_end,
            next_run_date=next_run,
            steps=steps,
        )

    def get_impact_analysis(self, db: Session, filters: IntegrationFilter) -> PayrollImpactAnalysis:
        
        depts = db.query(Employee.department).filter(
            Employee.is_active == True, Employee.department != None
        ).distinct().all()

        points = [
            ImpactAnalysisPoint(
                label=d[0],
                basic_salary=Decimal("0.00"),
                net_pay=Decimal("0.00"),
                loss_of_pay=Decimal("0.00"),
            )
            for d in depts
        ]
        return PayrollImpactAnalysis(period="Current Month", points=points)

    def get_top_deductions_additions(self, db: Session, filters: IntegrationFilter) -> TopDeductionsAdditions:
        month, year = filters.month, filters.year
        if not month or not year:
            month, year = _current_month_year()

        lop = db.query(func.sum(AttendanceCorrection.payroll_impact)).filter(
            AttendanceCorrection.correction_type == "Post-Payroll Adjustment",
            AttendanceCorrection.payroll_impact < 0,
        ).scalar() or Decimal("0.00")

        lwop = Decimal("0.00")  # populate once LWOP tracking is wired to attendance

        overtime = db.query(func.sum(AttendanceCorrection.payroll_impact)).filter(
            AttendanceCorrection.correction_type == "Overtime Update",
            AttendanceCorrection.payroll_impact > 0,
        ).scalar() or Decimal("0.00")

        holiday = Decimal("0.00")

        return TopDeductionsAdditions(
            deductions=[
                DeductionAdditionItem(label="Loss of Pay", amount=abs(lop), pct_change=None),
                DeductionAdditionItem(label="Leave Without Pay", amount=lwop, pct_change=None),
            ],
            additions=[
                DeductionAdditionItem(label="Overtime Pay", amount=overtime, pct_change=None),
                DeductionAdditionItem(label="Holiday Pay", amount=holiday, pct_change=None),
            ],
        )

    

    def get_freeze_status(self, db: Session, month: int, year: int) -> AttendanceFreeze:
        return _get_or_create_freeze(db, month, year)

    def freeze_for_payroll(self, db: Session, month: int, year: int, requested_by: str) -> AttendanceFreeze:
        
        freeze = _get_or_create_freeze(db, month, year)
        if freeze.status == "FROZEN":
            raise HTTPException(400, "Attendance data is already frozen for this period.")

        freeze.status      = "FROZEN"
        freeze.frozen_at   = datetime.utcnow()
        freeze.frozen_by   = requested_by
        freeze.unfrozen_at = None

        next_month = month + 1 if month < 12 else 1
        next_year  = year if month < 12 else year + 1
        freeze.next_freeze_start = date(next_year, next_month, 1)
        freeze.next_freeze_end   = freeze.next_freeze_start + timedelta(days=freeze.freeze_window_days - 1)

        freeze.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(freeze)
        return freeze

    def unfreeze(self, db: Session, month: int, year: int) -> AttendanceFreeze:
        freeze = _get_or_create_freeze(db, month, year)
        if freeze.status != "FROZEN":
            raise HTTPException(400, "Attendance data is not currently frozen.")
        freeze.status      = "UNFROZEN"
        freeze.unfrozen_at = datetime.utcnow()
        freeze.updated_at  = datetime.utcnow()
        db.commit()
        db.refresh(freeze)
        return freeze

   

    def get_integration_status(self, db: Session) -> IntegrationStatusOut:
        att_sync = db.query(IntegrationSyncLog).filter(
            IntegrationSyncLog.sync_type == "attendance"
        ).order_by(IntegrationSyncLog.synced_at.desc()).first()

        pay_sync = db.query(IntegrationSyncLog).filter(
            IntegrationSyncLog.sync_type == "payroll"
        ).order_by(IntegrationSyncLog.synced_at.desc()).first()

        settings = _get_or_create_settings(db)

        last_att = att_sync.synced_at if att_sync else datetime.utcnow()
        last_pay = pay_sync.synced_at if pay_sync else datetime.utcnow()

        freshness_hours = round((datetime.utcnow() - last_att).total_seconds() / 3600, 1)

        open_issues = db.query(func.count(SystemHealthIssue.id)).filter(
            SystemHealthIssue.is_resolved == False
        ).scalar() or 0
        warnings = db.query(func.count(SystemHealthIssue.id)).filter(
            SystemHealthIssue.is_resolved == False,
            SystemHealthIssue.severity == "warning",
        ).scalar() or 0

        return IntegrationStatusOut(
            attendance_sync=SyncStatusCard(
                label="Attendance Sync",
                last_sync_at=last_att,
                sync_frequency_minutes=settings.attendance_sync_frequency_minutes,
                is_healthy=(att_sync.status == "success") if att_sync else True,
            ),
            payroll_sync=SyncStatusCard(
                label="Payroll Sync",
                last_sync_at=last_pay,
                sync_frequency_minutes=settings.payroll_sync_frequency_minutes,
                is_healthy=(pay_sync.status == "success") if pay_sync else True,
            ),
            data_freshness=DataFreshnessCard(
                hours_ago=freshness_hours,
                latency_minutes=5,
            ),
            system_health=SystemHealthCard(
                issues_found=open_issues,
                warnings=warnings,
            ),
        )

    def get_realtime_data_flow(self, db: Session) -> RealtimeDataFlowOut:
        settings = _get_or_create_settings(db)
        last_sync = db.query(IntegrationSyncLog).order_by(
            IntegrationSyncLog.synced_at.desc()
        ).first()

        total = db.query(func.count(IntegrationSyncLog.id)).scalar() or 0
        success = db.query(func.count(IntegrationSyncLog.id)).filter(
            IntegrationSyncLog.status == "success"
        ).scalar() or 0
        rate = round(success / total * 100, 1) if total > 0 else 99.8

        return RealtimeDataFlowOut(
            sync_frequency_minutes=settings.attendance_sync_frequency_minutes,
            success_rate_pct=rate,
            last_sync_at=last_sync.synced_at if last_sync else datetime.utcnow(),
        )

    def sync_now(self, db: Session, payload: SyncNowRequest) -> IntegrationSyncLog:
        
        log = IntegrationSyncLog(
            sync_type="attendance",
            status="success",
            duration_minutes=0,
            records_synced=db.query(func.count(Employee.id)).scalar() or 0,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def refresh_status(self, db: Session) -> IntegrationStatusOut:
        
        return self.get_integration_status(db)

    

    def list_calculation_rules(self, db: Session) -> List[PayrollCalculationRule]:
        rules = db.query(PayrollCalculationRule).all()
        if not rules:
            rules = self._seed_default_rules(db)
        return rules

    def _seed_default_rules(self, db: Session) -> List[PayrollCalculationRule]:
        defaults = [
            dict(rule_key="loss_of_pay", title="Loss of Pay Calculation",
                 description="Automatic deduction based on absence days",
                 formula="Daily Rate × Absent Days", multiplier=1.0, icon_color="red"),
            dict(rule_key="overtime", title="Overtime Hours Feed",
                 description="Overtime hours automatically added to payroll",
                 formula="Hourly Rate × 1.5 × Overtime Hours", multiplier=1.5, icon_color="yellow"),
            dict(rule_key="holiday_pay", title="Holiday Working Pay",
                 description="Double pay for holiday work days",
                 formula="Daily Rate × 2 × Holiday Work Days", multiplier=2.0, icon_color="green"),
            dict(rule_key="lwop", title="Leave Without Pay Tracking",
                 description="Track and deduct for unauthorized leave",
                 formula="Daily Rate × LWOP Days", multiplier=1.0, icon_color="blue"),
        ]
        rules = [PayrollCalculationRule(**d) for d in defaults]
        db.add_all(rules)
        db.commit()
        for r in rules:
            db.refresh(r)
        return rules

    def update_calculation_rule(self, db: Session, rule_id: int, payload: CalculationRuleUpdate) -> PayrollCalculationRule:
        rule = db.query(PayrollCalculationRule).filter(PayrollCalculationRule.id == rule_id).first()
        if not rule:
            raise HTTPException(404, "Calculation rule not found.")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(rule, k, v)
        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
        return rule

    def toggle_rule_active(self, db: Session, rule_id: int) -> PayrollCalculationRule:
        rule = db.query(PayrollCalculationRule).filter(PayrollCalculationRule.id == rule_id).first()
        if not rule:
            raise HTTPException(404, "Calculation rule not found.")
        rule.is_active = not rule.is_active
        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
        return rule

    
    

    def list_action_items(self, db: Session, active_only: bool = True) -> List[IntegrationActionItem]:
        q = db.query(IntegrationActionItem)
        if active_only:
            q = q.filter(IntegrationActionItem.is_resolved == False)
        return q.order_by(IntegrationActionItem.created_at.desc()).all()

    def resolve_action_item(self, db: Session, item_id: int, payload: ActionResolve) -> IntegrationActionItem:
        item = db.query(IntegrationActionItem).filter(IntegrationActionItem.id == item_id).first()
        if not item:
            raise HTTPException(404, "Action item not found.")
        item.is_resolved = True
        item.resolved_at = datetime.utcnow()
        db.commit()
        db.refresh(item)
        return item

    def resolve_all_action_items(self, db: Session) -> dict:
        items = db.query(IntegrationActionItem).filter(
            IntegrationActionItem.is_resolved == False
        ).all()
        for item in items:
            item.is_resolved = True
            item.resolved_at = datetime.utcnow()
        db.commit()
        return {"resolved_count": len(items)}

   

    def get_payroll_calculation(self, db: Session, filters: IntegrationFilter) -> PayrollCalculationOut:
        
        q = db.query(Employee).filter(Employee.is_active == True)
        if filters.department and filters.department not in ("All Departments", "All"):
            q = q.filter(Employee.department == filters.department)
        if filters.location and filters.location not in ("All Locations", "All"):
            q = q.filter(Employee.location == filters.location)

        employees = q.all()
        rows: List[PayrollCalculationRow] = []
        total_net = Decimal("0.00")

        for emp in employees:
            
            row = PayrollCalculationRow(
                employee_id=emp.id,
                employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
                department=emp.department,
                present_days=0,
                absent_days=0,
                overtime_hours=0.0,
                holiday_work_days=0,
                basic_salary=Decimal("0.00"),
                loss_of_pay=Decimal("0.00"),
                overtime_pay=Decimal("0.00"),
                net_pay=Decimal("0.00"),
                status="Pending",
            )
            rows.append(row)
            total_net += row.net_pay

        return PayrollCalculationOut(
            rows=rows,
            total_employees=len(rows),
            total_net_pay=total_net,
        )

    def run_payroll(self, db: Session, payload: RunPayrollRequest) -> dict:
       
        freeze = _get_or_create_freeze(db, payload.month, payload.year)
        if freeze.status != "FROZEN":
            raise HTTPException(
                400,
                "Attendance must be frozen before running payroll. Use 'Freeze for Payroll' first.",
            )
        
        return {
            "message": f"Payroll run triggered for {payload.month}/{payload.year}.",
            "status": "Processing",
        }

    def export_calculation_csv(self, db: Session, filters: IntegrationFilter) -> str:
        data = self.get_payroll_calculation(db, filters)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Employee", "Department", "Present Days", "Absent Days",
            "Overtime (Hrs)", "Holiday Work", "Basic Salary",
            "Loss of Pay", "Overtime Pay", "Net Pay", "Status",
        ])
        for r in data.rows:
            writer.writerow([
                r.employee_name, r.department or "", r.present_days, r.absent_days,
                r.overtime_hours, r.holiday_work_days, r.basic_salary,
                r.loss_of_pay, r.overtime_pay, r.net_pay, r.status,
            ])
        return output.getvalue()

  

    def list_corrections(self, db: Session, status_filter: Optional[str] = None) -> List[dict]:
        q = (
            db.query(AttendanceCorrection, Employee)
            .join(Employee, Employee.id == AttendanceCorrection.employee_id)
        )
        if status_filter and status_filter not in ("All Status", "All"):
            q = q.filter(AttendanceCorrection.status == status_filter.upper())

        rows = q.order_by(AttendanceCorrection.created_at.desc()).all()
        result = []
        for corr, emp in rows:
            result.append({
                "id": corr.id,
                "employee_id": corr.employee_id,
                "employee_name": f"{emp.first_name} {emp.last_name or ''}".strip(),
                "employee_code": emp.employee_code,
                "original_date": str(corr.original_date),
                "correction_type": corr.correction_type,
                "original_value": corr.original_value,
                "corrected_value": corr.corrected_value,
                "payroll_impact": corr.payroll_impact,
                "status": corr.status,
                "requested_by": corr.requested_by,
                "requested_at": str(corr.requested_at) if corr.requested_at else None,
            })
        return result

    def add_correction(self, db: Session, payload: CorrectionCreate) -> AttendanceCorrection:
        emp = db.query(Employee).filter(Employee.id == payload.employee_id).first()
        if not emp:
            raise HTTPException(404, "Employee not found.")

        corr = AttendanceCorrection(
            employee_id=payload.employee_id,
            original_date=payload.original_date,
            correction_type=payload.correction_type,
            original_value=payload.original_value,
            corrected_value=payload.corrected_value,
            payroll_impact=payload.payroll_impact,
            requested_by=payload.requested_by,
            requested_at=date.today(),
            status="PENDING",
        )
        db.add(corr)
        db.commit()
        db.refresh(corr)
        return corr

    def update_correction(self, db: Session, correction_id: int, payload: CorrectionUpdate) -> AttendanceCorrection:
        corr = db.query(AttendanceCorrection).filter(AttendanceCorrection.id == correction_id).first()
        if not corr:
            raise HTTPException(404, "Correction not found.")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(corr, k, v)
        if payload.status in ("APPROVED", "REJECTED"):
            corr.reviewed_at = datetime.utcnow()
        corr.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(corr)
        return corr

    def approve_correction(self, db: Session, correction_id: int, reviewed_by: str) -> AttendanceCorrection:
        return self.update_correction(
            db, correction_id,
            CorrectionUpdate(status="APPROVED", reviewed_by=reviewed_by),
        )

    def reject_correction(self, db: Session, correction_id: int, reviewed_by: str) -> AttendanceCorrection:
        return self.update_correction(
            db, correction_id,
            CorrectionUpdate(status="REJECTED", reviewed_by=reviewed_by),
        )

    def export_corrections_csv(self, db: Session) -> str:
        rows = self.list_corrections(db)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Employee", "Code", "Original Date", "Correction Type",
            "Original Value", "Corrected Value", "Payroll Impact",
            "Status", "Requested By", "Requested At",
        ])
        for r in rows:
            writer.writerow([
                r["employee_name"], r["employee_code"], r["original_date"],
                r["correction_type"], r["original_value"], r["corrected_value"],
                r["payroll_impact"], r["status"], r["requested_by"], r["requested_at"],
            ])
        return output.getvalue()

    

    def list_reports(self, db: Session) -> List[PayrollIntegrationReport]:
        reports = db.query(PayrollIntegrationReport).all()
        if not reports:
            reports = self._seed_default_reports(db)
        return reports

    def _seed_default_reports(self, db: Session) -> List[PayrollIntegrationReport]:
        defaults = [
            dict(report_key="payroll_attendance_reconciliation", title="Payroll-Attendance Reconciliation",
                 category="RECONCILIATION",
                 description="Monthly reconciliation report showing attendance vs payroll data",
                 frequency="monthly", formats="PDF, Excel", column_count=5),
            dict(report_key="loss_of_pay_report", title="Loss of Pay Report",
                 category="DEDUCTION",
                 description="Detailed report of all loss of pay calculations and deductions",
                 frequency="monthly", formats="Excel, CSV", column_count=5),
            dict(report_key="overtime_payment_summary", title="Overtime Payment Summary",
                 category="ADDITION",
                 description="Overtime hours and corresponding payments summary",
                 frequency="monthly", formats="PDF, Excel", column_count=5),
            dict(report_key="holiday_working_compensation", title="Holiday Working Compensation",
                 category="ADDITION",
                 description="Report of holiday work days and double pay compensation",
                 frequency="monthly", formats="PDF, Excel", column_count=5),
            dict(report_key="leave_without_pay_report", title="Leave Without Pay Report",
                 category="DEDUCTION",
                 description="Unauthorized leave days and corresponding salary deductions",
                 frequency="monthly", formats="Excel, CSV", column_count=5),
            dict(report_key="post_payroll_correction_log", title="Post-Payroll Correction Log",
                 category="AUDIT",
                 description="Audit trail of all post-payroll attendance corrections",
                 frequency="monthly", formats="PDF, Excel", column_count=5),
            dict(report_key="attendance_freeze_log", title="Attendance Freeze Log",
                 category="AUDIT",
                 description="Complete history of attendance freeze periods for payroll",
                 frequency="quarterly", formats="PDF", column_count=5),
            dict(report_key="integration_health_report", title="Integration Health Report",
                 category="SYSTEM",
                 description="System health and data sync status between attendance and payroll",
                 frequency="weekly", formats="PDF, Excel", column_count=5),
        ]
        reports = [PayrollIntegrationReport(**d) for d in defaults]
        db.add_all(reports)
        db.commit()
        for r in reports:
            db.refresh(r)
        return reports

    def generate_report(self, db: Session, report_key: str) -> dict:
        report = db.query(PayrollIntegrationReport).filter(
            PayrollIntegrationReport.report_key == report_key
        ).first()
        if not report:
            raise HTTPException(404, "Report not found.")
        report.last_generated = date.today()
        db.commit()
        db.refresh(report)
        return {"message": f"'{report.title}' generated successfully.", "generated_at": str(report.last_generated)}

    def export_all_reports(self, db: Session) -> str:
        reports = self.list_reports(db)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Title", "Category", "Frequency", "Formats", "Last Generated"])
        for r in reports:
            writer.writerow([r.title, r.category, r.frequency, r.formats, r.last_generated or ""])
        return output.getvalue()

   

    def get_settings(self, db: Session) -> IntegrationSettings:
        return _get_or_create_settings(db)

    def update_settings(self, db: Session, payload: IntegrationSettingsUpdate) -> IntegrationSettings:
        settings = _get_or_create_settings(db)
        data = payload.model_dump(exclude_unset=True)

        if "payroll_processing_password" in data and data["payroll_processing_password"]:
            data["payroll_processing_password"] = bcrypt.hash(data["payroll_processing_password"])

        for k, v in data.items():
            setattr(settings, k, v)
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
        return settings

    def reset_settings_to_defaults(self, db: Session) -> IntegrationSettings:
        settings = _get_or_create_settings(db)
        settings.two_factor_enabled = True
        settings.session_timeout_minutes = 15
        settings.attendance_sync_frequency_minutes = 15
        settings.payroll_sync_frequency_minutes = 30
        settings.retry_failed_syncs_count = 3
        settings.email_notifications = True
        settings.push_notifications = True
        settings.sms_notifications = False
        settings.alert_threshold = "High: Any error"
        settings.overtime_multiplier = 1.5
        settings.holiday_pay_multiplier = 2.0
        settings.monthly_working_days = 30
        settings.daily_hours = 8.0
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
        return settings



payroll_integration_service = PayrollIntegrationService()