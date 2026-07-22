
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from core.database import get_db

from model.Forms_Workflows.request import (
    RequestAttachment,
    RequestComment,
    RequestManagement,
    RequestStatusLog,
    RequestTypeConfig,
    RequestCategory,
    RequestStatus,
    SLA_DAYS,
    default_priority,
    RequestPersonalInfoDetail,
    RequestWorkRelatedDetail,
    RequestAdminDetail,
    RequestFinancialDetail,
    RequestTravelExpenseDetail,
    RequestITSystemsDetail,
    RequestFeedbackDetail,
)
from schema.Forms_Workflows.request import (
    AssignPayload,
    CommentCreate,
    CommentOut,
    AttachmentOut,
    RequestDashboardStats,
    RequestCategoryCount,
    RequestStatusCount,
    RequestManagementCreate,
    RequestManagementListOut,
    RequestManagementOut,
    RequestManagementUpdate,
    RequestTypeConfigCreate,
    RequestTypeConfigOut,
    RequestTypeConfigUpdate,
    ResolvePayload,
    StatusTransitionPayload,
)

router = APIRouter(prefix="/requests", tags=["Request Management"])


def _generate_request_id(db: Session) -> str:
  
    year = datetime.utcnow().year
    count = db.execute(
        select(func.count()).select_from(RequestManagement)
    ).scalar_one()
    return f"REQ-{year}-{count + 1:06d}"


def _eager_load(query):

    return query.options(
        selectinload(RequestManagement.personal_info_detail),
        selectinload(RequestManagement.work_related_detail),
        selectinload(RequestManagement.admin_detail),
        selectinload(RequestManagement.financial_detail),
        selectinload(RequestManagement.travel_expense_detail),
        selectinload(RequestManagement.it_systems_detail),
        selectinload(RequestManagement.feedback_detail),
        selectinload(RequestManagement.comments),
        selectinload(RequestManagement.attachments),
        selectinload(RequestManagement.status_logs),
    )


def _get_or_404(request_id: int, db: Session) -> RequestManagement:
    req = db.execute(
        _eager_load(
            select(RequestManagement).where(
                RequestManagement.id == request_id,
                RequestManagement.is_deleted.is_(False),
            )
        )
    ).scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


_DETAIL_MAP = {
    RequestCategory.PERSONAL_INFORMATION: (
        "personal_info_detail", RequestPersonalInfoDetail, "personal_info_detail"
    ),
    RequestCategory.WORK_RELATED: (
        "work_related_detail", RequestWorkRelatedDetail, "work_related_detail"
    ),
    RequestCategory.ADMINISTRATIVE: (
        "admin_detail", RequestAdminDetail, "admin_detail"
    ),
    RequestCategory.FINANCIAL: (
        "financial_detail", RequestFinancialDetail, "financial_detail"
    ),
    RequestCategory.TRAVEL_EXPENSE: (
        "travel_expense_detail", RequestTravelExpenseDetail, "travel_expense_detail"
    ),
    RequestCategory.IT_SYSTEMS: (
        "it_systems_detail", RequestITSystemsDetail, "it_systems_detail"
    ),
    RequestCategory.FEEDBACK: (
        "feedback_detail", RequestFeedbackDetail, "feedback_detail"
    ),
}


def _attach_detail(req: RequestManagement, payload: RequestManagementCreate, db: Session) -> None:
    
    entry = _DETAIL_MAP.get(payload.category)
    if entry is None:
        return
    payload_attr, model_class, _ = entry
    detail_data = getattr(payload, payload_attr, None)
    if detail_data is None:
     
        detail_obj = model_class(request_id=req.id)
    else:
        detail_obj = model_class(request_id=req.id, **detail_data.model_dump(exclude_unset=True))
    db.add(detail_obj)


def _log_status(
    req: RequestManagement,
    to_status: str,
    from_status: Optional[str],
    changed_by: Optional[str],
    note: Optional[str],
    db: Session,
) -> None:
    log = RequestStatusLog(
        request_id=req.id,
        from_status=from_status,
        to_status=to_status,
        changed_by=changed_by,
        note=note,
    )
    db.add(log)


def _transition_status(
    req: RequestManagement,
    new_status: str,
    changed_by: Optional[str],
    note: Optional[str],
    db: Session,
) -> None:
    old = req.status
    req.status = new_status
    req.updated_at = datetime.utcnow()
    _log_status(req, new_status, old, changed_by, note, db)


