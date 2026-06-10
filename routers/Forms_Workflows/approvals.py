from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date

from core.database import get_db
from model.Forms_Workflows.approval import ApprovalRequest
from schema.Forms_Workflows.approval import (
    ApprovalRequestCreate,
    ApprovalRequestUpdate,
    ApprovalRequestResponse,
    ApprovalActionSchema,
    ApprovalDashboardStats,
)

router = APIRouter(prefix="/api/approvals", tags=["Approvals Dashboard"])


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD STATS
#  GET /api/approvals/dashboard/stats
#  Powers the 4 stat cards: Total, Pending, Approved, Rejected
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/stats", response_model=ApprovalDashboardStats)
def get_dashboard_stats(
    employee_name: Optional[str] = Query(None, description="Filter by employee (Employee View)"),
    assigned_to: Optional[str] = Query(None, description="Filter by manager (Manager View)"),
    db: Session = Depends(get_db),
):
    q = db.query(ApprovalRequest)
    if employee_name:
        q = q.filter(ApprovalRequest.employee_name == employee_name)
    if assigned_to:
        q = q.filter(ApprovalRequest.assigned_to == assigned_to)

    all_records = q.all()
    total       = len(all_records)
    pending     = sum(1 for r in all_records if r.status == "Pending")
    approved    = sum(1 for r in all_records if r.status == "Approved")
    rejected    = sum(1 for r in all_records if r.status == "Rejected")

    last_approved = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.status == "Approved")
        .order_by(ApprovalRequest.action_taken_at.desc())
        .first()
    )

    rejection_rate = round((rejected / total) * 100, 1) if total > 0 else 0.0

    return ApprovalDashboardStats(
        total_requests=total,
        pending=pending,
        approved=approved,
        rejected=rejected,
        last_approved_date=last_approved.action_taken_at if last_approved else None,
        rejection_rate=rejection_rate,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  LIST REQUESTS (with filters)
#  GET /api/approvals/
#  Supports: status, type, priority, date range, search, employee/manager view
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=List[ApprovalRequestResponse])
def list_approval_requests(
    # View mode
    employee_name: Optional[str] = Query(None, description="Employee View — filter by employee"),
    assigned_to: Optional[str]   = Query(None, description="Manager View — filter by assignee"),

    # Filters visible in UI
    status:         Optional[str]  = Query(None, description="All Status / Pending / Approved / Rejected / Cancelled"),
    reference_type: Optional[str]  = Query(None, description="All Types / leave / expense / transfer / promotion / exit"),
    priority:       Optional[str]  = Query(None, description="All Priorities / Low / Medium / High / Critical"),
    date_from:      Optional[date] = Query(None, description="Date range from"),
    date_to:        Optional[date] = Query(None, description="Date range to"),
    search:         Optional[str]  = Query(None, description="Search by title or description"),

    skip:  int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    # Auto-check SLA breach before returning
    _check_sla_breaches(db)

    q = db.query(ApprovalRequest)

    if employee_name:
        q = q.filter(ApprovalRequest.employee_name == employee_name)
    if assigned_to:
        q = q.filter(ApprovalRequest.assigned_to == assigned_to)
    if status:
        q = q.filter(ApprovalRequest.status == status)
    if reference_type:
        q = q.filter(ApprovalRequest.reference_type == reference_type)
    if priority:
        q = q.filter(ApprovalRequest.priority == priority)
    if date_from:
        q = q.filter(ApprovalRequest.start_date >= date_from)
    if date_to:
        q = q.filter(ApprovalRequest.end_date <= date_to)
    if search:
        q = q.filter(
            ApprovalRequest.title.ilike(f"%{search}%") |
            ApprovalRequest.description.ilike(f"%{search}%")
        )

    return q.order_by(ApprovalRequest.created_at.desc()).offset(skip).limit(limit).all()


# ══════════════════════════════════════════════════════════════════════════════
#  GET SINGLE REQUEST
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{approval_id}", response_model=ApprovalRequestResponse)
def get_approval_request(approval_id: int, db: Session = Depends(get_db)):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  CREATE NEW REQUEST
#  POST /api/approvals/
#  Triggered by "New Request" button in UI
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=ApprovalRequestResponse, status_code=201)
def create_approval_request(payload: ApprovalRequestCreate, db: Session = Depends(get_db)):
    record = ApprovalRequest(**payload.model_dump())

    # Auto-set SLA breach flag
    if record.sla_due_date and datetime.utcnow() > record.sla_due_date:
        record.sla_breached = True

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  UPDATE REQUEST
# ══════════════════════════════════════════════════════════════════════════════

@router.put("/{approval_id}", response_model=ApprovalRequestResponse)
def update_approval_request(
    approval_id: int, payload: ApprovalRequestUpdate, db: Session = Depends(get_db)
):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  APPROVE
#  POST /api/approvals/{id}/approve
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{approval_id}/approve", response_model=ApprovalRequestResponse)
def approve_request(
    approval_id: int, payload: ApprovalActionSchema, db: Session = Depends(get_db)
):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if record.status != "Pending":
        raise HTTPException(status_code=400, detail=f"Cannot approve — request is already '{record.status}'")
    record.status         = "Approved"
    record.action_by      = payload.action_by
    record.comments       = payload.comments
    record.action_taken_at = datetime.utcnow()
    record.updated_at     = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  REJECT
#  POST /api/approvals/{id}/reject
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{approval_id}/reject", response_model=ApprovalRequestResponse)
def reject_request(
    approval_id: int, payload: ApprovalActionSchema, db: Session = Depends(get_db)
):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if record.status != "Pending":
        raise HTTPException(status_code=400, detail=f"Cannot reject — request is already '{record.status}'")
    record.status          = "Rejected"
    record.action_by       = payload.action_by
    record.comments        = payload.comments
    record.action_taken_at = datetime.utcnow()
    record.updated_at      = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  CANCEL (the X button in Actions column)
#  POST /api/approvals/{id}/cancel
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{approval_id}/cancel", response_model=ApprovalRequestResponse)
def cancel_request(approval_id: int, db: Session = Depends(get_db)):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if record.status in ("Approved", "Rejected", "Cancelled"):
        raise HTTPException(status_code=400, detail=f"Request is already '{record.status}'")
    record.status     = "Cancelled"
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  ESCALATE
#  POST /api/approvals/{id}/escalate
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{approval_id}/escalate", response_model=ApprovalRequestResponse)
def escalate_request(
    approval_id: int,
    escalate_to: str = Query(..., description="Username to escalate to"),
    db: Session = Depends(get_db),
):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    record.status      = "Escalated"
    record.assigned_to = escalate_to
    record.updated_at  = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  DELETE
# ══════════════════════════════════════════════════════════════════════════════

@router.delete("/{approval_id}", status_code=204)
def delete_approval_request(approval_id: int, db: Session = Depends(get_db)):
    record = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")
    db.delete(record)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  INTERNAL — auto-mark SLA breached
# ══════════════════════════════════════════════════════════════════════════════

def _check_sla_breaches(db: Session):
    now = datetime.utcnow()
    breached = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.sla_due_date < now,
            ApprovalRequest.sla_breached == False,
            ApprovalRequest.status == "Pending",
        )
        .all()
    )
    for r in breached:
        r.sla_breached = True
    if breached:
        db.commit()