from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException
from datetime import datetime, timezone
import csv, io

from model.Payroll.payroll_integration import (
    IntegrationSettings, AttendanceSyncLog, AttendanceFreeze,
    EmployeeAttendancePayroll, CalculationRule, AttendanceCorrection,
    SystemAlert, IntegrationReport,
)
from schema.Payroll.payroll_integration import (
    IntegrationSettingsUpdate, SyncTriggerRequest,
    AttendanceFreezeCreate, RunPayrollRequest,
    CalculationRuleCreate, CalculationRuleUpdate,
    AttendanceCorrectionCreate, CorrectionReviewRequest,
    ResolveAlertRequest,
)


class PayrollIntegrationService:
    def __init__(self, db: Session):
        self.db = db

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_settings_row(self) -> IntegrationSettings:
        row = self.db.execute(select(IntegrationSettings)).scalar_one_or_none()
        if not row:
            row = IntegrationSettings()
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
        return row

    def _get_or_404(self, model, pk: int):
        obj = self.db.get(model, pk)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{model.__name__} {pk} not found")
        return obj

    # ── Dashboard ─────────────────────────────────────────────────────────────
    def get_dashboard_summary(self, month, department, location):
        # Build base query filtered by month/department if provided
        q = select(EmployeeAttendancePayroll)
        if month:
            q = q.where(EmployeeAttendancePayroll.period_month == month)
        if department:
            q = q.where(EmployeeAttendancePayroll.department == department)
        rows = self.db.execute(q).scalars().all()

        # Last sync info
        last_sync = self.db.execute(
            select(AttendanceSyncLog)
            .where(AttendanceSyncLog.sync_type == "attendance")
            .order_by(AttendanceSyncLog.synced_at.desc())
        ).scalar_one_or_none()

        # Pending corrections
        pending_corrections = self.db.execute(
            select(func.count(AttendanceCorrection.id))
            .where(AttendanceCorrection.status == "PENDING")
        ).scalar() or 0

        # Aggregates
        total_lop        = sum(r.loss_of_pay for r in rows)
        lop_affected     = sum(1 for r in rows if r.loss_of_pay > 0)
        total_ot_pay     = sum(r.overtime_pay for r in rows)
        avg_ot_hours     = (sum(r.overtime_hours for r in rows) / len(rows)) if rows else 0
        holiday_pay      = sum(r.holiday_pay for r in rows)
        lwp_days         = sum(r.lwp_days for r in rows)
        lwp_deduction    = sum(r.loss_of_pay for r in rows if r.lwp_days > 0)
        processed        = [r for r in rows if r.payroll_status == "approved"]
        processed_payroll= sum(r.net_pay for r in processed)

        # Sync freshness
        sync_hours = 0.0
        data_status = "No sync yet"
        if last_sync:
            delta = datetime.now(timezone.utc) - last_sync.synced_at.replace(tzinfo=timezone.utc)
            sync_hours = round(delta.total_seconds() / 3600, 1)
            data_status = "Live" if last_sync.status == "success" else "Stale"

        return {
            "real_time_sync_hours":       sync_hours,
            "data_status":                data_status,
            "total_loss_of_pay":          total_lop,
            "lop_affected_employees":     lop_affected,
            "overtime_pay":               total_ot_pay,
            "overtime_avg_hours":         round(avg_ot_hours, 1),
            "holiday_pay":                holiday_pay,
            "leave_without_pay_days":     lwp_days,
            "lwp_deduction":              lwp_deduction,
            "pending_corrections":        pending_corrections,
            "processed_payroll":          processed_payroll,
            "processed_payroll_employees": len(processed),
        }

    # ── Settings ──────────────────────────────────────────────────────────────
    def get_settings(self):
        return self._get_settings_row()

    def update_settings(self, data: IntegrationSettingsUpdate):
        row = self._get_settings_row()
        for k, v in data.model_dump().items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    # ── Sync ──────────────────────────────────────────────────────────────────
    def trigger_sync(self, data: SyncTriggerRequest):
        log = AttendanceSyncLog(
            sync_type=data.sync_type,
            status="success",
            records_synced=0,
            triggered_by="manual",
            duration_ms=0,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_sync_logs(self, sync_type, limit):
        q = select(AttendanceSyncLog).order_by(AttendanceSyncLog.synced_at.desc()).limit(limit)
        if sync_type:
            q = q.where(AttendanceSyncLog.sync_type == sync_type)
        return self.db.execute(q).scalars().all()

    def get_sync_status(self):
        att = self.db.execute(
            select(AttendanceSyncLog)
            .where(AttendanceSyncLog.sync_type == "attendance")
            .order_by(AttendanceSyncLog.synced_at.desc())
        ).scalar_one_or_none()

        pay = self.db.execute(
            select(AttendanceSyncLog)
            .where(AttendanceSyncLog.sync_type == "payroll")
            .order_by(AttendanceSyncLog.synced_at.desc())
        ).scalar_one_or_none()

        settings = self._get_settings_row()

        return {
            "attendance_sync": {
                "last_sync":    att.synced_at.isoformat() if att else None,
                "status":       att.status if att else "never",
                "frequency":    settings.attendance_sync_frequency,
            },
            "payroll_sync": {
                "last_sync":    pay.synced_at.isoformat() if pay else None,
                "status":       pay.status if pay else "never",
                "frequency":    settings.payroll_sync_frequency,
            },
            "data_freshness": "Live" if att and att.status == "success" else "Stale",
            "system_health":  "Healthy",
        }

    # ── Freeze ────────────────────────────────────────────────────────────────
    def get_freeze_status(self):
        row = self.db.execute(
            select(AttendanceFreeze).order_by(AttendanceFreeze.id.desc())
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="No freeze period configured yet")
        return row

    def create_freeze_period(self, data: AttendanceFreezeCreate):
        row = AttendanceFreeze(
            period_start=data.period_start,
            period_end=data.period_end,
            freeze_window=data.freeze_window,
            freeze_status="UNFROZEN",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def freeze_now(self, frozen_by: str):
        row = self.db.execute(
            select(AttendanceFreeze).order_by(AttendanceFreeze.id.desc())
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="No freeze period found")
        row.freeze_status = "FROZEN"
        row.frozen_by = frozen_by
        row.frozen_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return row

    def unfreeze(self, unfrozen_by: str):
        row = self.db.execute(
            select(AttendanceFreeze).order_by(AttendanceFreeze.id.desc())
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="No freeze period found")
        row.freeze_status = "UNFROZEN"
        row.unfrozen_by = unfrozen_by
        row.unfrozen_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return row

    # ── Payroll Calculation ───────────────────────────────────────────────────
    def get_payroll_calculation(self, period_month, department):
        q = select(EmployeeAttendancePayroll)
        if period_month:
            q = q.where(EmployeeAttendancePayroll.period_month == period_month)
        if department:
            q = q.where(EmployeeAttendancePayroll.department == department)
        return self.db.execute(q).scalars().all()

    def run_payroll(self, data: RunPayrollRequest):
        q = select(EmployeeAttendancePayroll).where(
            EmployeeAttendancePayroll.period_month == data.period_month
        )
        if data.department:
            q = q.where(EmployeeAttendancePayroll.department == data.department)
        rows = self.db.execute(q).scalars().all()
        for r in rows:
            r.payroll_status = "calculated"
        self.db.commit()
        return rows

    def export_payroll_data(self, period_month):
        q = select(EmployeeAttendancePayroll)
        if period_month:
            q = q.where(EmployeeAttendancePayroll.period_month == period_month)
        rows = self.db.execute(q).scalars().all()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Employee ID", "Name", "Department", "Period",
                         "Present Days", "Absent Days", "OT Hours",
                         "Basic Salary", "Loss of Pay", "Net Pay", "Status"])
        for r in rows:
            writer.writerow([r.employee_id, r.employee_name, r.department,
                             r.period_month, r.present_days, r.absent_days,
                             r.overtime_hours, r.basic_salary, r.loss_of_pay,
                             r.net_pay, r.payroll_status])

        file_path = f"/tmp/payroll_export_{period_month or 'all'}.csv"
        with open(file_path, "w") as f:
            f.write(buf.getvalue())
        return file_path, f"payroll_{period_month or 'all'}.csv"

    # ── Calculation Rules ─────────────────────────────────────────────────────
    def list_calculation_rules(self):
        return self.db.execute(
            select(CalculationRule).order_by(CalculationRule.display_order)
        ).scalars().all()

    def create_calculation_rule(self, data: CalculationRuleCreate):
        row = CalculationRule(**data.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_calculation_rule(self, rule_id: int, data: CalculationRuleUpdate):
        row = self._get_or_404(CalculationRule, rule_id)
        for k, v in data.model_dump().items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def toggle_calculation_rule(self, rule_id: int):
        row = self._get_or_404(CalculationRule, rule_id)
        row.is_active = not row.is_active
        self.db.commit()
        self.db.refresh(row)
        return row

    # ── Corrections ───────────────────────────────────────────────────────────
    def list_corrections(self, status, employee_id):
        q = select(AttendanceCorrection).order_by(AttendanceCorrection.requested_at.desc())
        if status:
            q = q.where(AttendanceCorrection.status == status.upper())
        if employee_id:
            q = q.where(AttendanceCorrection.employee_id == employee_id)
        return self.db.execute(q).scalars().all()

    def add_correction(self, data: AttendanceCorrectionCreate):
        row = AttendanceCorrection(**data.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def review_correction(self, correction_id: int, decision: str, data: CorrectionReviewRequest):
        row = self._get_or_404(AttendanceCorrection, correction_id)
        row.status = decision
        row.reviewed_by = data.reviewed_by
        row.reviewed_at = datetime.now(timezone.utc)
        row.review_remarks = data.review_remarks
        self.db.commit()
        self.db.refresh(row)
        return row

    def export_corrections(self):
        rows = self.db.execute(select(AttendanceCorrection)).scalars().all()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ID", "Employee ID", "Name", "Date", "Type",
                         "Original", "Corrected", "Impact", "Status", "Requested By"])
        for r in rows:
            writer.writerow([r.id, r.employee_id, r.employee_name,
                             r.original_date, r.correction_type,
                             r.original_value, r.corrected_value,
                             r.payroll_impact, r.status, r.requested_by])
        file_path = "/tmp/corrections_export.csv"
        with open(file_path, "w") as f:
            f.write(buf.getvalue())
        return file_path, "corrections.csv"

    # ── System Alerts ─────────────────────────────────────────────────────────
    def list_alerts(self, is_resolved):
        q = select(SystemAlert).where(SystemAlert.is_resolved == is_resolved).order_by(SystemAlert.created_at.desc())
        return self.db.execute(q).scalars().all()

    def resolve_alert(self, alert_id: int, data: ResolveAlertRequest):
        row = self._get_or_404(SystemAlert, alert_id)
        row.is_resolved = True
        row.resolved_by = data.resolved_by
        row.resolved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return row

    # ── Reports ───────────────────────────────────────────────────────────────
    def list_reports(self):
        return self.db.execute(
            select(IntegrationReport)
            .where(IntegrationReport.is_active == True)
            .order_by(IntegrationReport.id)
        ).scalars().all()

    def generate_report(self, report_id: int, format: str):
        row = self._get_or_404(IntegrationReport, report_id)
        file_path = f"/tmp/integration_report_{report_id}.{format.lower()}"
        # Write placeholder file
        with open(file_path, "w") as f:
            f.write(f"Integration Report: {row.report_name}\nFormat: {format}")
        row.last_generated = datetime.now(timezone.utc).date()
        self.db.commit()
        return file_path, f"{row.report_name}.{format.lower()}"