from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.database import get_db
from typing import Optional, List
from datetime import datetime

from model.Forms_Workflows.approval import ApprovalRequest
from schema.Forms_Workflows.approval import (
    ApprovalRequestCreate,
    ApprovalRequestUpdate,
    ApprovalRequestResponse,
    ApprovalActionSchema,
    ApprovalDashboardSummary,
)

router = APIRouter(
    prefix="/approvals",
    tags=["Forms & Workflows"],
)


# ─────────────────────────────────────────────────────────────────────────────
# POST /approvals/
# Raise a new approval request → always starts as Pending
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_approval(
    payload: ApprovalRequestCreate,
    db: Session = Depends(get_db),
):
    approval = ApprovalRequest(**payload.model_dump())
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


# ─────────────────────────────────────────────────────────────────────────────
# GET /approvals/
# List approval requests with optional filters
# (Status | Type | Employee filters used in the dashboard filter bar)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[ApprovalRequestResponse],
)
def list_approvals(
    status:         Optional[str] = Query(None),
    assigned_to:    Optional[str] = Query(None),
    reference_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(ApprovalRequest)
    if status:
        query = query.where(ApprovalRequest.status == status)
    if assigned_to:
        query = query.where(ApprovalRequest.assigned_to == assigned_to)
    if reference_type:
        query = query.where(ApprovalRequest.reference_type == reference_type)
    return db.execute(query).scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# GET /approvals/summary
# Stat-card counts for the Approvals Dashboard header:
#   Total Requests | Pending | Approved | Rejected
#
# Pass assigned_to for Manager View, employee_id for Employee View
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=ApprovalDashboardSummary,
)
def approval_summary(
    assigned_to: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(ApprovalRequest)
    if assigned_to:
        query = query.where(ApprovalRequest.assigned_to == assigned_to)
    if employee_id:
        query = query.where(ApprovalRequest.employee_id == employee_id)

    records = db.execute(query).scalars().all()

    total    = len(records)
    pending  = sum(1 for r in records if r.status == "Pending")
    approved = sum(1 for r in records if r.status == "Approved")
    rejected = sum(1 for r in records if r.status == "Rejected")

    return ApprovalDashboardSummary(
        total_requests=total,
        pending=pending,
        approved=approved,
        rejected=rejected,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /approvals/pending/{assigned_to}
# Manager View queue: all Pending requests assigned to one approver
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/pending/{assigned_to}",
    response_model=List[ApprovalRequestResponse],
)
def pending_for_approver(
    assigned_to: str,
    db: Session = Depends(get_db),
):
    return db.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.assigned_to == assigned_to,
            ApprovalRequest.status == "Pending",
        )
    ).scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# GET /approvals/{approval_id}
# Fetch a single approval request by ID
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{approval_id}",
    response_model=ApprovalRequestResponse,
)
def get_approval(
    approval_id: int,
    db: Session = Depends(get_db),
):
    approval = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    ).scalars().first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /approvals/{approval_id}/approve
# Manager clicks the ✓ (approve) action button
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/{approval_id}/approve",
    response_model=ApprovalRequestResponse,
)
def approve_request(
    approval_id: int,
    payload: ApprovalActionSchema,
    db: Session = Depends(get_db),
):
    approval = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    ).scalars().first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != "Pending":
        raise HTTPException(status_code=400, detail=f"Request is already {approval.status}")

    approval.status          = "Approved"
    approval.action_taken_at = datetime.utcnow()
    approval.action_by       = payload.action_by
    approval.comments        = payload.comments
    db.commit()
    db.refresh(approval)
    return approval


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /approvals/{approval_id}/reject
# Manager clicks the ✗ (reject) action button
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/{approval_id}/reject",
    response_model=ApprovalRequestResponse,
)
def reject_request(
    approval_id: int,
    payload: ApprovalActionSchema,
    db: Session = Depends(get_db),
):
    approval = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    ).scalars().first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != "Pending":
        raise HTTPException(status_code=400, detail=f"Request is already {approval.status}")

    approval.status          = "Rejected"
    approval.action_taken_at = datetime.utcnow()
    approval.action_by       = payload.action_by
    approval.comments        = payload.comments
    db.commit()
    db.refresh(approval)
    return approval