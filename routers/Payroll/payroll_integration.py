from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from core.dependencies import get_db
from schema.Payroll.payroll_integration import (
    IntegrationSettingsUpdate, IntegrationSettingsOut,
    SyncTriggerRequest, AttendanceSyncLogOut,
    AttendanceFreezeCreate, AttendanceFreezeOut,
    EmployeeAttendancePayrollOut, RunPayrollRequest,
    CalculationRuleCreate, CalculationRuleUpdate, CalculationRuleOut,
    AttendanceCorrectionCreate, CorrectionReviewRequest, AttendanceCorrectionOut,
    SystemAlertOut, ResolveAlertRequest,
    DashboardSummaryOut,
    IntegrationReportOut,
)
from services.Payroll.payroll_integration_service import PayrollIntegrationService

router = APIRouter(
    prefix="/payroll-integration",
    tags=["Payroll Integration"]
)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    month: Optional[str] = None,
    department: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns all 8 summary cards on the Dashboard tab:
    Real-time Sync, Data Status, Total Loss of Pay, Overtime Pay,
    Holiday Pay, Leave Without Pay, Pending Corrections, Processed Payroll.
    """
    return PayrollIntegrationService(db).get_dashboard_summary(month, department, location)


# ── Integration Settings ──────────────────────────────────────────────────────

@router.get("/settings", response_model=IntegrationSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    """Returns Integration Settings & Configuration (Settings tab)."""
    return PayrollIntegrationService(db).get_settings()

@router.put("/settings", response_model=IntegrationSettingsOut)
def update_settings(data: IntegrationSettingsUpdate, db: Session = Depends(get_db)):
    """Updates Security, Sync, Notification, and Calculation Settings."""
    return PayrollIntegrationService(db).update_settings(data)


# ── Sync ──────────────────────────────────────────────────────────────────────

@router.post("/sync", response_model=AttendanceSyncLogOut)
def trigger_sync(data: SyncTriggerRequest, db: Session = Depends(get_db)):
    """Manual sync trigger — Sync Now / Payroll Sync buttons on Integration tab."""
    return PayrollIntegrationService(db).trigger_sync(data)

@router.get("/sync/logs", response_model=List[AttendanceSyncLogOut])
def get_sync_logs(
    sync_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db)
):
    """Returns sync history logs for Integration Status panel."""
    return PayrollIntegrationService(db).get_sync_logs(sync_type, limit)

@router.get("/sync/status")
def get_sync_status(db: Session = Depends(get_db)):
    """
    Returns live Integration Status sidebar:
    Attendance Sync (last sync, frequency), Payroll Sync, Data Freshness, System Health.
    """
    return PayrollIntegrationService(db).get_sync_status()


# ── Attendance Freeze ─────────────────────────────────────────────────────────

@router.get("/freeze", response_model=AttendanceFreezeOut)
def get_freeze_status(db: Session = Depends(get_db)):
    """Returns current freeze status — Integration tab Attendance Freeze card."""
    return PayrollIntegrationService(db).get_freeze_status()

@router.post("/freeze", response_model=AttendanceFreezeOut, status_code=201)
def create_freeze_period(data: AttendanceFreezeCreate, db: Session = Depends(get_db)):
    """Creates a new freeze period configuration."""
    return PayrollIntegrationService(db).create_freeze_period(data)

@router.post("/freeze/freeze-now", response_model=AttendanceFreezeOut)
def freeze_now(frozen_by: str, db: Session = Depends(get_db)):
    """Freeze Now button — locks attendance data for payroll processing."""
    return PayrollIntegrationService(db).freeze_now(frozen_by)

@router.post("/freeze/unfreeze", response_model=AttendanceFreezeOut)
def unfreeze(unfrozen_by: str, db: Session = Depends(get_db)):
    """Unfreezes attendance data."""
    return PayrollIntegrationService(db).unfreeze(unfrozen_by)


# ── Payroll Calculation ───────────────────────────────────────────────────────

@router.get("/calculation", response_model=List[EmployeeAttendancePayrollOut])
def get_payroll_calculation(
    period_month: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns Payroll Calculation Details table:
    Employee, Department, Present Days, Absent Days, Overtime Hrs,
    Holiday Work, Basic Salary, Loss of Pay, Net Pay.
    """
    return PayrollIntegrationService(db).get_payroll_calculation(period_month, department)

@router.post("/calculation/run", response_model=List[EmployeeAttendancePayrollOut])
def run_payroll(data: RunPayrollRequest, db: Session = Depends(get_db)):
    """Run Payroll button — triggers payroll calculation for the period."""
    return PayrollIntegrationService(db).run_payroll(data)