@router.get("/dashboard/stats", response_model=RequestDashboardStats, summary="Get dashboard statistics")
def get_dashboard_stats(
    location:    Optional[str] = Query(None),
    department:  Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
   
    base = select(RequestManagement).where(RequestManagement.is_deleted.is_(False))
    if location:
        base = base.where(RequestManagement.location == location)
    if department:
        base = base.where(RequestManagement.department == department)
    if employee_id:
        base = base.where(RequestManagement.employee_id == employee_id)

    rows: List[RequestManagement] = db.execute(base).scalars().all()

    counts: dict[str, int] = {}
    cat_counts: dict[str, int] = {}
    for r in rows:
        counts[r.status] = counts.get(r.status, 0) + 1
        cat_counts[r.category] = cat_counts.get(r.category, 0) + 1

    return RequestDashboardStats(
        total=len(rows),
        in_progress=counts.get(RequestStatus.IN_PROGRESS, 0),
        approved=counts.get(RequestStatus.APPROVED, 0),
        completed=counts.get(RequestStatus.COMPLETED, 0),
        pending=counts.get(RequestStatus.PENDING, 0),
        rejected=counts.get(RequestStatus.REJECTED, 0),
        by_category=[RequestCategoryCount(category=k, count=v) for k, v in cat_counts.items()],
        by_status=[RequestStatusCount(status=k, count=v) for k, v in counts.items()],
    )


@router.get(
    "/types",
    response_model=List[RequestTypeConfigOut],
    summary="List all active request types grouped by category",
)
def list_request_types(
    category: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    q = select(RequestTypeConfig)
    if category:
        q = q.where(RequestTypeConfig.category == category)
    if active_only:
        q = q.where(RequestTypeConfig.is_active.is_(True))
    return db.execute(q).scalars().all()


@router.post(
    "/types",
    response_model=RequestTypeConfigOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create / register a new request type",
)
def create_request_type(payload: RequestTypeConfigCreate, db: Session = Depends(get_db)):
    obj = RequestTypeConfig(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch(
    "/types/{config_id}",
    response_model=RequestTypeConfigOut,
    summary="Update request type config (SLA, priority, workflow, etc.)",
)
def update_request_type(
    config_id: int,
    payload: RequestTypeConfigUpdate,
    db: Session = Depends(get_db),
):
    obj = db.get(RequestTypeConfig, config_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Request type config not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


@router.post(
    "/",
    response_model=RequestManagementOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new request",
)
def create_request(payload: RequestManagementCreate, db: Session = Depends(get_db)):

    priority = payload.priority or default_priority(payload.request_type)
    sla      = SLA_DAYS.get(payload.request_type)

    req = RequestManagement(
        request_id  = _generate_request_id(db),
        category    = payload.category,
        request_type= payload.request_type,
        subject     = payload.subject,
        description = payload.description,
        employee_id = payload.employee_id,
        employee_name = payload.employee_name,
        employee_email= payload.employee_email,
        department  = payload.department,
        location    = payload.location,
        workflow    = payload.workflow,
        priority    = priority,
        sla_days    = sla,
        status      = RequestStatus.OPEN,
    )
    db.add(req)
    db.flush()  

    _attach_detail(req, payload, db)

   
    _log_status(req, RequestStatus.OPEN, None, payload.employee_name or "System", "Request submitted", db)

    db.commit()
    db.refresh(req)
    return _get_or_404(req.id, db)


@router.get(
    "/",
    response_model=List[RequestManagementListOut],
    summary="List requests with filters",
)
def list_requests(
    category:    Optional[str] = Query(None, description="Filter by RequestCategory"),
    request_type:Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority:    Optional[str] = Query(None),
    location:    Optional[str] = Query(None),
    department:  Optional[str] = Query(None),
    workflow:    Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    search:      Optional[str] = Query(None, description="Search by request_id or subject"),
    date_from:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to:     Optional[str] = Query(None, description="YYYY-MM-DD"),
    skip: int  = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = select(RequestManagement).where(RequestManagement.is_deleted.is_(False))

    if category:
        q = q.where(RequestManagement.category == category)
    if request_type:
        q = q.where(RequestManagement.request_type == request_type)
    if status_filter:
        q = q.where(RequestManagement.status == status_filter)
    if priority:
        q = q.where(RequestManagement.priority == priority)
    if location:
        q = q.where(RequestManagement.location == location)
    if department:
        q = q.where(RequestManagement.department == department)
    if workflow:
        q = q.where(RequestManagement.workflow == workflow)
    if employee_id:
        q = q.where(RequestManagement.employee_id == employee_id)
    if search:
        like = f"%{search}%"
        q = q.where(
            RequestManagement.request_id.ilike(like)
            | RequestManagement.subject.ilike(like)
        )
    if date_from:
        q = q.where(RequestManagement.submitted_at >= datetime.fromisoformat(date_from))
    if date_to:
        q = q.where(RequestManagement.submitted_at <= datetime.fromisoformat(date_to + "T23:59:59"))

    q = q.order_by(RequestManagement.submitted_at.desc()).offset(skip).limit(limit)
    return db.execute(q).scalars().all()


@router.get(
    "/employee/{employee_id}",
    response_model=List[RequestManagementListOut],
    summary="List all requests by a specific employee",
)
def list_employee_requests(
    employee_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    category:     Optional[str] = Query(None),
    skip: int  = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = (
        select(RequestManagement)
        .where(
            RequestManagement.employee_id == employee_id,
            RequestManagement.is_deleted.is_(False),
        )
    )
    if status_filter:
        q = q.where(RequestManagement.status == status_filter)
    if category:
        q = q.where(RequestManagement.category == category)
    q = q.order_by(RequestManagement.submitted_at.desc()).offset(skip).limit(limit)
    return db.execute(q).scalars().all()


@router.get(
    "/{request_id}",
    response_model=RequestManagementOut,
    summary="Get full request detail including all sub-tables",
)
def get_request(request_id: int, db: Session = Depends(get_db)):
    return _get_or_404(request_id, db)


@router.get(
    "/by-ref/{public_id}",
    response_model=RequestManagementOut,
    summary="Get request by public ID (e.g. REQ-2024-000001)",
)
def get_request_by_ref(public_id: str, db: Session = Depends(get_db)):
    req = db.execute(
        _eager_load(
            select(RequestManagement).where(
                RequestManagement.request_id == public_id.upper(),
                RequestManagement.is_deleted.is_(False),
            )
        )
    ).scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@router.patch(
    "/{request_id}",
    response_model=RequestManagementOut,
    summary="Update master fields and/or detail fields",
)
def update_request(
    request_id: int,
    payload: RequestManagementUpdate,
    db: Session = Depends(get_db),
):
    req = _get_or_404(request_id, db)

    master_fields = {"subject", "description", "priority", "workflow", "assigned_to", "resolution_note"}
    for field in master_fields:
        val = getattr(payload, field, None)
        if val is not None:
            setattr(req, field, val)

    if payload.status and payload.status != req.status:
        _transition_status(req, payload.status, None, "Updated via PATCH", db)
    else:
        req.updated_at = datetime.utcnow()

    
    detail_update_map = {
        "personal_info_detail":  req.personal_info_detail,
        "work_related_detail":   req.work_related_detail,
        "admin_detail":          req.admin_detail,
        "financial_detail":      req.financial_detail,
        "travel_expense_detail": req.travel_expense_detail,
        "it_systems_detail":     req.it_systems_detail,
        "feedback_detail":       req.feedback_detail,
    }
    for attr, detail_obj in detail_update_map.items():
        detail_payload = getattr(payload, attr, None)
        if detail_payload is None:
            continue
        if detail_obj is None:
          
            model_class = _DETAIL_MAP[req.category][1]
            new_obj = model_class(
                request_id=req.id,
                **detail_payload.model_dump(exclude_unset=True)
            )
            db.add(new_obj)
        else:
            for k, v in detail_payload.model_dump(exclude_unset=True).items():
                setattr(detail_obj, k, v)

    db.commit()
    return _get_or_404(request_id, db)


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a request",
)
def delete_request(request_id: int, db: Session = Depends(get_db)):
    req = _get_or_404(request_id, db)
    req.is_deleted = True
    req.deleted_at = datetime.utcnow()
    db.commit()


@router.patch(
    "/{request_id}/status",
    response_model=RequestManagementOut,
    summary="Generic status transition with audit log",
)
def transition_status(
    request_id: int,
    payload: StatusTransitionPayload,
    db: Session = Depends(get_db),
):
    valid_statuses = [e.value for e in RequestStatus]
    if payload.new_status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )
    req = _get_or_404(request_id, db)
    _transition_status(req, payload.new_status, payload.changed_by, payload.note, db)
    db.commit()
    return _get_or_404(request_id, db)


@router.patch(
    "/{request_id}/approve",
    response_model=RequestManagementOut,
    summary="Approve a request",
)
def approve_request(
    request_id: int,
    changed_by: Optional[str] = Query(None),
    note: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    req = _get_or_404(request_id, db)
    if req.status == RequestStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Request is already approved")
    _transition_status(req, RequestStatus.APPROVED, changed_by, note or "Approved", db)
    db.commit()
    return _get_or_404(request_id, db)


@router.patch(
    "/{request_id}/reject",
    response_model=RequestManagementOut,
    summary="Reject a request",
)
def reject_request(
    request_id: int,
    changed_by: Optional[str] = Query(None),
    note: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    req = _get_or_404(request_id, db)
    _transition_status(req, RequestStatus.REJECTED, changed_by, note or "Rejected", db)
    db.commit()
    return _get_or_404(request_id, db)


@router.patch(
    "/{request_id}/resolve",
    response_model=RequestManagementOut,
    summary="Mark a request as completed/resolved with resolution note",
)
def resolve_request(
    request_id: int,
    payload: ResolvePayload,
    db: Session = Depends(get_db),
):
    req = _get_or_404(request_id, db)
    req.resolution_note = payload.resolution_note
    req.resolved_by     = payload.resolved_by
    req.resolved_at     = datetime.utcnow()
    _transition_status(req, RequestStatus.COMPLETED, payload.resolved_by, payload.resolution_note, db)
    db.commit()
    return _get_or_404(request_id, db)


@router.patch(
    "/{request_id}/assign",
    response_model=RequestManagementOut,
    summary="Assign request to an HR agent",
)
def assign_request(
    request_id: int,
    payload: AssignPayload,
    db: Session = Depends(get_db),
):
    req = _get_or_404(request_id, db)
    req.assigned_to = payload.assigned_to
    req.assigned_at = datetime.utcnow()
    if req.status == RequestStatus.OPEN:
        _transition_status(req, RequestStatus.IN_PROGRESS, payload.assigned_by, "Assigned to agent", db)
    else:
        req.updated_at = datetime.utcnow()
    db.commit()
    return _get_or_404(request_id, db)


@router.patch(
    "/{request_id}/close",
    response_model=RequestManagementOut,
    summary="Close a request",
)
def close_request(
    request_id: int,
    changed_by: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    req = _get_or_404(request_id, db)
    _transition_status(req, RequestStatus.CLOSED, changed_by, "Closed", db)
    db.commit()
    return _get_or_404(request_id, db)


@router.get(
    "/{request_id}/comments",
    response_model=List[CommentOut],
    summary="List all comments on a request",
)
def list_comments(request_id: int, db: Session = Depends(get_db)):
    _get_or_404(request_id, db)   
    rows = db.execute(
        select(RequestComment)
        .where(RequestComment.request_id == request_id)
        .order_by(RequestComment.created_at)
    ).scalars().all()
    return rows


@router.post(
    "/{request_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment or internal note to a request",
)
def add_comment(
    request_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
):
    _get_or_404(request_id, db)
    comment = RequestComment(
        request_id  = request_id,
        body        = payload.body,
        is_internal = payload.is_internal,
        author_name = payload.author_name,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment



class _AttachmentCreate(AttachmentOut.__class__):
    pass


from pydantic import BaseModel as _BM


class AttachmentCreatePayload(_BM):
    file_name:       str
    file_url:        str
    file_size_bytes: Optional[int] = None
    mime_type:       Optional[str] = None
    uploaded_by:     Optional[str] = None


@router.post(
    "/{request_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a file attachment URL against a request",
)
def add_attachment(
    request_id: int,
    payload: AttachmentCreatePayload,
    db: Session = Depends(get_db),
):
    _get_or_404(request_id, db)
    att = RequestAttachment(
        request_id      = request_id,
        file_name       = payload.file_name,
        file_url        = payload.file_url,
        file_size_bytes = payload.file_size_bytes,
        mime_type       = payload.mime_type,
        uploaded_by     = payload.uploaded_by,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


@router.delete(
    "/{request_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attachment",
)
def delete_attachment(
    request_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
):
    att = db.execute(
        select(RequestAttachment).where(
            RequestAttachment.id == attachment_id,
            RequestAttachment.request_id == request_id,
        )
    ).scalars().first()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    db.delete(att)
    db.commit()


from pydantic import BaseModel as _BM2


class BulkStatusPayload(_BM2):
    request_ids: List[int]
    new_status:  str
    changed_by:  Optional[str] = None
    note:        Optional[str] = None


@router.post(
    "/bulk/status",
    summary="Bulk status update for multiple requests",
)
def bulk_update_status(payload: BulkStatusPayload, db: Session = Depends(get_db)):
    valid_statuses = [e.value for e in RequestStatus]
    if payload.new_status not in valid_statuses:
        raise HTTPException(status_code=422, detail=f"Invalid status: {payload.new_status}")

    updated = []
    failed  = []
    for rid in payload.request_ids:
        try:
            req = db.execute(
                select(RequestManagement).where(
                    RequestManagement.id == rid,
                    RequestManagement.is_deleted.is_(False),
                )
            ).scalars().first()
            if not req:
                failed.append({"id": rid, "reason": "not found"})
                continue
            _transition_status(req, payload.new_status, payload.changed_by, payload.note, db)
            updated.append(rid)
        except Exception as exc: 
            failed.append({"id": rid, "reason": str(exc)})

    db.commit()
    return {"updated": updated, "failed": failed}
