from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.database import get_db
from typing import Optional
from datetime import datetime

from model.Forms_Workflows.approval import ApprovalRequest
from schema.Forms_Workflows.approval import (
    ApprovalRequestCreate,
    ApprovalRequestUpdate,
    ApprovalRequestResponse,
    ApprovalActionSchema,
)

router = APIRouter(prefix="/approvals", tags=["Forms & Workflows"])


@router.post("/", response_model=ApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
def create_approval(payload: ApprovalRequestCreate, db: Session = Depends(get_db)):
    approval = ApprovalRequest(**payload.model_dump())
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


@router.get("/", response_model=list[ApprovalRequestResponse])
def list_approvals(
    status: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
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


# ── Static sub-paths before /{approval_id} ────────────────────────────────────

@router.get("/pending/{assigned_to}", response_model=list[ApprovalRequestResponse])
def pending_for_approver(assigned_to: str, db: Session = Depends(get_db)):
    return db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.assigned_to == assigned_to,
            ApprovalRequest.status == "Pending",
        )
    ).scalars().all()


@router.get("/{approval_id}", response_model=ApprovalRequestResponse)
def get_approval(approval_id: int, db: Session = Depends(get_db)):
    approval = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    ).scalars().first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


@router.patch("/{approval_id}/approve", response_model=ApprovalRequestResponse)
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

    approval.status = "Approved"
    approval.action_taken_at = datetime.utcnow()
    approval.action_by = payload.action_by
    if payload.comments:
        approval.comments = payload.comments
    db.commit()
    db.refresh(approval)
    return approval


@router.patch("/{approval_id}/reject", response_model=ApprovalRequestResponse)
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

    approval.status = "Rejected"
    approval.action_taken_at = datetime.utcnow()
    approval.action_by = payload.action_by
    if payload.comments:
        approval.comments = payload.comments
    db.commit()
    db.refresh(approval)
    return approval