@router.get("/calculation/export")
def export_payroll_data(period_month: Optional[str] = None, db: Session = Depends(get_db)):
    """Export Data button on Payroll Calculation tab."""
    file_path, filename = PayrollIntegrationService(db).export_payroll_data(period_month)
    return FileResponse(file_path, filename=filename)


# ── Calculation Rules ─────────────────────────────────────────────────────────

@router.get("/calculation/rules", response_model=List[CalculationRuleOut])
def list_calculation_rules(db: Session = Depends(get_db)):
    """
    Returns all rules from Integration tab - Calculation Rules & Configuration:
    Loss of Pay, Overtime Hours Feed, Holiday Working Pay, Leave Without Pay Tracking.
    """
    return PayrollIntegrationService(db).list_calculation_rules()

@router.post("/calculation/rules", response_model=CalculationRuleOut, status_code=201)
def create_calculation_rule(data: CalculationRuleCreate, db: Session = Depends(get_db)):
    return PayrollIntegrationService(db).create_calculation_rule(data)

@router.put("/calculation/rules/{rule_id}", response_model=CalculationRuleOut)
def update_calculation_rule(rule_id: int, data: CalculationRuleUpdate, db: Session = Depends(get_db)):
    return PayrollIntegrationService(db).update_calculation_rule(rule_id, data)

@router.patch("/calculation/rules/{rule_id}/toggle", response_model=CalculationRuleOut)
def toggle_calculation_rule(rule_id: int, db: Session = Depends(get_db)):
    """Activate/deactivate a calculation rule (eye icon button on Integration tab)."""
    return PayrollIntegrationService(db).toggle_calculation_rule(rule_id)


# ── Corrections ───────────────────────────────────────────────────────────────

@router.get("/corrections", response_model=List[AttendanceCorrectionOut])
def list_corrections(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns Corrections tab table:
    Employee, Original Date, Correction Type, Original Value,
    Corrected Value, Payroll Impact, Status, Requested By.
    """
    return PayrollIntegrationService(db).list_corrections(status, employee_id)

@router.post("/corrections", response_model=AttendanceCorrectionOut, status_code=201)
def add_correction(data: AttendanceCorrectionCreate, db: Session = Depends(get_db)):
    """Add Correction button on Corrections tab."""
    return PayrollIntegrationService(db).add_correction(data)

@router.post("/corrections/{correction_id}/approve", response_model=AttendanceCorrectionOut)
def approve_correction(
    correction_id: int,
    data: CorrectionReviewRequest,
    db: Session = Depends(get_db)
):
    """Approve correction — green tick action button."""
    return PayrollIntegrationService(db).review_correction(correction_id, "APPROVED", data)

@router.post("/corrections/{correction_id}/reject", response_model=AttendanceCorrectionOut)
def reject_correction(
    correction_id: int,
    data: CorrectionReviewRequest,
    db: Session = Depends(get_db)
):
    """Reject correction — red X action button."""
    return PayrollIntegrationService(db).review_correction(correction_id, "REJECTED", data)

@router.get("/corrections/export")
def export_corrections(db: Session = Depends(get_db)):
    """Export Corrections button on Corrections tab."""
    file_path, filename = PayrollIntegrationService(db).export_corrections()
    return FileResponse(file_path, filename=filename)


# ── System Alerts ─────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=List[SystemAlertOut])
def list_alerts(is_resolved: Optional[bool] = False, db: Session = Depends(get_db)):
    """Returns Action Required alerts from Dashboard sidebar."""
    return PayrollIntegrationService(db).list_alerts(is_resolved)

@router.post("/alerts/{alert_id}/resolve", response_model=SystemAlertOut)
def resolve_alert(alert_id: int, data: ResolveAlertRequest, db: Session = Depends(get_db)):
    """Mark Resolved button on alert cards."""
    return PayrollIntegrationService(db).resolve_alert(alert_id, data)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports", response_model=List[IntegrationReportOut])
def list_reports(db: Session = Depends(get_db)):
    """
    Returns Reports tab cards:
    Payroll-Attendance Reconciliation, Loss of Pay Report, Overtime Payment Summary,
    Holiday Working Compensation, Leave Without Pay Report,
    Post-Payroll Correction Log, Attendance Freeze Log, Integration Health Report.
    """
    return PayrollIntegrationService(db).list_reports()

@router.get("/reports/{report_id}/generate")
def generate_report(
    report_id: int,
    format: str = Query(default="PDF", enum=["PDF", "Excel", "CSV"]),
    db: Session = Depends(get_db)
):
    """Download button on Reports tab cards."""
    file_path, filename = PayrollIntegrationService(db).generate_report(report_id, format)
    return FileResponse(file_path, filename=filename)
