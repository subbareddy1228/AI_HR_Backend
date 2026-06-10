# routers/Forms_Workflows/custom_form_builder.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from model.Forms_Workflows.custom_form import CustomForm, FormSubmission, FormVersion
from schema.Forms_Workflows.custom_form import (
    CustomFormCreate,
    CustomFormUpdate,
    CustomFormResponse,
    CustomFormSummary,
    FormSubmissionCreate,
    FormSubmissionUpdate,
    FormSubmissionResponse,
    FormVersionResponse,
    FormDashboardStats,
)

router = APIRouter(prefix="/api/custom-forms", tags=["Custom Form Builder"])


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD STATS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/stats", response_model=FormDashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_forms       = db.query(CustomForm).count()
    draft_forms       = db.query(CustomForm).filter(CustomForm.status == "Draft").count()
    published_forms   = db.query(CustomForm).filter(CustomForm.status == "Published").count()
    archived_forms    = db.query(CustomForm).filter(CustomForm.status == "Archived").count()
    total_submissions = db.query(FormSubmission).count()
    return FormDashboardStats(
        total_forms=total_forms,
        draft_forms=draft_forms,
        published_forms=published_forms,
        archived_forms=archived_forms,
        total_submissions=total_submissions,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  LIST FORMS
#  Supports status tabs: Draft / Published / Archived
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=List[CustomFormSummary])
def list_forms(
    status:       Optional[str]  = Query(None, description="Draft/Published/Archived"),
    form_category: Optional[str] = Query(None),
    is_active:    Optional[bool] = Query(None),
    search:       Optional[str]  = Query(None, description="Search by form name"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(CustomForm)
    if status:
        q = q.filter(CustomForm.status == status)
    if form_category:
        q = q.filter(CustomForm.form_category == form_category)
    if is_active is not None:
        q = q.filter(CustomForm.is_active == is_active)
    if search:
        q = q.filter(CustomForm.form_name.ilike(f"%{search}%"))
    return q.order_by(CustomForm.created_at.desc()).offset(skip).limit(limit).all()


# ══════════════════════════════════════════════════════════════════════════════
#  GET SINGLE FORM (full with pages/fields)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{form_id}", response_model=CustomFormResponse)
def get_form(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  CREATE FORM
#  Triggered by new form creation in Form Design Interface
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=CustomFormResponse, status_code=201)
def create_form(payload: CustomFormCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    # Serialize nested Pydantic objects to dicts
    if payload.pages:
        data["pages"] = [p.model_dump() for p in payload.pages]
    if payload.fields_schema:
        data["fields_schema"] = [f.model_dump() for f in payload.fields_schema]
    form = CustomForm(**data)
    db.add(form)
    db.commit()
    db.refresh(form)
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  UPDATE FORM (Save button)
#  Auto-saves version history on page/field changes
# ══════════════════════════════════════════════════════════════════════════════

@router.put("/{form_id}", response_model=CustomFormResponse)
def update_form(
    form_id: int,
    payload: CustomFormUpdate,
    changed_by: Optional[str] = Query(None),
    change_notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    data = payload.model_dump(exclude_unset=True)
    schema_changed = "pages" in data or "fields_schema" in data

    if "pages" in data and payload.pages is not None:
        data["pages"] = [p.model_dump() for p in payload.pages]
    if "fields_schema" in data and payload.fields_schema is not None:
        data["fields_schema"] = [f.model_dump() for f in payload.fields_schema]

    for field, value in data.items():
        setattr(form, field, value)

    # Save version snapshot if schema changed
    if schema_changed:
        form.version = (form.version or 1) + 1
        snapshot = FormVersion(
            form_id=form_id,
            version_number=form.version,
            pages=form.pages,
            fields_schema=form.fields_schema,
            changed_by=changed_by,
            change_notes=change_notes,
        )
        db.add(snapshot)

    form.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  DELETE FORM
# ══════════════════════════════════════════════════════════════════════════════

@router.delete("/{form_id}", status_code=204)
def delete_form(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    sub_count = db.query(FormSubmission).filter(FormSubmission.form_id == form_id).count()
    if sub_count:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete — {sub_count} submission(s) exist. Archive instead."
        )
    db.delete(form)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLISH (Publish button in UI)
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{form_id}/publish", response_model=CustomFormResponse)
def publish_form(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if not form.is_active:
        raise HTTPException(status_code=400, detail="Activate the form before publishing")
    form.status      = "Published"
    form.is_published = True
    form.updated_at  = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  UNPUBLISH → back to Draft
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{form_id}/unpublish", response_model=CustomFormResponse)
def unpublish_form(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    form.status       = "Draft"
    form.is_published = False
    form.updated_at   = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  ARCHIVE
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{form_id}/archive", response_model=CustomFormResponse)
def archive_form(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    form.status       = "Archived"
    form.is_active    = False
    form.is_published = False
    form.updated_at   = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  DUPLICATE (Duplicate button in UI)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{form_id}/duplicate", response_model=CustomFormResponse, status_code=201)
def duplicate_form(form_id: int, db: Session = Depends(get_db)):
    original = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Form not found")
    copy = CustomForm(
        form_name                  = f"{original.form_name} (Copy)",
        form_category              = original.form_category,
        description                = original.description,
        pages                      = original.pages,
        fields_schema              = original.fields_schema,
        prepopulate_fields         = original.prepopulate_fields,
        allow_multiple_submissions = original.allow_multiple_submissions,
        require_approval           = original.require_approval,
        approver_role              = original.approver_role,
        show_progress_bar          = original.show_progress_bar,
        allow_save_draft           = original.allow_save_draft,
        status                     = "Draft",
        is_active                  = False,
        is_published               = False,
        version                    = 1,
        created_by                 = original.created_by,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


# ══════════════════════════════════════════════════════════════════════════════
#  RESET FORM FIELDS (Reset button in UI)
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{form_id}/reset", response_model=CustomFormResponse)
def reset_form(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    form.pages        = None
    form.fields_schema = None
    form.updated_at   = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ══════════════════════════════════════════════════════════════════════════════
#  VERSION HISTORY (Version History section in UI)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{form_id}/versions", response_model=List[FormVersionResponse])
def get_version_history(form_id: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return (
        db.query(FormVersion)
        .filter(FormVersion.form_id == form_id)
        .order_by(FormVersion.version_number.desc())
        .all()
    )


@router.post("/{form_id}/versions/{version_number}/restore", response_model=CustomFormResponse)
def restore_version(form_id: int, version_number: int, db: Session = Depends(get_db)):
    form = db.query(CustomForm).filter(CustomForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    version = db.query(FormVersion).filter(
        FormVersion.form_id == form_id,
        FormVersion.version_number == version_number,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    form.pages        = version.pages
    form.fields_schema = version.fields_schema
    form.version      = form.version + 1
    form.updated_at   = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


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
    if not form.allow_multiple_submissions:
        existing = db.query(FormSubmission).filter(
            FormSubmission.form_id == form_id,
            FormSubmission.submitted_by == payload.submitted_by,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="You have already submitted this form")
    data = payload.model_dump()
    data["form_id"]      = form_id
    data["form_version"] = form.version
    submission = FormSubmission(**data)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/{form_id}/submissions", response_model=List[FormSubmissionResponse])
def list_submissions(
    form_id:       int,
    status:        Optional[str] = Query(None, description="Draft/Submitted/Reviewed/Approved/Rejected"),
    employee_name: Optional[str] = Query(None),
    skip:  int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
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
    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return sub


@router.patch("/{form_id}/submissions/{submission_id}/review", response_model=FormSubmissionResponse)
def review_submission(
    form_id:      int,
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
    sub.updated_at   = datetime.utcnow()
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


# ── Submission Summary Stats ───────────────────────────────────────────────────
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
        "form_id":   form_id,
        "form_name": form.form_name,
        "version":   form.version,
        "total":     total,
        "by_status": by_status,
    }