"""
Router: Employee Separation & Exit Management
Prefix : /api/separation
Covers : Resignation → Clearance → Exit Interview → Settlement → Letters
         + Alumni Management + Employee Exits Report + Exit Trends
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlmodel import Session

from schema.HR_Operations.exit_management import (
    ResignationCreate, ResignationAccept, ResignationResponse,
    ClearanceInitiateRequest, ClearanceItemUpdate, ClearanceChecklistResponse,
    ExitInterviewSubmit, ExitInterviewResponse,
    FnFCalculateRequest, FnFSettlementResponse,
    ExitAnalyticsResponse,
    # New schemas
    AlumniCreate, AlumniUpdate, AlumniResponse,
    EmployeeExitsReportResponse,
    ExitTrendsResponse,
)
from services.Exit_service import ExitService
from core.dependencies import get_db, get_current_user, require_roles

router = APIRouter(prefix="/api/separation", tags=["Exit Management"])


# ═══════════════════════════════════════════════════════════════════════════════
#  RESIGNATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/resign", response_model=ResignationResponse,
    status_code=status.HTTP_201_CREATED, summary="Employee submits resignation")
def submit_resignation(payload: ResignationCreate, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["employee", "manager", "hr_admin", "superadmin"]))):
    return ExitService.submit_resignation(db, payload, current_user.id)


@router.get("/resign/{emp_id}", response_model=ResignationResponse,
    summary="Get resignation details for an employee")
def get_resignation(emp_id: int, db: Session = Depends(get_db),
    current_user=Depends(get_current_user)):
    if current_user.role == "employee" and current_user.id != emp_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = ExitService.get_resignation(db, emp_id)
    if not result:
        raise HTTPException(status_code=404, detail="No active resignation found")
    return result


@router.put("/resign/{resignation_id}/accept", response_model=ResignationResponse,
    summary="HR accepts an employee's resignation")
def accept_resignation(resignation_id: int, payload: ResignationAccept,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return ExitService.accept_resignation(db, resignation_id, payload, current_user.id)


@router.put("/resign/{resignation_id}/revoke", response_model=ResignationResponse,
    summary="Employee revokes their resignation")
def revoke_resignation(resignation_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["employee", "manager", "hr_admin", "superadmin"]))):
    return ExitService.revoke_resignation(db, resignation_id, current_user.id)


@router.get("/notice-period/{emp_id}", summary="Get notice period status")
def get_notice_period_status(emp_id: int, db: Session = Depends(get_db),
    current_user=Depends(get_current_user)):
    if current_user.role == "employee" and current_user.id != emp_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return ExitService.get_notice_period_status(db, emp_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  CLEARANCE CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/clearance/{emp_id}", response_model=ClearanceChecklistResponse,
    status_code=status.HTTP_201_CREATED, summary="Initiate clearance workflow")
def initiate_clearance(emp_id: int, payload: ClearanceInitiateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return ExitService.initiate_clearance(db, emp_id, payload, current_user.id)


@router.get("/clearance/{emp_id}", response_model=ClearanceChecklistResponse,
    summary="Get clearance checklist status")
def get_clearance_status(emp_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "manager"]))):
    result = ExitService.get_clearance(db, emp_id)
    if not result:
        raise HTTPException(status_code=404, detail="Clearance checklist not found")
    return result


@router.put("/clearance/{checklist_item_id}/complete",
    response_model=ClearanceChecklistResponse,
    summary="Mark a clearance checklist item as complete")
def complete_clearance_item(checklist_item_id: int, payload: ClearanceItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "manager"]))):
    return ExitService.complete_clearance_item(db, checklist_item_id, payload, current_user.id)


# ═══════════════════════════════════════════════════════════════════════════════
#  EXIT INTERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/exit-interview", response_model=ExitInterviewResponse,
    status_code=status.HTTP_201_CREATED, summary="Employee submits exit interview")
def submit_exit_interview(payload: ExitInterviewSubmit,
    background_tasks: BackgroundTasks, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["employee", "manager", "hr_admin", "superadmin"]))):
    interview = ExitService.submit_exit_interview(db, payload, current_user.id)
    background_tasks.add_task(ExitService.run_sentiment_analysis, db, interview.id)
    return interview


@router.get("/exit-interview/{emp_id}", response_model=ExitInterviewResponse,
    summary="Get exit interview data for an employee")
def get_exit_interview(emp_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    result = ExitService.get_exit_interview(db, emp_id)
    if not result:
        raise HTTPException(status_code=404, detail="Exit interview not found")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  FULL & FINAL SETTLEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/settlement/{emp_id}/calculate", response_model=FnFSettlementResponse,
    status_code=status.HTTP_201_CREATED, summary="Calculate Full & Final settlement")
def calculate_settlement(emp_id: int, payload: FnFCalculateRequest,
    background_tasks: BackgroundTasks, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    settlement = ExitService.calculate_settlement(db, emp_id, payload, current_user.id)
    background_tasks.add_task(ExitService.generate_settlement_pdf, db, settlement.id)
    return settlement


@router.get("/settlement/{emp_id}", response_model=FnFSettlementResponse,
    summary="Get settlement breakdown for an employee")
def get_settlement(emp_id: int, db: Session = Depends(get_db),
    current_user=Depends(get_current_user)):
    if current_user.role == "employee" and current_user.id != emp_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = ExitService.get_settlement(db, emp_id)
    if not result:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return result


@router.patch("/settlement/{settlement_id}/approve", response_model=FnFSettlementResponse,
    summary="Approve Full & Final settlement")
def approve_settlement(settlement_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return ExitService.approve_settlement(db, settlement_id, current_user.id)


@router.patch("/settlement/{settlement_id}/mark-paid", response_model=FnFSettlementResponse,
    summary="Mark Full & Final settlement as paid")
def mark_settlement_paid(settlement_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return ExitService.mark_settlement_paid(db, settlement_id, current_user.id)


# ═══════════════════════════════════════════════════════════════════════════════
#  SEPARATION LETTERS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/letters/{emp_id}/generate", status_code=status.HTTP_201_CREATED,
    summary="Generate Experience Letter and/or Relieving Letter")
def generate_separation_letters(emp_id: int, letter_types: List[str],
    background_tasks: BackgroundTasks, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    letter_ids = ExitService.generate_separation_letters(db, emp_id, letter_types, current_user.id)
    background_tasks.add_task(ExitService.send_separation_email, db, emp_id, letter_ids)
    return {"message": "Separation letters generated successfully.", "letter_ids": letter_ids}


# ═══════════════════════════════════════════════════════════════════════════════
#  EXIT CASES DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/cases", summary="Get all exit cases with progress and clearance status")
def get_exit_cases(
    department: Optional[str] = None,
    case_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "manager"])),
):
    """
    Returns exit cases with: employee info, dept, last day, clearance progress %,
    pending departments, status (In Progress / Completed / Pending / Escalated)
    """
    return ExitService.get_exit_cases(db, department=department, status=case_status)


@router.get("/cases/stats", summary="Exit cases dashboard stats")
def get_exit_cases_stats(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    """Returns: total_cases, pending, escalated, alumni count"""
    return ExitService.get_exit_cases_stats(db)


# ═══════════════════════════════════════════════════════════════════════════════
#  ALUMNI MANAGEMENT  ← NEW
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/alumni", response_model=AlumniResponse,
    status_code=status.HTTP_201_CREATED, summary="Add employee to alumni network")
def create_alumni(payload: AlumniCreate, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    """
    Creates alumni record after employee exit.
    Tracks rehire eligibility, boomerang flag, and engagement level.
    """
    return ExitService.create_alumni(db, payload, current_user.id)


@router.get("/alumni", response_model=List[AlumniResponse],
    summary="List all alumni")
def list_alumni(
    department: Optional[str] = None,
    rehire_eligible: Optional[bool] = None,
    boomerang: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    return ExitService.list_alumni(db, department=department,
        rehire_eligible=rehire_eligible, boomerang=boomerang)


@router.get("/alumni/{alumni_id}", response_model=AlumniResponse,
    summary="Get specific alumni record")
def get_alumni(alumni_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    result = ExitService.get_alumni(db, alumni_id)
    if not result:
        raise HTTPException(status_code=404, detail="Alumni not found")
    return result


@router.put("/alumni/{alumni_id}", response_model=AlumniResponse,
    summary="Update alumni record")
def update_alumni(alumni_id: int, payload: AlumniUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return ExitService.update_alumni(db, alumni_id, payload)


@router.delete("/alumni/{alumni_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove alumni record")
def delete_alumni(alumni_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    ExitService.delete_alumni(db, alumni_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  EMPLOYEE EXITS REPORT  ← NEW
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/reports/employee-exits", response_model=EmployeeExitsReportResponse,
    summary="Employee exits report with filters")
def employee_exits_report(
    location: Optional[str] = None,
    department: Optional[str] = None,
    exit_reason: Optional[str] = None,
    from_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    """
    Returns filterable employee exits list with:
    employee, location, department, designation, joining date,
    exit date, reason for exit. Supports Excel and PDF export.
    """
    return ExitService.get_employee_exits_report(
        db, location=location, department=department,
        exit_reason=exit_reason, from_date=from_date, to_date=to_date,
    )


@router.get("/reports/employee-exits/pdf", summary="Download employee exits report as PDF")
def download_exits_pdf(
    location: Optional[str] = None,
    department: Optional[str] = None,
    exit_reason: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    pdf_path = ExitService.export_exits_pdf(
        db, location=location, department=department,
        exit_reason=exit_reason, from_date=from_date, to_date=to_date,
    )
    return FileResponse(pdf_path, media_type="application/pdf",
        filename="employee_exits_report.pdf")


@router.get("/reports/employee-exits/excel", summary="Download employee exits report as Excel")
def download_exits_excel(
    location: Optional[str] = None,
    department: Optional[str] = None,
    exit_reason: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    excel_path = ExitService.export_exits_excel(
        db, location=location, department=department,
        exit_reason=exit_reason, from_date=from_date, to_date=to_date,
    )
    return FileResponse(excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="employee_exits_report.xlsx")


# ═══════════════════════════════════════════════════════════════════════════════
#  EXIT TRENDS ANALYSIS  ← NEW
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/trends", response_model=ExitTrendsResponse,
    summary="Exit trend analysis — exit rate, avg tenure, top exit reason")
def get_exit_trends(
    period: Optional[str] = Query(default="last_3_months",
        description="last_3_months / last_6_months / last_year / all"),
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    """
    Returns:
    - Exit Rate % (overall attrition trend)
    - Avg Tenure (employee stay duration in years)
    - Top Exit Reason (most common reason)
    - Monthly exit counts for chart
    - Department-wise breakdown
    """
    return ExitService.get_exit_trends(db, period=period, department=department)


# ═══════════════════════════════════════════════════════════════════════════════
#  EXISTING ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/analytics", response_model=ExitAnalyticsResponse,
    summary="Attrition and exit analytics dashboard")
def exit_analytics(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    return ExitService.get_exit_analytics(db, from_date=from_date,
        to_date=to_date, department_id=department_id)