# routers/Forms_Workflows/request_management.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from model.Forms_Workflows.request import HRRequest, RequestTemplate
from schema.Forms_Workflows.request import (
    HRRequestCreate,
    HRRequestUpdate,
    HRRequestResponse,
    RequestActionSchema,
    RequestDashboardStats,
    RequestTemplateResponse,
)

router = APIRouter(prefix="/api/hr-requests", tags=["Request Management"])


# ══════════════════════════════════════════════════════════════════════════════
#  INTERNAL — Auto SLA breach check
# ══════════════════════════════════════════════════════════════════════════════

def _check_sla_breaches(db: Session):
    now = datetime.utcnow()
    breached = (
        db.query(HRRequest)
        .filter(
            HRRequest.sla_due_date < now,
            HRRequest.sla_breached == False,
            HRRequest.status.in_(["Open", "In Progress"]),
        )
        .all()
    )
    for r in breached:
        r.sla_breached = True
    if breached:
        db.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD STATS
#  Powers: Total Requests / In Progress / Approved / Completed stat cards
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/stats", response_model=RequestDashboardStats)
def get_dashboard_stats(
    employee_name: Optional[str] = Query(None),
    location:      Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(HRRequest)
    if employee_name:
        q = q.filter(HRRequest.employee_name == employee_name)
    if location:
        q = q.filter(HRRequest.location == location)
    all_records = q.all()
    return RequestDashboardStats(
        total_requests = len(all_records),
        in_progress    = sum(1 for r in all_records if r.status == "In Progress"),
        approved       = sum(1 for r in all_records if r.status == "Approved"),
        completed      = sum(1 for r in all_records if r.status == "Completed"),
        open           = sum(1 for r in all_records if r.status == "Open"),
        rejected       = sum(1 for r in all_records if r.status == "Rejected"),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATES — Category Cards & Quick Actions
#  Powers: Personal Info cards, Work-Related cards, Financial cards etc.
#          and Quick Actions section at bottom of page
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/templates/all", response_model=List[RequestTemplateResponse])
def list_templates(
    category:        Optional[str]  = Query(None),
    is_quick_action: Optional[bool] = Query(None),
    is_active:       Optional[bool] = Query(True),
    db: Session = Depends(get_db),
):
    q = db.query(RequestTemplate)
    if category:
        q = q.filter(RequestTemplate.category == category)
    if is_quick_action is not None:
        q = q.filter(RequestTemplate.is_quick_action == is_quick_action)
    if is_active is not None:
        q = q.filter(RequestTemplate.is_active == is_active)
    return q.all()


@router.get("/templates/quick-actions", response_model=List[RequestTemplateResponse])
def get_quick_actions(db: Session = Depends(get_db)):
    """Powers the Quick Actions (Auto-fill enabled) section at the bottom."""
    return (
        db.query(RequestTemplate)
        .filter(
            RequestTemplate.is_quick_action == True,
            RequestTemplate.is_active == True,
        )
        .all()
    )


@router.get("/templates/by-category/{category}", response_model=List[RequestTemplateResponse])
def get_templates_by_category(category: str, db: Session = Depends(get_db)):
    """
    Powers the category tab cards:
    Personal Information / Work-Related / Administrative /
    Financial / Travel & Expense / IT & Systems / Feedback
    """
    return (
        db.query(RequestTemplate)
        .filter(
            RequestTemplate.category == category,
            RequestTemplate.is_active == True,
        )
        .all()
    )


@router.post("/templates/create-request/{template_id}",
             response_model=HRRequestResponse, status_code=201)
def create_from_template(
    template_id:   int,
    employee_name: Optional[str] = Query(None),
    employee_id:   Optional[int] = Query(None),
    location:      Optional[str] = Query(None),
    submitted_by:  Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Create a pre-filled request from Quick Action / category card click."""
    template = db.query(RequestTemplate).filter(RequestTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    count = db.query(HRRequest).count()
    record = HRRequest(
        request_id       = f"REQ-{1001 + count}",
        title            = template.title,
        description      = template.description,
        request_type     = template.request_type,
        category         = template.category,
        priority         = template.priority,
        sla              = template.sla,
        workflow         = template.workflow,
        is_quick_action  = template.is_quick_action,
        auto_description = template.auto_description,
        employee_id      = employee_id,
        employee_name    = employee_name,
        location         = location,
        submitted_by     = submitted_by,
        form_data        = template.form_schema,
        status           = "Open",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  LIST REQUESTS
#  Powers: Request History table with all filters
#  Filters: Location / Workflows / Status / Filter Status / Date Range / Search
#  Category tabs: Personal Info / Work-Related / Administrative /
#                 Financial / Travel & Expense / IT & Systems / Feedback
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=List[HRRequestResponse])
def list_hr_requests(
    category:      Optional[str]     = Query(None),
    location:      Optional[str]     = Query(None),
    workflow:      Optional[str]     = Query(None),
    status:        Optional[str]     = Query(None),
    filter_status: Optional[str]     = Query(None),
    priority:      Optional[str]     = Query(None),
    date_from:     Optional[datetime] = Query(None),
    date_to:       Optional[datetime] = Query(None),
    search:        Optional[str]     = Query(None, description="Search by ID or type"),
    employee_name: Optional[str]     = Query(None),
    skip:  int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    _check_sla_breaches(db)
    q = db.query(HRRequest)
    if category:
        q = q.filter(HRRequest.category == category)
    if location:
        q = q.filter(HRRequest.location == location)
    if workflow:
        q = q.filter(HRRequest.workflow == workflow)
    if status:
        q = q.filter(HRRequest.status == status)
    if filter_status:
        q = q.filter(HRRequest.filter_status == filter_status)
    if priority:
        q = q.filter(HRRequest.priority == priority)
    if employee_name:
        q = q.filter(HRRequest.employee_name.ilike(f"%{employee_name}%"))
    if date_from:
        q = q.filter(HRRequest.submitted_date >= date_from)
    if date_to:
        q = q.filter(HRRequest.submitted_date <= date_to)
    if search:
        q = q.filter(
            HRRequest.request_id.ilike(f"%{search}%") |
            HRRequest.request_type.ilike(f"%{search}%") |
            HRRequest.title.ilike(f"%{search}%")
        )
    return q.order_by(HRRequest.created_at.desc()).offset(skip).limit(limit).all()


# ══════════════════════════════════════════════════════════════════════════════
#  GET SINGLE REQUEST
#  Powers: Click on REQ-1001 link in table
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/by-id/{id}", response_model=HRRequestResponse)
def get_by_numeric_id(id: int, db: Session = Depends(get_db)):
    record = db.query(HRRequest).filter(HRRequest.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    return record


@router.get("/{request_id}", response_model=HRRequestResponse)
def get_hr_request(request_id: str, db: Session = Depends(get_db)):
    record = db.query(HRRequest).filter(HRRequest.request_id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  CREATE — "New Request" button
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=HRRequestResponse, status_code=201)
def create_hr_request(payload: HRRequestCreate, db: Session = Depends(get_db)):
    count = db.query(HRRequest).count()
    data  = payload.model_dump()
    data["request_id"] = f"REQ-{1001 + count}"
    record = HRRequest(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  UPDATE
# ══════════════════════════════════════════════════════════════════════════════

@router.put("/{request_id}", response_model=HRRequestResponse)
def update_hr_request(
    request_id: str, payload: HRRequestUpdate, db: Session = Depends(get_db)
):
    record = db.query(HRRequest).filter(HRRequest.request_id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  ASSIGN → moves status to "In Progress"
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{request_id}/assign", response_model=HRRequestResponse)
def assign_request(
    request_id:  str,
    assigned_to: str = Query(...),
    db: Session = Depends(get_db),
):
    record = db.query(HRRequest).filter(HRRequest.request_id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    record.assigned_to   = assigned_to
    record.status        = "In Progress"
    record.filter_status = "In Progress"
    record.updated_at    = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  APPROVE — status = Approved (shown as green badge in table)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{request_id}/approve", response_model=HRRequestResponse)
def approve_request(
    request_id: str, payload: RequestActionSchema, db: Session = Depends(get_db)
):
    record = db.query(HRRequest).filter(HRRequest.request_id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    if record.status in ("Approved", "Completed", "Rejected", "Cancelled"):
        raise HTTPException(status_code=400, detail=f"Request is already '{record.status}'")
    record.status          = "Approved"
    record.filter_status   = "Approved"
    record.action_by       = payload.action_by
    record.comments        = payload.comments
    record.response        = payload.response
    record.action_taken_at = datetime.utcnow()
    record.updated_at      = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  REJECT — status = Rejected (shown as red badge in table)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{request_id}/reject", response_model=HRRequestResponse)
def reject_request(
    request_id: str, payload: RequestActionSchema, db: Session = Depends(get_db)
):
    record = db.query(HRRequest).filter(HRRequest.request_id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    if record.status in ("Approved", "Completed", "Rejected", "Cancelled"):
        raise HTTPException(status_code=400, detail=f"Request is already '{record.status}'")
    record.status          = "Rejected"
    record.filter_status   = "Rejected"
    record.action_by       = payload.action_by
    record.comments        = payload.comments
    record.action_taken_at = datetime.utcnow()
    record.updated_at      = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  COMPLETE — status = Completed (shown as green "Completed" badge)
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{request_id}/complete", response_model=HRRequestResponse)
def complete_request(
    request_id: str,
    response:   Optional[str] = Query(None),
    action_by:  Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    record = db.query(HRRequest).filter(HRRequest.request_id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    record.status          = "Completed"
    record.filter_status   = "Completed"
    record.response        = response
    record.action_by       = action_by
    record.action_taken_at = datetime.utcnow()
    record.updated_at      = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  CANCEL
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{request_id}/cancel", response_model=HRRequestResponse)
def cancel_request(request_id: str, db: Session = Depends(get_db)):
    record = db.query(HRRequest).filter(HRRequest.request_id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    if record.status in ("Completed", "Cancelled"):
        raise HTTPException(status_code=400, detail=f"Request is already '{record.status}'")
    record.status     = "Cancelled"
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ══════════════════════════════════════════════════════════════════════════════
#  DELETE
# ══════════════════════════════════════════════════════════════════════════════

@router.delete("/{request_id}", status_code=204)
def delete_hr_request(request_id: str, db: Session = Depends(get_db)):
    record = db.query(HRRequest).filter(HRRequest.request_id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    db.delete(record)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  LOCATIONS — for Location dropdown filter
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/meta/locations")
def get_locations(db: Session = Depends(get_db)):
    """Returns distinct locations for the Location filter dropdown."""
    results = db.query(HRRequest.location).distinct().filter(
        HRRequest.location != None
    ).all()
    return {"locations": [r[0] for r in results]}


# ══════════════════════════════════════════════════════════════════════════════
#  WORKFLOWS — for Workflows dropdown filter
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/meta/workflows")
def get_workflows(db: Session = Depends(get_db)):
    """Returns distinct workflows for the Workflows filter dropdown."""
    results = db.query(HRRequest.workflow).distinct().filter(
        HRRequest.workflow != None
    ).all()
    return {"workflows": [r[0] for r in results]}