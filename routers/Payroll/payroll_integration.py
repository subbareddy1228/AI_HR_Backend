from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io

from core.database import get_db
from schema.Payroll.payroll_integration import (
    DashboardSummary, PayrollProcessingStatus, PayrollImpactAnalysis,
    TopDeductionsAdditions,
    FreezeStatusOut, FreezeAction,
    IntegrationStatusOut, RealtimeDataFlowOut, SyncNowRequest,
    CalculationRuleOut, CalculationRuleUpdate,
    ActionItemOut, ActionResolve,
    PayrollCalculationOut, RunPayrollRequest,
    CorrectionCreate, CorrectionUpdate,
    ReportOut,
    IntegrationSettingsOut, IntegrationSettingsUpdate,
    IntegrationFilter,
)
from services.Payroll.payroll_integration_service import payroll_integration_service as svc

router = APIRouter(
    prefix="/integration",
    tags=["Attendance-Payroll Integration"],
)




def _build_filters(
    month: Optional[int], year: Optional[int],
    department: Optional[str], location: Optional[str], status: Optional[str],
) -> IntegrationFilter:
    return IntegrationFilter(month=month, year=year, department=department, location=location, status=status)




@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    month: Optional[int] = Query(None),
    year:  Optional[int] = Query(None),
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    
    filters = _build_filters(month, year, department, location, status)
    return svc.get_dashboard_summary(db, filters)


@router.get("/dashboard/processing-status", response_model=PayrollProcessingStatus)
def processing_status(
    month: int = Query(...),
    year:  int = Query(...),
    db: Session = Depends(get_db),
):
    
    return svc.get_processing_status(db, month, year)


