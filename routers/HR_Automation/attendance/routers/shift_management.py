"""
routers/shift_management.py
FastAPI router — Shift Management & Rostering module (all 6 tabs).
Prefix : /api/attendance/shifts
Auth   : JWT via get_current_user / require_hr_admin
"""

from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from model.HR_Automation.shift_management import SwapStatusEnum
from schema.HR_Automation.shift_management import (
    ShiftCreateIn, ShiftUpdateIn, ShiftOut,
    BulkAssignIn, IndividualAssignIn, ShiftAssignmentOut, AssignmentUpdateIn,
    GenerateRosterIn, RosterOut, PublishRosterOut,
    SwapRequestIn, SwapApprovalIn, SwapRequestOut,
    FlexibleArrangementIn, FlexibleArrangementOut,
    WorkHourRulesOut, WorkHourRulesUpdate,
    NotificationOut, MarkReadIn, MessageResponse,
)
from services.HR_Automation.shift_management_service import (
    ShiftMasterService, ShiftAssignmentService,
    RosteringService, ShiftSwapService,
    FlexibleArrangementService, WorkHourRulesService,
    NotificationService,
)

router = APIRouter(
    prefix="/api/attendance/shifts",
    tags=["Shift Management & Rostering"],
)


# ═══════════════════════════════════════════════════════════
# TAB 1 — SHIFT MASTER
# ═══════════════════════════════════════════════════════════

@router.get("/master", response_model=List[ShiftOut])
def list_shifts(
    search:     Optional[str] = Query(None, description="Search shifts..."),
    shift_type: Optional[str] = Query(None, description="All | general | night | rotational | flexible"),
    db:         Session       = Depends(get_db),
    current_user              = Depends(get_current_user),
):
    """
    Shift Master tab — the main shift table.
    Columns: Shift Name · Code · Type (badge) · Timing · Duration · Week Offs · Differential Pay · Status · Actions
    Filters: Search box + Type dropdown (All Types).
    """
    return ShiftMasterService.list_shifts(db, search, shift_type)


