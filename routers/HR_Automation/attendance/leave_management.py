"""
routers/leave_management.py
FastAPI router — Leave Management System (all 7 tabs).
Prefix : /api/attendance/leave
Auth   : JWT via get_current_user / require_hr_admin
"""

import io
from datetime import date
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    Query, Path, UploadFile, File,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user

from model.HR_Automation.leave_management import ApplicationStatusEnum, CompOffStatusEnum
from schema.HR_Automation.leave_management import (
    LeaveTypeCreateIn, LeaveTypeUpdateIn, LeaveTypeOut,
    LeaveBalanceOut, AdjustBalanceIn,
    LeaveApplicationIn, LeaveApplicationOut,
    ApproveRejectIn, OverlapCheckOut,
    CalendarOut,
    CompOffCreateIn, CompOffOut,
    CampaignCreateIn, CampaignOut, CoverageOut,
    DelegationCreateIn, DelegationOut,
    MessageResponse, AccrualResultOut, LapseResultOut,
)
from services.HR_Automation.leave_management import (
    LeaveTypeService, LeaveBalanceService,
    LeaveApplicationService, LeaveCalendarService,
    CompOffService, LeavePlanningService, DelegationService,
)

router = APIRouter(
    prefix="/api/attendance/leave",
    tags=["Leave Management System"],
)


# ══════════════════════════════════════════════════════════
# TAB 1 — LEAVE TYPES
# ══════════════════════════════════════════════════════════