@router.get("/dashboard/impact-analysis", response_model=PayrollImpactAnalysis)
def impact_analysis(
    month: Optional[int] = Query(None),
    year:  Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    
    filters = _build_filters(month, year, None, None, None)
    return svc.get_impact_analysis(db, filters)


@router.get("/dashboard/top-deductions-additions", response_model=TopDeductionsAdditions)
def top_deductions_additions(
    month: Optional[int] = Query(None),
    year:  Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    
    filters = _build_filters(month, year, None, None, None)
    return svc.get_top_deductions_additions(db, filters)




@router.get("/freeze-status", response_model=FreezeStatusOut)
def freeze_status(
    month: int = Query(...),
    year:  int = Query(...),
    db: Session = Depends(get_db),
):
    return svc.get_freeze_status(db, month, year)


@router.post("/freeze", response_model=FreezeStatusOut)
def freeze_for_payroll(
    month: int = Query(...),
    year:  int = Query(...),
    payload: FreezeAction = FreezeAction(),
    db: Session = Depends(get_db),
):
    return svc.freeze_for_payroll(db, month, year, payload.requested_by)


@router.post("/unfreeze", response_model=FreezeStatusOut)
def unfreeze(
    month: int = Query(...),
    year:  int = Query(...),
    db: Session = Depends(get_db),
):
    return svc.unfreeze(db, month, year)




@router.get("/calculation", response_model=PayrollCalculationOut)
def get_calculation(
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    
    filters = _build_filters(None, None, department, location, None)
    return svc.get_payroll_calculation(db, filters)


@router.post("/calculation/run-payroll")
def run_payroll(payload: RunPayrollRequest, db: Session = Depends(get_db)):
    
    return svc.run_payroll(db, payload)


@router.get("/calculation/export")
def export_calculation(
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    
    filters = _build_filters(None, None, department, location, None)
    csv_data = svc.export_calculation_csv(db, filters)
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=payroll_calculation.csv"},
    )




@router.get("/status", response_model=IntegrationStatusOut)
def integration_status(db: Session = Depends(get_db)):
    
    return svc.get_integration_status(db)


@router.post("/refresh-status", response_model=IntegrationStatusOut)
def refresh_status(db: Session = Depends(get_db)):
    
    return svc.refresh_status(db)


@router.get("/realtime-data-flow", response_model=RealtimeDataFlowOut)
def realtime_data_flow(db: Session = Depends(get_db)):
    
    return svc.get_realtime_data_flow(db)


@router.post("/sync-now")
def sync_now(payload: SyncNowRequest = SyncNowRequest(), db: Session = Depends(get_db)):
    
    return svc.sync_now(db, payload)


@router.post("/refresh-flow")
def refresh_flow_status(db: Session = Depends(get_db)):
    
    return svc.get_realtime_data_flow(db)



@router.get("/calculation-rules", response_model=list[CalculationRuleOut])
def list_calculation_rules(db: Session = Depends(get_db)):
    \
    return svc.list_calculation_rules(db)


@router.put("/calculation-rules/{rule_id}", response_model=CalculationRuleOut)
def update_calculation_rule(rule_id: int, payload: CalculationRuleUpdate, db: Session = Depends(get_db)):
   
    return svc.update_calculation_rule(db, rule_id, payload)


@router.post("/calculation-rules/{rule_id}/toggle", response_model=CalculationRuleOut)
def toggle_calculation_rule(rule_id: int, db: Session = Depends(get_db)):
    
    return svc.toggle_rule_active(db, rule_id)




@router.get("/action-items", response_model=list[ActionItemOut])
def list_action_items(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    return svc.list_action_items(db, active_only=active_only)


@router.post("/action-items/{item_id}/resolve", response_model=ActionItemOut)
def resolve_action_item(item_id: int, payload: ActionResolve = ActionResolve(), db: Session = Depends(get_db)):
    
    return svc.resolve_action_item(db, item_id, payload)


@router.post("/action-items/resolve-all")
def resolve_all_action_items(db: Session = Depends(get_db)):
    
    return svc.resolve_all_action_items(db)




@router.get("/corrections")
def list_corrections(
    status: Optional[str] = Query(None, description="PENDING | APPROVED | REJECTED"),
    db: Session = Depends(get_db),
):
    
    return svc.list_corrections(db, status_filter=status)


@router.post("/corrections", status_code=201)
def add_correction(payload: CorrectionCreate, db: Session = Depends(get_db)):
   
    return svc.add_correction(db, payload)


@router.put("/corrections/{correction_id}")
def update_correction(correction_id: int, payload: CorrectionUpdate, db: Session = Depends(get_db)):
    
    return svc.update_correction(db, correction_id, payload)


@router.post("/corrections/{correction_id}/approve")
def approve_correction(
    correction_id: int,
    reviewed_by: str = Query("Payroll Admin"),
    db: Session = Depends(get_db),
):
    
    return svc.approve_correction(db, correction_id, reviewed_by)


@router.post("/corrections/{correction_id}/reject")
def reject_correction(
    correction_id: int,
    reviewed_by: str = Query("Payroll Admin"),
    db: Session = Depends(get_db),
):
    
    return svc.reject_correction(db, correction_id, reviewed_by)


@router.get("/corrections/export")
def export_corrections(db: Session = Depends(get_db)):
    
    csv_data = svc.export_corrections_csv(db)
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_corrections.csv"},
    )




@router.get("/reports", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db)):
    
    return svc.list_reports(db)


@router.post("/reports/{report_key}/generate")
def generate_report(report_key: str, db: Session = Depends(get_db)):
    
    return svc.generate_report(db, report_key)


@router.get("/reports/export-all")
def export_all_reports(db: Session = Depends(get_db)):
   
    csv_data = svc.export_all_reports(db)
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=payroll_integration_reports.csv"},
    )




@router.get("/settings", response_model=IntegrationSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    
    return svc.get_settings(db)


@router.put("/settings", response_model=IntegrationSettingsOut)
def update_settings(payload: IntegrationSettingsUpdate, db: Session = Depends(get_db)):
  
    return svc.update_settings(db, payload)


@router.post("/settings/reset", response_model=IntegrationSettingsOut)
def reset_settings(db: Session = Depends(get_db)):
   
    return svc.reset_settings_to_defaults(db)