from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from model.HR_Operations.letter_generation import (
    LetterTemplate,
    LetterRequest,
    LetterGeneration,
    LetterWorkflow,
    LetterSystemSettings,
)
from schema.HR_Operations.letter_generation import (
    LetterTemplateCreate,
    LetterTemplateUpdate,
    LetterTemplateResponse,
    LetterRequestCreate,
    LetterRequestUpdate,
    LetterRequestResponse,
    LetterGenerationCreate,
    LetterGenerationUpdate,
    LetterGenerationResponse,
    LetterWorkflowCreate,
    LetterWorkflowUpdate,
    LetterWorkflowResponse,
    LetterSystemSettingsUpdate,
    LetterSystemSettingsResponse,
    DashboardStatsResponse,
    LetterUsageReportItem,
    EmployeeLetterReportItem,
)

router = APIRouter(prefix="/letter-generation", tags=["Letter Generation"])




@router.get("/dashboard", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Aggregate stats shown on the Dashboard tab (totals cards)."""
    total_templates   = db.query(LetterTemplate).count()
    active_templates  = db.query(LetterTemplate).filter(LetterTemplate.is_active == True).count()
    ai_templates      = db.query(LetterTemplate).filter(LetterTemplate.is_ai_optimised == True).count()

    total_requests    = db.query(LetterRequest).count()
    approved_requests = db.query(LetterRequest).filter(LetterRequest.status == "Approved").count()
    pending_requests  = db.query(LetterRequest).filter(LetterRequest.status == "Pending").count()
    rejected_requests = db.query(LetterRequest).filter(LetterRequest.status == "Rejected").count()
    auto_approved     = db.query(LetterRequest).join(
        LetterTemplate, LetterRequest.template_id == LetterTemplate.id
    ).filter(LetterTemplate.auto_approve == True, LetterRequest.status == "Approved").count()

    total_downloads   = db.query(func.coalesce(func.sum(LetterGeneration.download_count), 0)).scalar()

    return DashboardStatsResponse(
        total_templates=total_templates,
        active_templates=active_templates,
        ai_optimised_templates=ai_templates,
        total_requests=total_requests,
        approved_requests=approved_requests,
        pending_requests=pending_requests,
        rejected_requests=rejected_requests,
        auto_approved_count=auto_approved,
        total_downloads=int(total_downloads),
    )




@router.post("/templates", response_model=LetterTemplateResponse, status_code=201)
def create_template(payload: LetterTemplateCreate, db: Session = Depends(get_db)):
    existing = db.query(LetterTemplate).filter(
        LetterTemplate.template_code == payload.template_code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template code already exists")
    record = LetterTemplate(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/templates", response_model=List[LetterTemplateResponse])
def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    query = db.query(LetterTemplate)
    if active_only:
        query = query.filter(LetterTemplate.is_active == True)
    if category:
        query = query.filter(LetterTemplate.category == category)
    return query.order_by(LetterTemplate.template_code).all()


@router.get("/templates/{template_id}", response_model=LetterTemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db)):
    record = db.query(LetterTemplate).filter(LetterTemplate.id == template_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Template not found")
    return record


@router.patch("/templates/{template_id}", response_model=LetterTemplateResponse)
def update_template(template_id: int, payload: LetterTemplateUpdate, db: Session = Depends(get_db)):
    record = db.query(LetterTemplate).filter(LetterTemplate.id == template_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Template not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    record = db.query(LetterTemplate).filter(LetterTemplate.id == template_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(record)
    db.commit()
    return {"message": "Template deleted successfully"}



def _next_request_code(db: Session) -> str:
    count = db.query(LetterRequest).count()
    year  = datetime.utcnow().year
    return f"LTR-REQ-{year}-{str(count + 1).zfill(3)}"


@router.post("/requests", response_model=LetterRequestResponse, status_code=201)
def create_request(payload: LetterRequestCreate, db: Session = Depends(get_db)):
    template = db.query(LetterTemplate).filter(
        LetterTemplate.id == payload.template_id, LetterTemplate.is_active == True
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Active template not found")

    
    settings = db.query(LetterSystemSettings).first()
    sla_map = {
        "High":   settings.high_priority_sla_hours   if settings else 4,
        "Medium": settings.medium_priority_sla_hours if settings else 24,
        "Low":    settings.low_priority_sla_hours    if settings else 72,
    }
    sla = sla_map.get(payload.priority, 24)

    
    initial_status = "Approved" if template.auto_approve else "Pending"

    record = LetterRequest(
        request_code=_next_request_code(db),
        sla_hours=sla,
        status=initial_status,
        **payload.model_dump(),
    )
    db.add(record)

    
    template.times_used += 1

    db.commit()
    db.refresh(record)
    return record


@router.get("/requests", response_model=List[LetterRequestResponse])
def list_requests(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(LetterRequest)
    if status:
        query = query.filter(LetterRequest.status == status)
    if priority:
        query = query.filter(LetterRequest.priority == priority)
    if employee_id:
        query = query.filter(LetterRequest.employee_id == employee_id)
    return query.order_by(LetterRequest.requested_at.desc()).all()


@router.get("/requests/{request_id}", response_model=LetterRequestResponse)
def get_request(request_id: int, db: Session = Depends(get_db)):
    record = db.query(LetterRequest).filter(LetterRequest.id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Letter request not found")
    return record


@router.patch("/requests/{request_id}", response_model=LetterRequestResponse)
def update_request(request_id: int, payload: LetterRequestUpdate, db: Session = Depends(get_db)):
    record = db.query(LetterRequest).filter(LetterRequest.id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Letter request not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    if "status" in payload.model_dump(exclude_unset=True):
        record.last_action_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.delete("/requests/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db)):
    record = db.query(LetterRequest).filter(LetterRequest.id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Letter request not found")
    db.delete(record)
    db.commit()
    return {"message": "Request deleted successfully"}




def _next_letter_code(db: Session) -> str:
    count = db.query(LetterGeneration).count()
    year  = datetime.utcnow().year
    return f"LTR-{year}-{str(count + 1).zfill(3)}"


def _next_verification_code(db: Session) -> str:
    count = db.query(LetterGeneration).count()
    year  = datetime.utcnow().year
    return f"VER-{year}-{str(count + 1).zfill(3)}"


@router.post("/generate", response_model=LetterGenerationResponse, status_code=201)
def generate_letter(payload: LetterGenerationCreate, db: Session = Depends(get_db)):
    
    template = db.query(LetterTemplate).filter(LetterTemplate.id == payload.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    settings = db.query(LetterSystemSettings).first()
    use_signature = payload.digital_signature or (
        settings.default_digital_signature == "Enable for all letters" if settings else False
    )

    record = LetterGeneration(
        letter_code=_next_letter_code(db),
        verification_code=_next_verification_code(db),
        digital_signature=use_signature,
        **payload.model_dump(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/generate", response_model=List[LetterGenerationResponse])
def list_generated_letters(
    status: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(LetterGeneration)
    if status:
        query = query.filter(LetterGeneration.status == status)
    if employee_id:
        query = query.filter(LetterGeneration.employee_id == employee_id)
    return query.order_by(LetterGeneration.created_at.desc()).all()




@router.get("/archive", response_model=List[LetterGenerationResponse])
def list_archive(
    letter_type: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    
    query = db.query(LetterGeneration).filter(LetterGeneration.status == "ISSUED")
    if letter_type:
        query = query.filter(LetterGeneration.letter_type == letter_type)
    if employee_id:
        query = query.filter(LetterGeneration.employee_id == employee_id)
    return query.order_by(LetterGeneration.created_at.desc()).all()


@router.get("/archive/{letter_id}", response_model=LetterGenerationResponse)
def get_archived_letter(letter_id: int, db: Session = Depends(get_db)):
    record = db.query(LetterGeneration).filter(LetterGeneration.id == letter_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Letter not found")
    return record


@router.patch("/archive/{letter_id}", response_model=LetterGenerationResponse)
def update_letter(letter_id: int, payload: LetterGenerationUpdate, db: Session = Depends(get_db)):
    record = db.query(LetterGeneration).filter(LetterGeneration.id == letter_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Letter not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/archive/{letter_id}")
def delete_letter(letter_id: int, db: Session = Depends(get_db)):
    record = db.query(LetterGeneration).filter(LetterGeneration.id == letter_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Letter not found")
    db.delete(record)
    db.commit()
    return {"message": "Letter deleted successfully"}


@router.post("/archive/{letter_id}/download")
def record_download(letter_id: int, db: Session = Depends(get_db)):
    
    record = db.query(LetterGeneration).filter(LetterGeneration.id == letter_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Letter not found")
    record.download_count += 1
    record.last_downloaded_at = datetime.utcnow()
    db.commit()
    return {"message": "Download recorded", "download_count": record.download_count}




@router.post("/workflow", response_model=LetterWorkflowResponse, status_code=201)
def create_workflow_step(payload: LetterWorkflowCreate, db: Session = Depends(get_db)):
    request = db.query(LetterRequest).filter(LetterRequest.id == payload.request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Letter request not found")
    record = LetterWorkflow(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/workflow", response_model=List[LetterWorkflowResponse])
def list_workflows(
    request_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(LetterWorkflow)
    if request_id:
        query = query.filter(LetterWorkflow.request_id == request_id)
    if status:
        query = query.filter(LetterWorkflow.status == status)
    return query.order_by(LetterWorkflow.request_id, LetterWorkflow.step_number).all()


@router.patch("/workflow/{workflow_id}", response_model=LetterWorkflowResponse)
def update_workflow_step(workflow_id: int, payload: LetterWorkflowUpdate, db: Session = Depends(get_db)):
    record = db.query(LetterWorkflow).filter(LetterWorkflow.id == workflow_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Workflow step not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    if "status" in payload.model_dump(exclude_unset=True):
        record.actioned_at = datetime.utcnow()
        
        if payload.status in ("Approved", "Rejected"):
            all_steps = db.query(LetterWorkflow).filter(
                LetterWorkflow.request_id == record.request_id
            ).all()
            if payload.status == "Rejected":
                req = db.query(LetterRequest).filter(
                    LetterRequest.id == record.request_id
                ).first()
                if req:
                    req.status = "Rejected"
                    req.last_action_at = datetime.utcnow()
            elif all(s.status in ("Approved", "Skipped") for s in all_steps if s.id != workflow_id):
                req = db.query(LetterRequest).filter(
                    LetterRequest.id == record.request_id
                ).first()
                if req:
                    req.status = "Approved"
                    req.last_action_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.post("/workflow/bulk-approve")
def bulk_approve_workflows(request_ids: List[int], db: Session = Depends(get_db)):
    
    updated = 0
    for rid in request_ids:
        req = db.query(LetterRequest).filter(
            LetterRequest.id == rid, LetterRequest.status == "Pending"
        ).first()
        if req:
            req.status = "Approved"
            req.last_action_at = datetime.utcnow()
            updated += 1
    db.commit()
    return {"message": f"{updated} requests approved"}




@router.get("/employee-portal/{employee_id}/requests", response_model=List[LetterRequestResponse])
def employee_my_requests(employee_id: int, db: Session = Depends(get_db)):
    
    return (
        db.query(LetterRequest)
        .filter(LetterRequest.employee_id == employee_id)
        .order_by(LetterRequest.requested_at.desc())
        .all()
    )


@router.get("/employee-portal/{employee_id}/downloads", response_model=List[LetterGenerationResponse])
def employee_downloads(employee_id: int, db: Session = Depends(get_db)):
    
    return (
        db.query(LetterGeneration)
        .filter(
            LetterGeneration.employee_id == employee_id,
            LetterGeneration.status == "ISSUED",
        )
        .order_by(LetterGeneration.created_at.desc())
        .all()
    )




@router.get("/reports/letter-usage", response_model=List[LetterUsageReportItem])
def letter_usage_report(db: Session = Depends(get_db)):
    
    templates = db.query(LetterTemplate).all()
    result = []
    for t in templates:
        requests = db.query(LetterRequest).filter(LetterRequest.template_id == t.id).all()
        approved = sum(1 for r in requests if r.status == "Approved")
        rejected = sum(1 for r in requests if r.status == "Rejected")
        pending  = sum(1 for r in requests if r.status == "Pending")
        downloads = (
            db.query(func.coalesce(func.sum(LetterGeneration.download_count), 0))
            .filter(LetterGeneration.template_id == t.id)
            .scalar()
        )
        result.append(
            LetterUsageReportItem(
                template_id=t.id,
                template_code=t.template_code,
                template_name=t.name,
                category=t.category,
                total_requests=len(requests),
                approved=approved,
                rejected=rejected,
                pending=pending,
                total_downloads=int(downloads),
            )
        )
    return result


@router.get("/reports/employee-wise", response_model=List[EmployeeLetterReportItem])
def employee_wise_report(db: Session = Depends(get_db)):
    
    rows = (
        db.query(
            LetterRequest.employee_id,
            func.count(LetterRequest.id).label("total"),
            func.sum(
                func.cast(LetterRequest.status == "Approved", Integer)
            ).label("approved"),
            func.sum(
                func.cast(LetterRequest.status == "Pending", Integer)
            ).label("pending"),
            func.sum(
                func.cast(LetterRequest.status == "Rejected", Integer)
            ).label("rejected"),
        )
        .group_by(LetterRequest.employee_id)
        .all()
    )
    result = []
    for row in rows:
        
        most_common = (
            db.query(LetterTemplate.name, func.count(LetterRequest.id).label("cnt"))
            .join(LetterRequest, LetterRequest.template_id == LetterTemplate.id)
            .filter(LetterRequest.employee_id == row.employee_id)
            .group_by(LetterTemplate.name)
            .order_by(func.count(LetterRequest.id).desc())
            .first()
        )
        result.append(
            EmployeeLetterReportItem(
                employee_id=row.employee_id,
                total_requests=row.total,
                approved=row.approved or 0,
                pending=row.pending or 0,
                rejected=row.rejected or 0,
                most_requested_type=most_common[0] if most_common else None,
            )
        )
    return result




@router.get("/settings", response_model=LetterSystemSettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    record = db.query(LetterSystemSettings).first()
    if not record:
        
        record = LetterSystemSettings()
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


@router.patch("/settings", response_model=LetterSystemSettingsResponse)
def update_settings(payload: LetterSystemSettingsUpdate, db: Session = Depends(get_db)):
    record = db.query(LetterSystemSettings).first()
    if not record:
        record = LetterSystemSettings()
        db.add(record)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.post("/settings/reset")
def reset_settings(db: Session = Depends(get_db)):
    
    record = db.query(LetterSystemSettings).first()
    if record:
        db.delete(record)
    record = LetterSystemSettings()
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"message": "Settings reset to default"}