@router.get("/types", response_model=List[LeaveTypeOut])
def list_leave_types(
    active_only: bool    = Query(False),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Leave Type Configuration table.
    Columns: Leave Type · Code · Paid badge · Accrual · Carry Forward
             Encashment · Half Day · Status · Actions (✏ 🗑)
    Returns display strings for every column so the frontend
    needs no local formatting logic.
    """
    return LeaveTypeService.list(db, active_only)


@router.post("/types", response_model=LeaveTypeOut, status_code=status.HTTP_201_CREATED)
def create_leave_type(
    payload:     LeaveTypeCreateIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + Add Leave Type button → modal → Save Leave Type.
    Modal fields: Name* · Code* · isPaid · accrualType · accrualAmount
                  maxAccrual · carryForward · encashment · allowHalfDay
                  allowNegative · probationApplicable · sandwichLeave
                  allowBackdated · allowShortLeave · isOptional
                  usageLimit · proration · approvalWorkflow
    """
    try:
        return LeaveTypeService.create(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/types/{lt_id}", response_model=LeaveTypeOut)
def get_leave_type(
    lt_id:       int    = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Returns one leave type — used to pre-populate the Edit modal."""
    try:
        lt = LeaveTypeService.get(db, lt_id)
        from services.HR_Automation.leave_management import _build_lt_out
        return _build_lt_out(lt)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.put("/types/{lt_id}", response_model=LeaveTypeOut)
def update_leave_type(
    lt_id:       int               = Path(...),
    payload:     LeaveTypeUpdateIn = ...,
    db:          Session           = Depends(get_db),
    current_user                   = Depends(get_current_user),
):
    """✏ Edit icon → Edit modal → Update Leave Type."""
    try:
        return LeaveTypeService.update(db, lt_id, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.delete("/types/{lt_id}", response_model=MessageResponse)
def delete_leave_type(
    lt_id:       int    = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    🗑 Trash icon — soft-deletes the leave type (is_active=False).
    Blocked if pending applications exist.
    """
    try:
        LeaveTypeService.delete(db, lt_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"message": f"Leave type {lt_id} deactivated."}


# ══════════════════════════════════════════════════════════
# TAB 2 — LEAVE BALANCE
# ══════════════════════════════════════════════════════════

@router.get("/balances", response_model=List[LeaveBalanceOut])
def list_balances(
    employee_id:   Optional[str] = Query(None),
    leave_type_id: Optional[int] = Query(None),
    year:          Optional[int] = Query(None),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(get_current_user),
):
    """
    Leave Balance Management table.
    Columns: Employee · Leave Type · Opening · Accrued · Used
             Carry Fwd · Encashed · Balance · Projected · Actions
    Header buttons: Auto Accrual · Process Lapse · Export Statement · Adjust Balance
    """
    return LeaveBalanceService.list(db, employee_id, leave_type_id, year)


@router.post("/balances/adjust", response_model=MessageResponse)
def adjust_balance(
    payload:     AdjustBalanceIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + Adjust Balance button → modal → Save Balance.
    Modal fields: Employee · Leave Type · Opening Balance
                  Adjustment Type (credit/debit) · Adjustment Amount
                  Effective Date · Reason
    Also used for Add Opening Balance (empty state button).
    """
    try:
        LeaveBalanceService.adjust(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"message": "Balance adjusted successfully."}


@router.post("/balances/auto-accrual", response_model=AccrualResultOut)
def auto_accrual(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Auto Accrual button (green) — runs monthly accrual for all
    active employees across all monthly leave types.
    Respects probation_applicable and max_accrual cap.
    """
    return LeaveBalanceService.run_auto_accrual(db)


@router.post("/balances/process-lapse", response_model=LapseResultOut)
def process_lapse(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Process Lapse button (yellow) — expires carry-forward balances
    that have exceeded their expiryMonths window.
    """
    return LeaveBalanceService.process_lapse(db)


@router.get("/balances/export-statement")
def export_statement(
    employee_id: Optional[str] = Query(None,
                                       description="Omit to export all employees"),
    year:        int            = Query(default_factory=lambda: date.today().year),
    db:          Session        = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    """
    Export Statement button (blue) — downloads leave balance CSV.
    Columns: Employee · Leave Type · Opening · Accrued · Used
             Carry Fwd · Encashed · Balance
    """
    csv_bytes = LeaveBalanceService.export_statement(db, employee_id, year)
    filename  = f"leave_statement_{year}.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ══════════════════════════════════════════════════════════
# TAB 3 — APPLICATIONS
# ══════════════════════════════════════════════════════════

@router.get("/applications", response_model=dict)
def list_applications(
    employee_id:   Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status",
                                          description="pending|approved|rejected|withdrawn"),
    search:        Optional[str] = Query(None,
                                         description="Search by employee name or leave type"),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(20, ge=1, le=200),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(get_current_user),
):
    """
    Leave Applications & Approval table.
    Columns: Employee · Leave Type · Dates · Days · Reason · Status · Actions
    Filters: Search box (name / leave type) · All Status dropdown
    Actions per row: ✓ Approve · ✗ Reject · ↩ Withdraw · 📎 View Attachment
    """
    st = ApplicationStatusEnum(status_filter) if status_filter else None
    return LeaveApplicationService.list(db, employee_id, st, search, page, page_size)


@router.post("/applications/check-overlap", response_model=OverlapCheckOut)
def check_overlap(
    employee_id: str          = Query(...),
    start_date:  date         = Query(...),
    end_date:    Optional[date] = Query(None),
    db:          Session      = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    """
    Called when the New Application modal dates are filled in —
    warns HR if the employee already has approved/pending leave
    in the same period.
    """
    return LeaveApplicationService.check_overlap(
        db, employee_id, start_date, end_date or start_date
    )


@router.post("/applications", response_model=List[LeaveApplicationOut],
             status_code=status.HTTP_201_CREATED)
def apply_leave(
    payload:     LeaveApplicationIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + New Application button → modal → Submit Application.
    Modal fields:
      Employee* · Leave Type* · Start Date* · End Date
      Half Day toggle (shown only if leave type allowHalfDay=True)
        → Half Day Type (First / Second)
      Reason* · Attachment (PDF/JPG/PNG)
      Bulk Leave toggle → employee checkbox list

    Auto-approves if days ≤ 1 (matches component logic).
    Deducts balance immediately on auto-approval.
    Builds multi-level approval workflow from leave type config.
    """
    try:
        apps = LeaveApplicationService.apply(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return apps


@router.post("/applications/{app_id}/decide",
             response_model=LeaveApplicationOut)
def decide_application(
    app_id:      int            = Path(...),
    payload:     ApproveRejectIn = ...,
    db:          Session        = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    """
    ✓ Approve / ✗ Reject buttons in Actions column.
    On approval  → deducts leave balance.
    On rejection → balance stays unchanged (was not deducted yet).
    """
    try:
        return LeaveApplicationService.decide(
            db, app_id, payload.approved, payload.rejectionReason, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.post("/applications/{app_id}/withdraw",
             response_model=LeaveApplicationOut)
def withdraw_application(
    app_id:      int    = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    ↩ Withdraw button — only pending applications can be withdrawn.
    Restores leave balance if application was auto-approved.
    """
    try:
        return LeaveApplicationService.withdraw(db, app_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# ══════════════════════════════════════════════════════════
# TAB 4 — CALENDAR
# ══════════════════════════════════════════════════════════

@router.get("/calendar", response_model=CalendarOut)
def get_calendar(
    year:        int           = Query(..., ge=2000, le=2100),
    month:       int           = Query(..., ge=1, le=12),
    department:  Optional[str] = Query(None),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """
    Leave Calendar & Planning — month grid view.
    ← / → arrow navigation changes year+month.
    Each day cell shows up to 3 employee names + leave type,
    with hasOverlap=True when >3 employees are on leave that day.
    Department-wise Leave Summary section above the calendar.
    """
    return LeaveCalendarService.get_month(db, year, month, department)


# ══════════════════════════════════════════════════════════
# TAB 5 — COMP-OFF
# ══════════════════════════════════════════════════════════

@router.get("/comp-off", response_model=List[CompOffOut])
def list_comp_offs(
    employee_id: Optional[str] = Query(None),
    status:      Optional[str] = Query(None,
                                       description="available|applied|expired"),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """
    Compensatory Off Management table.
    Columns: Employee · Earned Date · Hours · Source · Policy Type
             Expiry Date · Status · Actions (Apply button)
    Auto-marks expired records when listing.
    """
    st = CompOffStatusEnum(status) if status else None
    return CompOffService.list(db, employee_id, st)


@router.post("/comp-off", response_model=CompOffOut,
             status_code=status.HTTP_201_CREATED)
def add_comp_off(
    payload:     CompOffCreateIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + Add Comp-Off button → modal → Add Comp-Off.
    Modal fields:
      Employee* · Earned Date* · Hours Earned* · Source (Holiday/Weekend)
      Policy Type: Comp-Off (leave credit) | Overtime (monetary payment)
      Expiry Date (optional) · Description
    If policyType=compOff → automatically credits CO leave balance.
    """
    return CompOffService.create(db, payload, current_user.id)


@router.post("/comp-off/{comp_off_id}/apply",
             response_model=LeaveApplicationOut)
def apply_comp_off(
    comp_off_id: int    = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Apply button on each available comp-off row.
    Creates a pending LeaveApplication (isCompOff=True)
    and marks the comp-off as applied.
    """
    try:
        return CompOffService.apply_comp_off(db, comp_off_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# ══════════════════════════════════════════════════════════
# TAB 6 — PLANNING
# ══════════════════════════════════════════════════════════

@router.get("/planning/coverage", response_model=List[CoverageOut])
def get_coverage(
    start_date:  date          = Query(...),
    end_date:    date          = Query(...),
    department:  Optional[str] = Query(None,
                                       description="'All' or specific dept name"),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """
    Leave Planning & Coverage — Coverage Analysis cards.
    Each dept card: Total Employees · On Leave · Coverage% badge
    Badge colour: green ≥80% · yellow ≥60% · red <60%
    Filters: Department dropdown · Start Date · End Date
    """
    dept = None if (not department or department == "All") else department
    return LeavePlanningService.coverage(db, start_date, end_date, dept)


@router.get("/planning/campaigns", response_model=List[CampaignOut])
def list_campaigns(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Active Planning Campaigns table.
    Columns: Campaign Name · Period badge · Start Date · End Date
             Department · Status badge
    """
    return LeavePlanningService.list_campaigns(db)


@router.post("/planning/campaigns", response_model=CampaignOut,
             status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload:     CampaignCreateIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + Create Campaign button → modal → Create Campaign.
    Modal fields: Campaign Name* · Period (Quarterly/Annual)
                  Target Department · Start Date* · End Date* · Message
    """
    return LeavePlanningService.create_campaign(db, payload, current_user.id)


# ══════════════════════════════════════════════════════════
# TAB 7 — DELEGATION
# ══════════════════════════════════════════════════════════

@router.get("/delegations", response_model=List[DelegationOut])
def list_delegations(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Approval Delegation Management table.
    Columns: From Approver · To Approver · Start Date · End Date
             Reason · Status badge (Active / Inactive)
    isCurrentlyActive computed from date range vs today.
    """
    return DelegationService.list(db)


@router.post("/delegations", response_model=DelegationOut,
             status_code=status.HTTP_201_CREATED)
def setup_delegation(
    payload:     DelegationCreateIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + Setup Delegation button → modal → Setup Delegation.
    Modal fields: From Approver (Role)* · To Approver (Role)*
                  Start Date* · End Date* · Reason*
    e.g. "Manager" → "Deputy Manager" for a date range.
    Effective approver is resolved at application submission time.
    """
    return DelegationService.create(db, payload, current_user.id)


@router.delete("/delegations/{delegation_id}",
               response_model=MessageResponse)
def deactivate_delegation(
    delegation_id: int    = Path(...),
    db:            Session = Depends(get_db),
    current_user           = Depends(get_current_user),
):
    """Deactivate an active delegation immediately."""
    try:
        DelegationService.deactivate(db, delegation_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return {"message": f"Delegation {delegation_id} deactivated."}


