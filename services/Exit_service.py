"""
Router: Employee Separation & Exit Management
Prefix : /api/separation
Covers : Resignation → Clearance → Exit Interview → Settlement → Letters
"""
 
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
 
from schema.HR_Operations.letter_generation import (
    ResignationCreate, ResignationAccept, ResignationResponse,
    ClearanceInitiateRequest, ClearanceItemUpdate, ClearanceChecklistResponse,
    ExitInterviewSubmit, ExitInterviewResponse,
    FnFCalculateRequest, FnFSettlementResponse,
    ExitAnalyticsResponse,
)
from services.Exit_service import ExitService
from core.dependencies import get_db, get_current_user, require_roles
from core.dependencies import Role
 
router = APIRouter(prefix="/api/separation", tags=["Exit Management"])
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  RESIGNATION
# ═══════════════════════════════════════════════════════════════════════════════
 
@router.post(
    "/resign",
    response_model=ResignationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Employee submits resignation",
)
async def submit_resignation(
    payload: ResignationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.EMPLOYEE, Role.MANAGER, Role.HR_ADMIN])),
):
    """
    Logged-in employee submits a resignation.
    Triggers notification email to HR and direct manager.
    """
    return await ExitService.submit_resignation(db, payload, current_user.id)
 
 
@router.get(
    "/resign/{emp_id}",
    response_model=ResignationResponse,
    summary="Get resignation details for an employee",
)
async def get_resignation(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role == Role.EMPLOYEE and current_user.id != emp_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await ExitService.get_resignation(db, emp_id)
    if not result:
        raise HTTPException(status_code=404, detail="No active resignation found")
    return result
 
 
@router.put(
    "/resign/{resignation_id}/accept",
    response_model=ResignationResponse,
    summary="HR accepts an employee's resignation",
)
async def accept_resignation(
    resignation_id: int,
    payload: ResignationAccept,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
):
    """
    Sets last working day, marks notice period, and sends acceptance email.
    """
    return await ExitService.accept_resignation(db, resignation_id, payload, current_user.id)
 
 
@router.put(
    "/resign/{resignation_id}/revoke",
    response_model=ResignationResponse,
    summary="Employee revokes their resignation",
)
async def revoke_resignation(
    resignation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.EMPLOYEE, Role.MANAGER, Role.HR_ADMIN])),
):
    """
    Can only be done before HR accepts the resignation.
    """
    return await ExitService.revoke_resignation(db, resignation_id, current_user.id)
 
 
