"""
routers/Forms_Workflows/approvals_dashboard.py

FastAPI router for the Approvals Dashboard module.

Mount in main.py:
    from routers.Forms_Workflows import approvals_dashboard as approvals_dashboard_router
    app.include_router(
        approvals_dashboard_router.router,
        prefix="/api/forms",
        tags=["Forms & Workflows – Approvals Dashboard"],
    )

Base URL: /api/forms/approvals-dashboard/

Endpoints:
  ── Core CRUD ──
  POST   /                              Create approval request
  GET    /                              List (paginated, filtered)
  GET    /{approval_id}                 Get full detail
  PATCH  /{approval_id}                 Update mutable fields
  DELETE /{approval_id}                 Soft delete

  ── Approval actions ──
  POST   /{approval_id}/approve         Approve
  POST   /{approval_id}/reject          Reject
  POST   /{approval_id}/escalate        Escalate to senior approver
  POST   /{approval_id}/reassign        Reassign to different approver
  POST   /{approval_id}/withdraw        Employee withdraws
  POST   /{approval_id}/hold            Put on hold

  ── Comments ──
  POST   /{approval_id}/comments        Add comment
  DELETE /comments/{comment_id}         Delete comment

  ── Statistics ──
  GET    /stats/summary                 Dashboard 4-card stats

  ── Delegation ──
  POST   /delegations/                  Create delegation
  GET    /delegations/                  List delegations
  PATCH  /delegations/{delegation_id}   Update delegation

  ── Admin / scheduler ──
  POST   /internal/refresh-sla          Bulk SLA refresh (called by scheduler)
  POST   /internal/auto-escalate        Auto-escalate SLA-breached records
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db

import services.Forms_Workflows.approvals_dashboard_service as svc

from schema.Forms_Workflows.approval import (
    ApprovalCommentCreate,
    ApprovalCommentOut,
    ApprovalDelegationCreate,
    ApprovalDelegationOut,
    ApprovalDelegationUpdate,
    ApprovalsDashboardCreate,
    ApprovalsDashboardDetail,
    ApprovalsDashboardFilters,
    ApprovalsDashboardListItem,
    ApprovalsDashboardPage,
    ApprovalsDashboardStats,
    ApprovalsDashboardUpdate,
    ApprovePayload,
    EscalatePayload,
    OnHoldPayload,
    ReassignPayload,
    RejectPayload,
    WithdrawPayload,
)

router = APIRouter(
    prefix="/approvals-dashboard",
    tags=["Forms & Workflows – Approvals Dashboard"],
)


def _to_list_item(record) -> ApprovalsDashboardListItem:

    return ApprovalsDashboardListItem.model_validate(record)


def _to_detail(record) -> ApprovalsDashboardDetail:
 
    return ApprovalsDashboardDetail.model_validate(record)



@router.post(
    "/",
    response_model=ApprovalsDashboardDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new approval request",
    description=(
        "Creates a new entry in the Approvals Dashboard. "
        "The `approval_code` (APR-YYYY-NNNNNN) is generated server-side. "
        "An initial history entry with status `Pending` is recorded automatically."
    ),
)
def create_approval(
    payload: ApprovalsDashboardCreate,
    db     : Session = Depends(get_db),
) -> ApprovalsDashboardDetail:
    record = svc.create_approval(payload, db)
    return _to_detail(record)


@router.get(
    "/",
    response_model=ApprovalsDashboardPage,
    summary="List approval requests (paginated + filtered)",
    description=(
        "Supports all filter fields shown in the UI: status, type, priority, "
        "employee, date range, search text, view_mode (Employee / Manager). "
        "Returns paginated results with total count."
    ),
)
def list_approvals(

    view_mode      : str             = Query(default="Employee", description="Employee | Manager"),

    status_filter  : Optional[str]   = Query(default=None, alias="status",         description="Pending | Approved | Rejected | Escalated | On Hold | Withdrawn"),
    reference_type : Optional[str]   = Query(default=None,                         description="leave | transfer | reimbursement | …"),
    priority       : Optional[str]   = Query(default=None,                         description="Low | Medium | High | Urgent"),
    employee_id    : Optional[int]   = Query(default=None),
    employee_name  : Optional[str]   = Query(default=None),
    assigned_to_id : Optional[int]   = Query(default=None),
    sla_status     : Optional[str]   = Query(default=None,                         description="On Track | At Risk | SLA Breached"),
    date_from      : Optional[str]   = Query(default=None,                         description="ISO date string, e.g. 2024-01-01"),
    date_to        : Optional[str]   = Query(default=None,                         description="ISO date string, e.g. 2024-12-31"),
    search         : Optional[str]   = Query(default=None,                         description="Search on subject / employee name / approval code"),
    # ── Pagination ──
    page           : int             = Query(default=1,  ge=1),
    size           : int             = Query(default=20, ge=1, le=200),
    db             : Session         = Depends(get_db),
) -> ApprovalsDashboardPage:
    from datetime import datetime

    def _parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date format: '{value}'. Use ISO 8601, e.g. 2024-01-01.",
            )

    filters = ApprovalsDashboardFilters(
        view_mode      = view_mode,
        status         = status_filter,
        reference_type = reference_type,
        priority       = priority,
        employee_id    = employee_id,
        employee_name  = employee_name,
        assigned_to_id = assigned_to_id,
        sla_status     = sla_status,
        date_from      = _parse_dt(date_from),
        date_to        = _parse_dt(date_to),
        search         = search,
        page           = page,
        size           = size,
    )

    total, items = svc.list_approvals(filters, db)

    return ApprovalsDashboardPage(
        total = total,
        page  = page,
        size  = size,
        items = [_to_list_item(r) for r in items],
    )


@router.get(
    "/{approval_id}",
    response_model=ApprovalsDashboardDetail,
    summary="Get full approval detail",
    description="Returns the complete approval record including history log and comments.",
)
def get_approval(
    approval_id : int,
    db          : Session = Depends(get_db),
) -> ApprovalsDashboardDetail:
    record = svc.get_approval(approval_id, db)
    return _to_detail(record)


@router.patch(
    "/{approval_id}",
    response_model=ApprovalsDashboardDetail,
    summary="Update mutable fields",
    description=(
        "Partial update — only supplied fields are changed. "
        "Only allowed when the request is in Pending or On Hold state."
    ),
)
def update_approval(
    approval_id : int,
    payload     : ApprovalsDashboardUpdate,
    db          : Session = Depends(get_db),
) -> ApprovalsDashboardDetail:
    record = svc.update_approval(approval_id, payload, db)
    return _to_detail(record)


@router.delete(
    "/{approval_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete an approval request",
    description="Marks the record as deleted; does not physically remove it.",
)
def delete_approval(
    approval_id : int,
    deleted_by  : str = Query(..., description="Name / username of the actor deleting the record"),
    db          : Session = Depends(get_db),
) -> None:
    svc.soft_delete(approval_id, deleted_by, db)

@router.post(
    "/{approval_id}/approve",
    response_model=ApprovalsDashboardDetail,
    summary="Approve a request (Manager View)",
    description=(
        "Transitions the request to Approved. "
        "Records the action in history. "
        "Only allowed from Pending, On Hold, or Escalated state."
    ),
)
def approve_request(
    approval_id : int,
    payload     : ApprovePayload,
    db          : Session = Depends(get_db),
) -> ApprovalsDashboardDetail:
    record = svc.approve_request(approval_id, payload, db)
    return _to_detail(record)


@router.post(
    "/{approval_id}/reject",
    response_model=ApprovalsDashboardDetail,
    summary="Reject a request (Manager View)",
    description="Transitions the request to Rejected. A reason (comments) is mandatory.",
)
def reject_request(
    approval_id : int,
    payload     : RejectPayload,
    db          : Session = Depends(get_db),
) -> ApprovalsDashboardDetail:
    record = svc.reject_request(approval_id, payload, db)
    return _to_detail(record)


@router.post(
    "/{approval_id}/escalate",
    response_model=ApprovalsDashboardDetail,
    summary="Escalate to a senior approver (Manager View)",
    description=(
        "Transitions to Escalated status, sets a new assignee, "
        "and records the escalation reason in history."
    ),
)
def escalate_request(
    approval_id : int,
    payload     : EscalatePayload,
    db          : Session = Depends(get_db),
) -> ApprovalsDashboardDetail:
    record = svc.escalate_request(approval_id, payload, db)
    return _to_detail(record)


@router.post(
    "/{approval_id}/reassign",
    response_model=ApprovalsDashboardDetail,
    summary="Reassign to a different approver",
    description="Changes the `assigned_to` without changing the status.",
)
def reassign_request(
    approval_id : int,
    payload     : ReassignPayload,
    db          : Session = Depends(get_db),
) -> ApprovalsDashboardDetail:
    record = svc.reassign_request(approval_id, payload, db)
    return _to_detail(record)


@router.post(
    "/{approval_id}/withdraw",
    response_model=ApprovalsDashboardDetail,
    summary="Withdraw a request (Employee View)",
    description="Allows the requesting employee to cancel a pending request.",
)
def withdraw_request(
    approval_id : int,
    payload     : WithdrawPayload,
    db          : Session = Depends(get_db),
) -> ApprovalsDashboardDetail:
    record = svc.withdraw_request(approval_id, payload, db)
    return _to_detail(record)


@router.post(
    "/{approval_id}/hold",
    response_model=ApprovalsDashboardDetail,
    summary="Put a request on hold (Manager View)",
    description="Temporarily pauses the approval process; can be resumed later.",
)
def put_on_hold(
    approval_id : int,
    payload     : OnHoldPayload,
    db          : Session = Depends(get_db),
) -> ApprovalsDashboardDetail:
    record = svc.put_on_hold(approval_id, payload, db)
    return _to_detail(record)


@router.post(
    "/{approval_id}/comments",
    response_model=ApprovalCommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to an approval request",
    description=(
        "Internal comments (is_internal=true) are visible only to HR / managers. "
        "Public comments (is_internal=false) are visible to the requesting employee."
    ),
)
def add_comment(
    approval_id : int,
    payload     : ApprovalCommentCreate,
    db          : Session = Depends(get_db),
) -> ApprovalCommentOut:
    comment = svc.add_comment(approval_id, payload, db)
    return ApprovalCommentOut.model_validate(comment)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
)
def delete_comment(
    comment_id : int,
    db         : Session = Depends(get_db),
) -> None:
    svc.delete_comment(comment_id, db)


@router.get(
    "/stats/summary",
    response_model=ApprovalsDashboardStats,
    summary="Approvals Dashboard summary statistics",
    description=(
        "Returns aggregated counts for the 4 top cards "
        "(Total / Pending / Approved / Rejected) plus SLA breakdown. "
        "Pass `view_mode=Employee&employee_id=X` for employee view or "
        "`view_mode=Manager&assigned_to_id=Y` for manager view."
    ),
)
def get_dashboard_stats(
    view_mode      : str          = Query(default="Employee",  description="Employee | Manager"),
    employee_id    : Optional[int]= Query(default=None,        description="Filter by requesting employee (Employee View)"),
    assigned_to_id : Optional[int]= Query(default=None,        description="Filter by approver (Manager View)"),
    db             : Session      = Depends(get_db),
) -> ApprovalsDashboardStats:
    return svc.get_dashboard_stats(
        employee_id    = employee_id,
        assigned_to_id = assigned_to_id,
        view_mode      = view_mode,
        db             = db,
    )


@router.post(
    "/delegations/",
    response_model=ApprovalDelegationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an approval delegation",
    description="Delegates approval authority from one manager to another for a date range.",
)
def create_delegation(
    payload : ApprovalDelegationCreate,
    db      : Session = Depends(get_db),
) -> ApprovalDelegationOut:
    delegation = svc.create_delegation(payload, db)
    return ApprovalDelegationOut.model_validate(delegation)


@router.get(
    "/delegations/",
    response_model=List[ApprovalDelegationOut],
    summary="List approval delegations",
)
def list_delegations(
    delegator_id : Optional[int]  = Query(default=None),
    delegate_id  : Optional[int]  = Query(default=None),
    active_only  : bool           = Query(default=True),
    db           : Session        = Depends(get_db),
) -> List[ApprovalDelegationOut]:
    records = svc.list_delegations(delegator_id, delegate_id, active_only, db)
    return [ApprovalDelegationOut.model_validate(r) for r in records]


@router.patch(
    "/delegations/{delegation_id}",
    response_model=ApprovalDelegationOut,
    summary="Update a delegation (extend validity, deactivate, etc.)",
)
def update_delegation(
    delegation_id : int,
    payload       : ApprovalDelegationUpdate,
    db            : Session = Depends(get_db),
) -> ApprovalDelegationOut:
    delegation = svc.update_delegation(delegation_id, payload, db)
    return ApprovalDelegationOut.model_validate(delegation)


@router.post(
    "/internal/refresh-sla",
    status_code=status.HTTP_200_OK,
    summary="[Internal] Refresh SLA status for all active requests",
    description=(
        "Intended to be called by a scheduler (e.g. Celery beat) every hour. "
        "Recomputes sla_status for all non-terminal records with a due date. "
        "This endpoint should be protected by an internal API key in production."
    ),
    include_in_schema=True,
)
def refresh_sla_bulk(db: Session = Depends(get_db)) -> dict:
    svc._bulk_refresh_sla(db)
    return {"detail": "SLA statuses refreshed"}


@router.post(
    "/internal/auto-escalate",
    status_code=status.HTTP_200_OK,
    summary="[Internal] Auto-escalate SLA-breached pending requests",
    description=(
        "Intended to be called by a scheduler. "
        "Escalates Pending requests whose SLA has been breached and that "
        "have not yet been manually escalated."
    ),
    include_in_schema=True,
)
def auto_escalate(db: Session = Depends(get_db)) -> dict:
    count = svc.trigger_auto_escalation(db)
    return {"detail": f"{count} request(s) auto-escalated due to SLA breach"}
