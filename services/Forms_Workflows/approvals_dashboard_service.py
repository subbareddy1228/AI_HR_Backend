"""
services/Forms_Workflows/approvals_dashboard_service.py

Business-logic layer for the Approvals Dashboard.
All database interactions live here; the router stays thin.

Responsibilities:
  • Approval code generation       → APR-YYYY-NNNNNN
  • SLA due-date calculation       → based on sla_days_allowed
  • SLA status recomputation       → On Track / At Risk / SLA Breached
  • Status-transition guard        → only valid transitions allowed
  • History logging                → every status change is recorded
  • Dashboard stats aggregation    → 4-card totals + breakdowns
  • Delegation resolution          → find active delegate for a manager
  • Escalation auto-trigger        → called by a scheduler on SLA breach
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select, and_, or_
from sqlalchemy.orm import Session, selectinload

from model.Forms_Workflows.approval import (
    ApprovalDelegation,
    ApprovalHistory,
    ApprovalsDashboard,
    ApprovalDashboardComment,
    ApprovalSLAStatus,
    ApprovalStatus,
    ApprovalPriority,
)
from schema.Forms_Workflows.approval import (
    ApprovalCommentCreate,
    ApprovalsDashboardCreate,
    ApprovalsDashboardFilters,
    ApprovalsDashboardStats,
    ApprovalStatusCount,
    ApprovalsDashboardUpdate,
    ApprovePayload,
    EscalatePayload,
    OnHoldPayload,
    ReassignPayload,
    RejectPayload,
    WithdrawPayload,
    ApprovalDelegationCreate,
    ApprovalDelegationUpdate,
)




_SLA_AT_RISK_HOURS = 24

_VALID_TRANSITIONS: Dict[str, set] = {
    ApprovalStatus.PENDING   : {
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.ESCALATED,
        ApprovalStatus.ON_HOLD,
        ApprovalStatus.WITHDRAWN,
    },
    ApprovalStatus.ON_HOLD   : {
        ApprovalStatus.PENDING,
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.WITHDRAWN,
    },
    ApprovalStatus.ESCALATED : {
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.ON_HOLD,
        ApprovalStatus.WITHDRAWN,
    },
    ApprovalStatus.APPROVED  : set(),   # terminal
    ApprovalStatus.REJECTED  : set(),   # terminal
    ApprovalStatus.WITHDRAWN : set(),   # terminal
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _generate_approval_code(db: Session) -> str:
    year  = _utcnow().year
    count = db.execute(
        select(func.count()).select_from(ApprovalsDashboard)
    ).scalar_one()
    return f"APR-{year}-{count + 1:06d}"


def _compute_sla_due_date(submitted_at: datetime, sla_days: int) -> datetime:
   
    return submitted_at + timedelta(days=sla_days)


def _compute_sla_status(record: ApprovalsDashboard) -> str:
   
    if record.status in (
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.WITHDRAWN,
    ):
        return ApprovalSLAStatus.RESOLVED

    if not record.sla_due_date:
        return ApprovalSLAStatus.ON_TRACK

    now = _utcnow()
    if now > record.sla_due_date:
        return ApprovalSLAStatus.BREACHED
    if (record.sla_due_date - now).total_seconds() <= _SLA_AT_RISK_HOURS * 3600:
        return ApprovalSLAStatus.AT_RISK
    return ApprovalSLAStatus.ON_TRACK


def _days_overdue(record: ApprovalsDashboard) -> Optional[int]:
    
    if not record.sla_due_date:
        return None
    delta = _utcnow() - record.sla_due_date
    return delta.days


def _log_history(
    db        : Session,
    record    : ApprovalsDashboard,
    to_status : str,
    changed_by: Optional[str],
    note      : Optional[str] = None,
) -> None:
    db.add(
        ApprovalHistory(
            approval_id  =record.id,
            from_status  =record.status,
            to_status    =to_status,
            changed_by   =changed_by,
            note         =note,
        )
    )


def _guard_transition(record: ApprovalsDashboard, target: str) -> None:
    allowed = _VALID_TRANSITIONS.get(record.status, set())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot transition from '{record.status}' to '{target}'. "
                f"Allowed targets: {sorted(allowed) or 'none (terminal state)'}"
            ),
        )


def _eager_options():
    return [
        selectinload(ApprovalsDashboard.history),
        selectinload(ApprovalsDashboard.comments),
    ]


def _get_or_404(approval_id: int, db: Session) -> ApprovalsDashboard:
    record = db.execute(
        select(ApprovalsDashboard)
        .where(
            ApprovalsDashboard.id == approval_id,
            ApprovalsDashboard.is_deleted.is_(False),
        )
        .options(*_eager_options())
    ).scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return record


def _apply_filters(query, filters: ApprovalsDashboardFilters):
   

    if filters.status:
        query = query.where(ApprovalsDashboard.status == filters.status)

    if filters.reference_type:
        query = query.where(ApprovalsDashboard.reference_type == filters.reference_type)

    if filters.priority:
        query = query.where(ApprovalsDashboard.priority == filters.priority)

    if filters.employee_id:
        query = query.where(ApprovalsDashboard.employee_id == filters.employee_id)

    if filters.employee_name:
        query = query.where(
            ApprovalsDashboard.employee_name.ilike(f"%{filters.employee_name}%")
        )

    if filters.assigned_to_id:
        query = query.where(ApprovalsDashboard.assigned_to_id == filters.assigned_to_id)

    if filters.sla_status:
        query = query.where(ApprovalsDashboard.sla_status == filters.sla_status)

    if filters.date_from:
        query = query.where(ApprovalsDashboard.submitted_at >= filters.date_from)

    if filters.date_to:
        query = query.where(ApprovalsDashboard.submitted_at <= filters.date_to)

    if filters.search:
        term = f"%{filters.search}%"
        query = query.where(
            or_(
                ApprovalsDashboard.subject.ilike(term),
                ApprovalsDashboard.employee_name.ilike(term),
                ApprovalsDashboard.approval_code.ilike(term),
            )
        )

    return query


def create_approval(
    payload: ApprovalsDashboardCreate,
    db     : Session,
) -> ApprovalsDashboard:


    code = _generate_approval_code(db)

    sla_due = None
    if payload.sla_days_allowed and payload.sla_days_allowed > 0:
        sla_due = _compute_sla_due_date(_utcnow(), payload.sla_days_allowed)

    record = ApprovalsDashboard(
        approval_code     = code,
        sla_due_date      = sla_due,
        sla_status        = ApprovalSLAStatus.ON_TRACK,
        status            = ApprovalStatus.PENDING,
        **payload.model_dump(exclude_unset=True, exclude={"sla_days_allowed"}),
    )
    if payload.sla_days_allowed:
        record.sla_days_allowed = payload.sla_days_allowed

    db.add(record)
    db.flush()

 
    db.add(
        ApprovalHistory(
            approval_id  = record.id,
            from_status  = None,
            to_status    = ApprovalStatus.PENDING,
            changed_by   = payload.employee_name,
            note         = "Request submitted",
        )
    )

    db.commit()
    db.refresh(record)
    return record


def get_approval(approval_id: int, db: Session) -> ApprovalsDashboard:
    return _get_or_404(approval_id, db)


def list_approvals(
    filters : ApprovalsDashboardFilters,
    db      : Session,
) -> Tuple[int, List[ApprovalsDashboard]]:


    base_query = (
        select(ApprovalsDashboard)
        .where(ApprovalsDashboard.is_deleted.is_(False))
    )

    base_query = _apply_filters(base_query, filters)


    _bulk_refresh_sla(db)

    count_query = select(func.count()).select_from(
        base_query.subquery()
    )
    total = db.execute(count_query).scalar_one()

    paginated = (
        base_query
        .order_by(ApprovalsDashboard.submitted_at.desc())
        .offset((filters.page - 1) * filters.size)
        .limit(filters.size)
        .options(*_eager_options())
    )

    items = db.execute(paginated).scalars().all()
    return total, items


def update_approval(
    approval_id : int,
    payload     : ApprovalsDashboardUpdate,
    db          : Session,
) -> ApprovalsDashboard:
    

    record = _get_or_404(approval_id, db)

    if record.status not in (ApprovalStatus.PENDING, ApprovalStatus.ON_HOLD):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit a request in '{record.status}' state",
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(record, field, value)

    
    if "sla_days_allowed" in data and data["sla_days_allowed"]:
        record.sla_due_date = _compute_sla_due_date(
            record.submitted_at, data["sla_days_allowed"]
        )

    record.sla_status = _compute_sla_status(record)
    record.updated_at = _utcnow()

    db.commit()
    db.refresh(record)
    return record


def approve_request(
    approval_id : int,
    payload     : ApprovePayload,
    db          : Session,
) -> ApprovalsDashboard:
    record = _get_or_404(approval_id, db)
    _guard_transition(record, ApprovalStatus.APPROVED)

    _log_history(db, record, ApprovalStatus.APPROVED, payload.actioned_by, payload.comments)

    record.status          = ApprovalStatus.APPROVED
    record.actioned_by     = payload.actioned_by
    record.actioned_by_id  = payload.actioned_by_id
    record.action_comments = payload.comments
    record.actioned_at     = _utcnow()
    record.sla_status      = _compute_sla_status(record)
    record.updated_at      = _utcnow()

    db.commit()
    db.refresh(record)
    return record


def reject_request(
    approval_id : int,
    payload     : RejectPayload,
    db          : Session,
) -> ApprovalsDashboard:
    record = _get_or_404(approval_id, db)
    _guard_transition(record, ApprovalStatus.REJECTED)

    _log_history(db, record, ApprovalStatus.REJECTED, payload.actioned_by, payload.comments)

    record.status          = ApprovalStatus.REJECTED
    record.actioned_by     = payload.actioned_by
    record.actioned_by_id  = payload.actioned_by_id
    record.action_comments = payload.comments
    record.actioned_at     = _utcnow()
    record.sla_status      = _compute_sla_status(record)
    record.updated_at      = _utcnow()

    db.commit()
    db.refresh(record)
    return record


def escalate_request(
    approval_id : int,
    payload     : EscalatePayload,
    db          : Session,
) -> ApprovalsDashboard:
    record = _get_or_404(approval_id, db)
    _guard_transition(record, ApprovalStatus.ESCALATED)

    note = f"Escalated to {payload.escalated_to}. Reason: {payload.reason}"
    _log_history(db, record, ApprovalStatus.ESCALATED, payload.actioned_by, note)

    record.status             = ApprovalStatus.ESCALATED
    record.is_escalated       = True
    record.escalated_to       = payload.escalated_to
    record.escalated_to_id    = payload.escalated_to_id
    record.escalated_at       = _utcnow()
    record.escalation_reason  = payload.reason
    record.auto_escalated     = False
    record.assigned_to        = payload.escalated_to
    record.assigned_to_id     = payload.escalated_to_id
    record.assigned_at        = _utcnow()
    record.updated_at         = _utcnow()

    db.commit()
    db.refresh(record)
    return record


def reassign_request(
    approval_id : int,
    payload     : ReassignPayload,
    db          : Session,
) -> ApprovalsDashboard:
    record = _get_or_404(approval_id, db)

    if record.status not in (ApprovalStatus.PENDING, ApprovalStatus.ESCALATED, ApprovalStatus.ON_HOLD):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reassign a request in '{record.status}' state",
        )

    note = (
        f"Reassigned from '{record.assigned_to}' to '{payload.new_assignee_name}'. "
        f"By: {payload.actioned_by}. "
        + (f"Reason: {payload.reason}" if payload.reason else "")
    )
    _log_history(db, record, record.status, payload.actioned_by, note)

    record.assigned_to    = payload.new_assignee_name
    record.assigned_to_id = payload.new_assignee_id
    record.assigned_at    = _utcnow()
    record.updated_at     = _utcnow()

    db.commit()
    db.refresh(record)
    return record


def withdraw_request(
    approval_id : int,
    payload     : WithdrawPayload,
    db          : Session,
) -> ApprovalsDashboard:
    record = _get_or_404(approval_id, db)
    _guard_transition(record, ApprovalStatus.WITHDRAWN)

    _log_history(db, record, ApprovalStatus.WITHDRAWN, payload.withdrawn_by, payload.reason)

    record.status     = ApprovalStatus.WITHDRAWN
    record.updated_at = _utcnow()

    db.commit()
    db.refresh(record)
    return record


def put_on_hold(
    approval_id : int,
    payload     : OnHoldPayload,
    db          : Session,
) -> ApprovalsDashboard:
    record = _get_or_404(approval_id, db)
    _guard_transition(record, ApprovalStatus.ON_HOLD)

    _log_history(db, record, ApprovalStatus.ON_HOLD, payload.actioned_by, payload.reason)

    record.status     = ApprovalStatus.ON_HOLD
    record.updated_at = _utcnow()

    db.commit()
    db.refresh(record)
    return record


def soft_delete(
    approval_id : int,
    deleted_by  : str,
    db          : Session,
) -> None:
    record = _get_or_404(approval_id, db)

    if record.status == ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a pending approval; withdraw it first",
        )

    record.is_deleted  = True
    record.deleted_at  = _utcnow()
    record.deleted_by  = deleted_by
    record.updated_at  = _utcnow()

    db.commit()



def add_comment(
    approval_id : int,
    payload     : ApprovalCommentCreate,
    db          : Session,
) -> ApprovalDashboardComment:
    _get_or_404(approval_id, db)   # existence check

    comment = ApprovalDashboardComment(
        approval_id  = approval_id,
        body         = payload.body,
        is_internal  = payload.is_internal,
        author_name  = payload.author_name,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(comment_id: int, db: Session) -> None:
    comment = db.get(ApprovalDashboardComment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    db.delete(comment)
    db.commit()


def get_dashboard_stats(
    employee_id    : Optional[int],
    assigned_to_id : Optional[int],
    view_mode      : str,
    db             : Session,
) -> ApprovalsDashboardStats:


    base = select(ApprovalsDashboard).where(
        ApprovalsDashboard.is_deleted.is_(False)
    )

    if view_mode == "Employee" and employee_id:
        base = base.where(ApprovalsDashboard.employee_id == employee_id)
    elif view_mode == "Manager" and assigned_to_id:
        base = base.where(ApprovalsDashboard.assigned_to_id == assigned_to_id)

    rows = db.execute(base).scalars().all()

    counts: Dict[str, int] = {}
    sla_counts: Dict[str, int] = {"On Track": 0, "At Risk": 0, "SLA Breached": 0}
    ref_type_counts: Dict[str, int] = {}
    last_approved_at: Optional[datetime] = None

    for r in rows:
        counts[r.status] = counts.get(r.status, 0) + 1

    
        sla_key = r.sla_status
        if sla_key in sla_counts:
            sla_counts[sla_key] += 1

 
        ref_type_counts[r.reference_type] = ref_type_counts.get(r.reference_type, 0) + 1

    
        if r.status == ApprovalStatus.APPROVED and r.actioned_at:
            if last_approved_at is None or r.actioned_at > last_approved_at:
                last_approved_at = r.actioned_at

    total          = len(rows)
    total_rejected = counts.get(ApprovalStatus.REJECTED, 0)
    rejection_rate = round(total_rejected / total * 100, 1) if total else None

    by_status = [
        ApprovalStatusCount(status=k, count=v) for k, v in counts.items()
    ]
    by_ref_type = [
        ApprovalStatusCount(status=k, count=v) for k, v in ref_type_counts.items()
    ]

    return ApprovalsDashboardStats(
        total_requests     = total,
        total_pending      = counts.get(ApprovalStatus.PENDING,   0),
        total_approved     = counts.get(ApprovalStatus.APPROVED,  0),
        total_rejected     = total_rejected,
        total_escalated    = counts.get(ApprovalStatus.ESCALATED, 0),
        total_on_hold      = counts.get(ApprovalStatus.ON_HOLD,   0),
        total_withdrawn    = counts.get(ApprovalStatus.WITHDRAWN, 0),
        last_approved_at   = last_approved_at,
        rejection_rate_pct = rejection_rate,
        sla_on_track       = sla_counts["On Track"],
        sla_at_risk        = sla_counts["At Risk"],
        sla_breached       = sla_counts["SLA Breached"],
        by_status          = by_status,
        by_reference_type  = by_ref_type,
    )


def _bulk_refresh_sla(db: Session) -> None:

    records = db.execute(
        select(ApprovalsDashboard).where(
            ApprovalsDashboard.is_deleted.is_(False),
            ApprovalsDashboard.sla_due_date.isnot(None),
            ApprovalsDashboard.status.notin_(
                [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.WITHDRAWN]
            ),
        )
    ).scalars().all()

    for r in records:
        new_sla = _compute_sla_status(r)
        if new_sla != r.sla_status:
            r.sla_status  = new_sla
            r.updated_at  = _utcnow()

    if records:
        db.commit()


def trigger_auto_escalation(db: Session) -> int:

    records = db.execute(
        select(ApprovalsDashboard).where(
            ApprovalsDashboard.is_deleted.is_(False),
            ApprovalsDashboard.status == ApprovalStatus.PENDING,
            ApprovalsDashboard.sla_status == ApprovalSLAStatus.BREACHED,
            ApprovalsDashboard.is_escalated.is_(False),
            ApprovalsDashboard.sla_due_date.isnot(None),
        )
    ).scalars().all()

    count = 0
    for r in records:
        _log_history(
            db, r, ApprovalStatus.ESCALATED, "System",
            "Auto-escalated due to SLA breach",
        )
        r.status          = ApprovalStatus.ESCALATED
        r.is_escalated    = True
        r.auto_escalated  = True
        r.escalated_at    = _utcnow()
        r.escalation_reason = "SLA breach – auto-escalated by system"
        r.updated_at      = _utcnow()
        count += 1

    if count:
        db.commit()

    return count


def create_delegation(
    payload : ApprovalDelegationCreate,
    db      : Session,
) -> ApprovalDelegation:
    delegation = ApprovalDelegation(**payload.model_dump())
    db.add(delegation)
    db.commit()
    db.refresh(delegation)
    return delegation


def update_delegation(
    delegation_id : int,
    payload       : ApprovalDelegationUpdate,
    db            : Session,
) -> ApprovalDelegation:
    delegation = db.get(ApprovalDelegation, delegation_id)
    if not delegation:
        raise HTTPException(status_code=404, detail="Delegation not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(delegation, field, value)

    delegation.updated_at = _utcnow()
    db.commit()
    db.refresh(delegation)
    return delegation


def list_delegations(
    delegator_id : Optional[int],
    delegate_id  : Optional[int],
    active_only  : bool,
    db           : Session,
) -> List[ApprovalDelegation]:
    query = select(ApprovalDelegation)
    if delegator_id:
        query = query.where(ApprovalDelegation.delegator_id == delegator_id)
    if delegate_id:
        query = query.where(ApprovalDelegation.delegate_id == delegate_id)
    if active_only:
        now = _utcnow()
        query = query.where(
            ApprovalDelegation.is_active.is_(True),
            ApprovalDelegation.valid_from  <= now,
            ApprovalDelegation.valid_until >= now,
        )
    return db.execute(query).scalars().all()


def resolve_effective_approver(
    intended_approver_id : int,
    db                   : Session,
) -> Optional[int]:

    now = _utcnow()
    delegation = db.execute(
        select(ApprovalDelegation).where(
            ApprovalDelegation.delegator_id == intended_approver_id,
            ApprovalDelegation.is_active.is_(True),
            ApprovalDelegation.valid_from  <= now,
            ApprovalDelegation.valid_until >= now,
        ).limit(1)
    ).scalars().first()

    return delegation.delegate_id if delegation else intended_approver_id