@router.get(
    "/notice-period/{emp_id}",
    summary="Get notice period status for an employee",
)
async def get_notice_period_status(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Returns days served, days remaining, buyout amount if applicable.
    """
    if current_user.role == Role.EMPLOYEE and current_user.id != emp_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await ExitService.get_notice_period_status(db, emp_id)
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  CLEARANCE CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════
 
@router.post(
    "/clearance/{emp_id}",
    response_model=ClearanceChecklistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate clearance workflow for an employee",
)
async def initiate_clearance(
    emp_id: int,
    payload: ClearanceInitiateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
):
    """
    Seeds default clearance tasks (IT, Finance, Admin, HR).
    Optionally accepts custom tasks via request body.
    """
    return await ExitService.initiate_clearance(db, emp_id, payload, current_user.id)
 
 
@router.get(
    "/clearance/{emp_id}",
    response_model=ClearanceChecklistResponse,
    summary="Get clearance checklist status for an employee",
)
async def get_clearance_status(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN, Role.MANAGER])),
):
    result = await ExitService.get_clearance(db, emp_id)
    if not result:
        raise HTTPException(status_code=404, detail="Clearance checklist not found")
    return result
 
 
@router.put(
    "/clearance/{checklist_item_id}/complete",
    response_model=ClearanceChecklistResponse,
    summary="Mark a clearance checklist item as complete",
)
async def complete_clearance_item(
    checklist_item_id: int,
    payload: ClearanceItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN, Role.MANAGER])),
):
    """
    Called by the respective department (IT/Finance/Admin/HR) when their
    clearance task is done.  Automatically marks overall checklist COMPLETED
    when all items are done.
    """
    return await ExitService.complete_clearance_item(
        db, checklist_item_id, payload, current_user.id
    )
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  EXIT INTERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
 
@router.post(
    "/exit-interview",
    response_model=ExitInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Employee submits exit interview responses",
)
async def submit_exit_interview(
    payload: ExitInterviewSubmit,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.EMPLOYEE, Role.MANAGER, Role.HR_ADMIN])),
):
    """
    Employee fills the exit interview form.
    AI sentiment analysis runs asynchronously (OpenAI GPT-4).
    """
    interview = await ExitService.submit_exit_interview(db, payload, current_user.id)
    background_tasks.add_task(ExitService.run_sentiment_analysis, db, interview.id)
    return interview
 
 
@router.get(
    "/exit-interview/{emp_id}",
    response_model=ExitInterviewResponse,
    summary="Get exit interview data for an employee (HR Admin)",
)
async def get_exit_interview(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
):
    result = await ExitService.get_exit_interview(db, emp_id)
    if not result:
        raise HTTPException(status_code=404, detail="Exit interview not found")
    return result
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  FULL & FINAL SETTLEMENT
# ═══════════════════════════════════════════════════════════════════════════════
 
@router.post(
    "/settlement/{emp_id}/calculate",
    response_model=FnFSettlementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calculate Full & Final settlement for an employee",
)
async def calculate_settlement(
    emp_id: int,
    payload: FnFCalculateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
):
    """
    Computes gross earnings, total deductions, and net payable.
    Generates settlement PDF in the background.
    """
    settlement = await ExitService.calculate_settlement(db, emp_id, payload, current_user.id)
    background_tasks.add_task(ExitService.generate_settlement_pdf, db, settlement.id)
    return settlement
 
 
@router.get(
    "/settlement/{emp_id}",
    response_model=FnFSettlementResponse,
    summary="Get settlement breakdown for an employee",
)
async def get_settlement(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role == Role.EMPLOYEE and current_user.id != emp_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await ExitService.get_settlement(db, emp_id)
    if not result:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return result
 
 
@router.patch(
    "/settlement/{settlement_id}/approve",
    response_model=FnFSettlementResponse,
    summary="Approve Full & Final settlement",
)
async def approve_settlement(
    settlement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
):
    return await ExitService.approve_settlement(db, settlement_id, current_user.id)
 
 
@router.patch(
    "/settlement/{settlement_id}/mark-paid",
    response_model=FnFSettlementResponse,
    summary="Mark Full & Final settlement as paid",
)
async def mark_settlement_paid(
    settlement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
):
    return await ExitService.mark_settlement_paid(db, settlement_id, current_user.id)
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  SEPARATION LETTERS (Experience / Relieving)
# ═══════════════════════════════════════════════════════════════════════════════
 
@router.post(
    "/letters/{emp_id}/generate",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Experience Letter and/or Relieving Letter",
)
async def generate_separation_letters(
    emp_id: int,
    letter_types: List[str],               # e.g. ["experience", "relieving"]
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
):
    """
    Generates the specified letter type(s) for the employee.
    PDFs are stored in S3/local and can be sent via /api/hr-letters/{id}/send-email.
 
    Prerequisites:
    - Resignation must be ACCEPTED
    - Clearance must be COMPLETED
    - Settlement must be APPROVED
    """
    letter_ids = await ExitService.generate_separation_letters(
        db, emp_id, letter_types, current_user.id
    )
    background_tasks.add_task(ExitService.send_separation_email, db, emp_id, letter_ids)
    return {
        "message": "Separation letters generated successfully.",
        "letter_ids": letter_ids,
    }
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
 
@router.get(
    "/analytics",
    response_model=ExitAnalyticsResponse,
    summary="Attrition and exit analytics dashboard",
)
async def exit_analytics(
    from_date: str = None,   # YYYY-MM-DD
    to_date: str = None,
    department_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
):
    """
    Aggregated analytics: headcount attrition, exit reasons, monthly trends,
    sentiment breakdown from exit interviews, department-wise stats.
    """
    return await ExitService.get_exit_analytics(
        db,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
    )