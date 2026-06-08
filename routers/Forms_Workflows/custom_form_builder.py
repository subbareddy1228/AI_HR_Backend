from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from model.Forms_Workflows.custom_form import CustomForm, FormSubmission
from schema.Forms_Workflows.custom_form import (
    CustomFormCreate,
    CustomFormUpdate,
    CustomFormResponse,
    CustomFormSummary,
    FormSubmissionCreate,
    FormSubmissionUpdate,
    FormSubmissionResponse,
    FormDashboardStats,
)

router = APIRouter(prefix="/api/custom-forms", tags=["Custom Form Builder"])


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD STATS
#  GET /api/custom-forms/dashboard/stats
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/stats", response_model=FormDashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_forms      = db.query(CustomForm).count()
    active_forms     = db.query(CustomForm).filter(CustomForm.is_active == True).count()
    published_forms  = db.query(CustomForm).filter(CustomForm.is_published == True).count()
    total_submissions = db.query(FormSubmission).count()

    return FormDashboardStats(
        total_forms=total_forms,
        active_forms=active_forms,
        published_forms=published_forms,
        total_submissions=total_submissions,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  LIST FORMS
#  GET /api/custom-forms/
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=List[CustomFormSummary])
def list_forms(
    category:     Optional[str]  = Query(None, description="Onboarding/Leave/Expense/Survey/Exit/Other"),
    is_active:    Optional[bool] = Query(None),
    is_published: Optional[bool] = Query(None),
    search:       Optional[str]  = Query(None, description="Search by form name"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(CustomForm)
    if category:
        q = q.filter(CustomForm.form_category == category)
    if is_active is not None:
        q = q.filter(CustomForm.is_active == is_active)
    if is_published is not None:
        q = q.filter(CustomForm.is_published == is_published)
    if search:
        q = q.filter(CustomForm.form_name.ilike(f"%{search}%"))
    return q.order_by(CustomForm.created_at.desc()).offset(skip).limit(limit).all()


# ══════════════════════════════════════════════════════════════════════════════
#  GET SINGLE FORM (full with fields)
#  GET /api/custom-forms/{form_id}
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{form_id}", response_model=CustomFormResponse)
def get_form(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  CREATE FORM
#  POST /api/custom-forms/
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=CustomFormResponse, status_code=201)
def create_form(payload: CustomFormCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    # Convert list of FormFieldDefinition to plain dicts for JSON storage
    if data.get("fields_schema"):
        data["fields_schema"] = [
            f if isinstance(f, dict) else f.model_dump()
            for f in (payload.fields_schema or [])
        ]
    form = CustomForm(**data)
    db.add(form)
    db.commit()
    db.refresh(form)
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  UPDATE FORM
#  PUT /api/custom-forms/{form_id}
# ══════════════════════════════════════════════════════════════════════════════

@router.put("/{form_id}", response_model=CustomFormResponse)
def update_form(form_id: int, payload: CustomFormUpdate, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    data = payload.model_dump(exclude_unset=True)
    if "fields_schema" in data and data["fields_schema"] is not None:
        data["fields_schema"] = [
            f if isinstance(f, dict) else f.model_dump()
            for f in (payload.fields_schema or [])
        ]
    for field, value in data.items():
        setattr(form, field, value)
    # Bump version on schema change
    if "fields_schema" in data:
        form.version = (form.version or 1) + 1
    form.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  DELETE FORM
#  DELETE /api/custom-forms/{form_id}
# ══════════════════════════════════════════════════════════════════════════════

@router.delete("/{form_id}", status_code=204)
def delete_form(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    # Prevent delete if submissions exist
    sub_count = db.query(FormSubmission).filter(FormSubmission.form_id == form_id).count()
    if sub_count:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete — {sub_count} submission(s) exist. Deactivate instead."
        )
    db.delete(form)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  TOGGLE ACTIVE
#  PATCH /api/custom-forms/{form_id}/toggle-active
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{form_id}/toggle-active", response_model=CustomFormResponse)
def toggle_active(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    form.is_active = not form.is_active
    form.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLISH / UNPUBLISH
#  PATCH /api/custom-forms/{form_id}/publish
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{form_id}/publish", response_model=CustomFormResponse)
def toggle_publish(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if not form.is_active and not form.is_published:
        raise HTTPException(status_code=400, detail="Activate the form before publishing")
    form.is_published = not form.is_published
    form.updated_at   = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  DUPLICATE FORM
#  POST /api/custom-forms/{form_id}/duplicate
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{form_id}/duplicate", response_model=CustomFormResponse, status_code=201)
def duplicate_form(form_id: int, db: Session = Depends(get_db)):
    original = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Form not found")
    copy = CustomForm(
        form_name     = f"{original.form_name} (Copy)",
        form_category = original.form_category,
        description   = original.description,
        fields_schema = original.fields_schema,
        is_active     = False,
        is_published  = False,
        version       = 1,
        created_by    = original.created_by,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


# ══════════════════════════════════════════════════════════════════════════════
#  FORM SUBMISSIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{form_id}/submissions", response_model=FormSubmissionResponse, status_code=201)
def submit_form(form_id: int, payload: FormSubmissionCreate, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if not form.is_active:
        raise HTTPException(status_code=400, detail="Form is not active")
    if not form.is_published:
        raise HTTPException(status_code=400, detail="Form is not published yet")
    data = payload.model_dump()
    data["form_id"] = form_id
    submission = FormSubmission(**data)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/{form_id}/submissions", response_model=List[FormSubmissionResponse])
def list_submissions(
    form_id: int,
    status:        Optional[str] = Query(None, description="Draft/Submitted/Reviewed/Approved/Rejected"),
    employee_name: Optional[str] = Query(None),
    skip:  int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    q = db.query(FormSubmission).filter(FormSubmission.form_id == form_id)
    if status:
        q = q.filter(FormSubmission.status == status)
    if employee_name:
        q = q.filter(FormSubmission.employee_name.ilike(f"%{employee_name}%"))
    return q.order_by(FormSubmission.submitted_at.desc()).offset(skip).limit(limit).all()


@router.get("/{form_id}/submissions/{submission_id}", response_model=FormSubmissionResponse)
def get_submission(form_id: int, submission_id: int, db: Session = Depends(get_db)):
    sub = db.query(FormSubmission).filter(
        FormSubmission.id == submission_id,
        FormSubmission.form_id == form_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


@router.put("/{form_id}/submissions/{submission_id}", response_model=FormSubmissionResponse)
def update_submission(
    form_id: int, submission_id: int,
    payload: FormSubmissionUpdate,
    db: Session = Depends(get_db),
):
    sub = db.query(FormSubmission).filter(
        FormSubmission.id == submission_id,
        FormSubmission.form_id == form_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sub, field, value)
    if payload.reviewed_by:
        sub.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return sub


@router.patch("/{form_id}/submissions/{submission_id}/review", response_model=FormSubmissionResponse)
def review_submission(
    form_id: int,
    submission_id: int,
    status:       str = Query(..., description="Reviewed/Approved/Rejected"),
    reviewed_by:  str = Query(...),
    review_notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    allowed = {"Reviewed", "Approved", "Rejected"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")
    sub = db.query(FormSubmission).filter(
        FormSubmission.id == submission_id,
        FormSubmission.form_id == form_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    sub.status       = status
    sub.reviewed_by  = reviewed_by
    sub.review_notes = review_notes
    sub.reviewed_at  = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/{form_id}/submissions/{submission_id}", status_code=204)
def delete_submission(form_id: int, submission_id: int, db: Session = Depends(get_db)):
    sub = db.query(FormSubmission).filter(
        FormSubmission.id == submission_id,
        FormSubmission.form_id == form_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    db.delete(sub)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  SUBMISSION SUMMARY
#  GET /api/custom-forms/{form_id}/submissions/summary
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{form_id}/submissions/summary/stats")
def submission_summary(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    all_subs = db.query(FormSubmission).filter(FormSubmission.form_id == form_id).all()
    total    = len(all_subs)
    by_status = {}
    for s in all_subs:
        by_status[s.status] = by_status.get(s.status, 0) + 1
    return {
        "form_id":    form_id,
        "form_name":  form.form_name,
        "total":      total,
        "by_status":  by_status,
    }