@router.post("/master", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
def create_shift(
    payload:     ShiftCreateIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Add Shift button → Add New Shift modal → Save Shift.
    Fields: Name* · Code* · Type · Rotation Pattern (rotational only)
            Duration · Start Time · End Time · Core Hours (flexible only)
            Grace Period · Differential Pay · Week Offs checkboxes
            Break Times (add/remove rows) · Description
            Allow Multiple Shifts Per Day toggle · Active toggle
    """
    try:
        return ShiftMasterService.create_shift(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/master/{shift_id}", response_model=ShiftOut)
def get_shift(
    shift_id: int    = Path(...),
    db:       Session = Depends(get_db),
    current_user      = Depends(get_current_user),
):
    try:
        return ShiftMasterService.get_shift(db, shift_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.put("/master/{shift_id}", response_model=ShiftOut)
def update_shift(
    shift_id: int          = Path(...),
    payload:  ShiftUpdateIn = ...,
    db:       Session       = Depends(get_db),
    current_user            = Depends(get_current_user),
):
    """Edit icon → Edit Shift modal → Update Shift."""
    try:
        return ShiftMasterService.update_shift(db, shift_id, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.delete("/master/{shift_id}", response_model=MessageResponse)
def delete_shift(
    shift_id:    int    = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Trash icon → delete shift (blocked if active assignments exist)."""
    try:
        ShiftMasterService.delete_shift(db, shift_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"message": f"Shift {shift_id} deleted."}


# ═══════════════════════════════════════════════════════════
# TAB 2 — SHIFT ASSIGNMENT
# ═══════════════════════════════════════════════════════════

@router.post("/assignments/bulk", response_model=List[ShiftAssignmentOut],
             status_code=status.HTTP_201_CREATED)
def bulk_assign(
    payload:     BulkAssignIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Bulk Shift Assignment panel.
    Select Shift dropdown + employee checkbox list → assign.
    Sends shift_assigned notification to each employee.
    """
    try:
        assignments = ShiftAssignmentService.bulk_assign(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return assignments


@router.post("/assignments/individual", response_model=ShiftAssignmentOut,
             status_code=status.HTTP_201_CREATED)
def individual_assign(
    payload:     IndividualAssignIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Individual Assignment panel.
    Employee · Shift · Start Date · End Date (optional) → Assign Shift button.
    """
    try:
        return ShiftAssignmentService.individual_assign(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.get("/assignments", response_model=List[ShiftAssignmentOut])
def list_assignments(
    employee_id: Optional[str] = Query(None),
    active_only: bool          = Query(True),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """Current Shift Assignments table — Employee · Shift · Start · End · Status · Edit."""
    assignments = ShiftAssignmentService.list_assignments(db, employee_id, active_only)
    # Enrich shift name
    result = []
    for a in assignments:
        out = ShiftAssignmentOut.model_validate(a)
        out.shift_name = a.shift.name if a.shift else ""
        result.append(out)
    return result


@router.put("/assignments/{assignment_id}", response_model=ShiftAssignmentOut)
def update_assignment(
    assignment_id: int              = Path(...),
    payload:       AssignmentUpdateIn = ...,
    db:            Session           = Depends(get_db),
    current_user                     = Depends(get_current_user),
):
    """Edit icon in Current Shift Assignments table."""
    try:
        return ShiftAssignmentService.update_assignment(db, assignment_id, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


# ═══════════════════════════════════════════════════════════
# TAB 3 — ROSTERING
# ═══════════════════════════════════════════════════════════

@router.post("/rosters/generate", response_model=RosterOut,
             status_code=status.HTTP_201_CREATED)
def generate_roster(
    payload:     GenerateRosterIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Generate Roster button.
    Inputs: shift_id · period (weekly/monthly) · start_date
    For rotational shifts: rotation_pattern (daily/weekly/biweekly) + rotation_shift_ids.
    Generates ShiftRosterDay rows for the period.
    """
    try:
        return RosteringService.generate_roster(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.get("/rosters", response_model=List[RosterOut])
def list_rosters(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Shift Rosters table — Name · Shift · Period · Start · End · Status · Published · Actions."""
    rosters = RosteringService.list_rosters(db)
    result  = []
    for r in rosters:
        out = RosterOut.model_validate(r)
        out.shift_name = r.shift.name if r.shift else ""
        result.append(out)
    return result


@router.get("/rosters/{roster_id}", response_model=RosterOut)
def get_roster(
    roster_id:   int    = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Eye icon — view roster detail with all day rows."""
    try:
        r = RosteringService.get_roster(db, roster_id)
        out = RosterOut.model_validate(r)
        out.shift_name = r.shift.name if r.shift else ""
        return out
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.post("/rosters/{roster_id}/publish", response_model=PublishRosterOut)
def publish_roster(
    roster_id:   int    = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Publish button — publishes the roster and sends notifications to all
    employees assigned in the roster days.
    """
    try:
        return RosteringService.publish_roster(db, roster_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# ═══════════════════════════════════════════════════════════
# TAB 4 — SHIFT SWAP
# ═══════════════════════════════════════════════════════════

@router.get("/swaps", response_model=List[SwapRequestOut])
def list_swap_requests(
    status_filter: Optional[str] = Query(None, alias="status",
                                          description="pending | approved | rejected"),
    employee_id:   Optional[str] = Query(None),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(get_current_user),
):
    """
    Shift Swap Requests table.
    Columns: Employee · Current Shift · Requested Shift · Swap Date · Reason · Status · Actions (✓ ✗)
    """
    st = SwapStatusEnum(status_filter) if status_filter else None
    requests = ShiftSwapService.list_requests(db, st, employee_id)
    result   = []
    for r in requests:
        out = SwapRequestOut.model_validate(r)
        out.employee_name        = r.employee.name if r.employee else r.employee_id
        out.current_shift_name   = r.current_shift.name   if r.current_shift   else ""
        out.requested_shift_name = r.requested_shift.name if r.requested_shift else ""
        result.append(out)
    return result


@router.post("/swaps", response_model=SwapRequestOut, status_code=status.HTTP_201_CREATED)
def create_swap_request(
    payload:     SwapRequestIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """New Swap Request button → modal → Submit Request."""
    return ShiftSwapService.create_swap_request(db, payload, current_user.id)


@router.post("/swaps/{request_id}/decision", response_model=SwapRequestOut)
def decide_swap(
    request_id:  int           = Path(...),
    payload:     SwapApprovalIn = ...,
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """
    ✓ (approve) or ✗ (reject) buttons in the Actions column.
    On approval: updates ShiftAssignment + sends notification.
    On rejection: sends rejection notification.
    """
    try:
        req = ShiftSwapService.approve_or_reject(
            db, request_id, payload.approved,
            payload.rejection_reason, current_user.id,
        )
        out = SwapRequestOut.model_validate(req)
        out.current_shift_name   = req.current_shift.name   if req.current_shift   else ""
        out.requested_shift_name = req.requested_shift.name if req.requested_shift else ""
        return out
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# ═══════════════════════════════════════════════════════════
# TAB 5 — FLEXIBLE WORK
# ═══════════════════════════════════════════════════════════

@router.get("/flexible", response_model=List[FlexibleArrangementOut])
def list_flexible(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Flexible Work Arrangements table.
    Columns: Employee · Type · Core Hours · Flexible Window · Remote Days · Status · Edit
    """
    arrangements = FlexibleArrangementService.list_all(db)
    result = []
    for a in arrangements:
        out = FlexibleArrangementOut.model_validate(a)
        out.employee_name = a.employee.name if a.employee else a.employee_id
        result.append(out)
    return result


@router.post("/flexible", response_model=FlexibleArrangementOut,
             status_code=status.HTTP_201_CREATED)
def save_flexible(
    payload:     FlexibleArrangementIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Add Arrangement button → Flexible Work Arrangement modal → Save.
    Handles all 4 types: flexible / hybrid / compressed / remote.
    - flexible / remote : remote_work_days checkboxes
    - hybrid            : office_days + remote_days
    - compressed        : compressed_work_days + compressed_hours_per_day
    """
    arr = FlexibleArrangementService.save(db, payload, current_user.id)
    out = FlexibleArrangementOut.model_validate(arr)
    out.employee_name = arr.employee.name if arr.employee else arr.employee_id
    return out


@router.delete("/flexible/{arrangement_id}", response_model=MessageResponse)
def deactivate_flexible(
    arrangement_id: int    = Path(...),
    db:             Session = Depends(get_db),
    current_user            = Depends(get_current_user),
):
    try:
        FlexibleArrangementService.deactivate(db, arrangement_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return {"message": "Arrangement deactivated."}


# ═══════════════════════════════════════════════════════════
# TAB 6 — WORK HOUR RULES
# ═══════════════════════════════════════════════════════════

@router.get("/rules", response_model=WorkHourRulesOut)
def get_rules(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Work Hour Rules tab — loads the singleton rules config.
    Sections: Attendance Rules · Overtime Rules · Break Management
    """
    return WorkHourRulesService.get(db)


@router.put("/rules", response_model=WorkHourRulesOut)
def update_rules(
    payload:     WorkHourRulesUpdate,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Save button on Work Hour Rules tab.
    Partial update — only supplied fields are changed.
    Fields map directly to every input/toggle visible in the UI.
    """
    return WorkHourRulesService.update(db, payload, current_user.id)


# ═══════════════════════════════════════════════════════════
# NOTIFICATIONS  (Bell icon panel — top right)
# ═══════════════════════════════════════════════════════════

@router.get("/notifications", response_model=List[NotificationOut])
def get_notifications(
    unread_only: bool = Query(False),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Bell button → Notifications panel.
    Shows last 100 shift change notifications for the current user's employee.
    Badge shows unread count.
    """
    return NotificationService.list_for_employee(
        db, current_user.employee_id, unread_only
    )


@router.post("/notifications/mark-read", response_model=MessageResponse)
def mark_notifications_read(
    payload:     MarkReadIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Mark All Read button — or pass specific notification_ids to mark selectively.
    """
    count = NotificationService.mark_read(
        db, current_user.employee_id, payload.notification_ids
    )
    return {"message": f"{count} notification(s) marked as read."}
