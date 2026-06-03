from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from model.Forms_Workflows.approval import ApprovalRequest
from schema.Forms_Workflows.approval import (
    ApprovalRequestCreate,
    ApprovalRequestUpdate,
    ApprovalRequestResponse,
    ApprovalActionSchema,
)

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])


# ── Create ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ApprovalRequestResponse, status_code=201)
def create_approval_request(payload: ApprovalRequestCreate, db: Session = Depends(get_db)):
    record = ApprovalRequest(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── List / Filter ──────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ApprovalRequestResponse])
def list_approval_requests(
    status: Optional[str] = Query(None, description="Pending/Approved/Rejected/Escalated"),
    reference_type: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(ApprovalRequest)
    if status:
        q = q.filter(ApprovalRequest.status == status)
    if reference_type:
        q = q.filter(ApprovalRequest.reference_type == reference_type)
    if assigned_to:
        q = q.filter(ApprovalRequest.assigned_to == assigned_to)
    return q.order_by(ApprovalRequest.created_at.desc()).offset(skip).limit(limit).all()


# ── Get by ID ─────────────────────────────────────────────────────────────────

@router.get("/{approval_id}", response_model=ApprovalRequestResponse)
def get_approval_request(approval_id: int, db: Session = Depends(get_db)):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return record


# ── Update ────────────────────────────────────────────────────────────────────

@router.put("/{approval_id}", response_model=ApprovalRequestResponse)
def update_approval_request(
    approval_id: int, payload: ApprovalRequestUpdate, db: Session = Depends(get_db)
):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


# ── Approve ───────────────────────────────────────────────────────────────────

@router.post("/{approval_id}/approve", response_model=ApprovalRequestResponse)
def approve_request(
    approval_id: int, payload: ApprovalActionSchema, db: Session = Depends(get_db)
):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if record.status != "Pending":
        raise HTTPException(status_code=400, detail=f"Request is already '{record.status}'")
    record.status = "Approved"
    record.action_by = payload.action_by
    record.comments = payload.comments
    record.action_taken_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ── Reject ────────────────────────────────────────────────────────────────────

@router.post("/{approval_id}/reject", response_model=ApprovalRequestResponse)
def reject_request(
    approval_id: int, payload: ApprovalActionSchema, db: Session = Depends(get_db)
):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if record.status != "Pending":
        raise HTTPException(status_code=400, detail=f"Request is already '{record.status}'")
    record.status = "Rejected"
    record.action_by = payload.action_by
    record.comments = payload.comments
    record.action_taken_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ── Escalate ──────────────────────────────────────────────────────────────────

@router.post("/{approval_id}/escalate", response_model=ApprovalRequestResponse)
def escalate_request(
    approval_id: int,
    escalate_to: str = Query(..., description="Username to escalate to"),
    db: Session = Depends(get_db),
):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    record.status = "Escalated"
    record.assigned_to = escalate_to
    db.commit()
    db.refresh(record)
    return record


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{approval_id}", status_code=204)
def delete_approval_request(approval_id: int, db: Session = Depends(get_db)):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    db.delete(record)
    db.commit()

