from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from core.database import get_db
from typing import Optional, List
from datetime import datetime

from model.Forms_Workflows.custom_form import CustomForm, FormSubmission
from schema.Forms_Workflows.custom_form import (
    CustomFormCreate,
    CustomFormUpdate,
    CustomFormResponse,
    FormSubmissionCreate,
    FormSubmissionResponse,
)

router = APIRouter(
    prefix="/api/custom-forms",
    tags=["Custom Form Builder"],
)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/custom-forms/dashboard/stats
# Get Dashboard Stats
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/dashboard/stats",
    summary="Get Dashboard Stats",
)
def dashboard_stats(db: Session = Depends(get_db)):
    total      = db.execute(select(func.count(CustomForm.id))).scalar()
    published  = db.execute(select(func.count(CustomForm.id)).where(CustomForm.is_active == True)).scalar()
    unpublished = db.execute(select(func.count(CustomForm.id)).where(CustomForm.is_active == False)).scalar()
    submissions = db.execute(select(func.count(FormSubmission.id))).scalar()
    return {
        "total_forms":       total,
        "published_forms":   published,
        "unpublished_forms": unpublished,
        "total_submissions": submissions,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/custom-forms/
# List Forms
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[CustomFormResponse],
    summary="List Forms",
)
def list_forms(
    is_active:     Optional[bool] = Query(None, description="True = published forms only"),
    form_category: Optional[str]  = Query(None, description="General | HR | Leave …"),
    db: Session = Depends(get_db),
):
    query = select(CustomForm)
    if is_active is not None:
        query = query.where(CustomForm.is_active == is_active)
    if form_category:
        query = query.where(CustomForm.form_category == form_category)
    return db.execute(query).scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/custom-forms/
# Create Form
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=CustomFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Form",
)
def create_form(
    payload: CustomFormCreate,
    db: Session = Depends(get_db),
):
    form = CustomForm(**payload.model_dump())
    db.add(form)
    db.commit()
    db.refresh(form)
    return form


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/custom-forms/submissions/{submission_id}
# Get a single submission by ID
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/submissions/{submission_id}",
    response_model=FormSubmissionResponse,
    summary="Fetch a single form submission by ID",
)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
):
    sub = db.execute(
        select(FormSubmission).where(FormSubmission.id == submission_id)
    ).scalars().first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/custom-forms/{form_id}
# Get Form
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{form_id}",
    response_model=CustomFormResponse,
    summary="Get Form",
)
def get_form(
    form_id: int,
    db: Session = Depends(get_db),
):
    form = db.execute(
        select(CustomForm).where(CustomForm.id == form_id)
    ).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form


# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/custom-forms/{form_id}
# Update Form
# ─────────────────────────────────────────────────────────────────────────────

@router.put(
    "/{form_id}",
    response_model=CustomFormResponse,
    summary="Update Form",
)
def update_form(
    form_id: int,
    payload: CustomFormUpdate,
    db: Session = Depends(get_db),
):
    form = db.execute(
        select(CustomForm).where(CustomForm.id == form_id)
    ).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(form, field, value)
    form.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/custom-forms/{form_id}
# Delete Form
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{form_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Form",
)
def delete_form(
    form_id: int,
    db: Session = Depends(get_db),
):
    form = db.execute(
        select(CustomForm).where(CustomForm.id == form_id)
    ).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    db.delete(form)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/custom-forms/{form_id}/publish
# Publish Form  (Publish button in toolbar)
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/{form_id}/publish",
    response_model=CustomFormResponse,
    summary="Publish Form",
)
def publish_form(
    form_id: int,
    db: Session = Depends(get_db),
):
    form = db.execute(
        select(CustomForm).where(CustomForm.id == form_id)
    ).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if form.is_active:
        raise HTTPException(status_code=400, detail="Form is already published")
    form.is_active  = True
    form.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/custom-forms/{form_id}/unpublish
# Unpublish Form
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/{form_id}/unpublish",
    response_model=CustomFormResponse,
    summary="Unpublish Form",
)
def unpublish_form(
    form_id: int,
    db: Session = Depends(get_db),
):
    form = db.execute(
        select(CustomForm).where(CustomForm.id == form_id)
    ).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if not form.is_active:
        raise HTTPException(status_code=400, detail="Form is already unpublished")
    form.is_active  = False
    form.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/custom-forms/{form_id}/archive
# Archive Form
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/{form_id}/archive",
    response_model=CustomFormResponse,
    summary="Archive Form",
)
def archive_form(
    form_id: int,
    db: Session = Depends(get_db),
):
    form = db.execute(
        select(CustomForm).where(CustomForm.id == form_id)
    ).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    form.is_active  = False
    form.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/custom-forms/{form_id}/duplicate
# Duplicate Form  (Duplicate button in toolbar)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{form_id}/duplicate",
    response_model=CustomFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate Form",
)
def duplicate_form(
    form_id: int,
    db: Session = Depends(get_db),
):
    form = db.execute(
        select(CustomForm).where(CustomForm.id == form_id)
    ).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    duplicate = CustomForm(
        form_name     = f"{form.form_name} (Copy)",
        form_category = form.form_category,
        description   = form.description,
        fields_schema = form.fields_schema,
        is_active     = False,
        created_by    = form.created_by,
    )
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    return duplicate


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/custom-forms/{form_id}/reset
# Reset Form  (Reset Form Builder button in Form Configuration tab)
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/{form_id}/reset",
    response_model=CustomFormResponse,
    summary="Reset Form",
)
def reset_form(
    form_id: int,
    db: Session = Depends(get_db),
):
    form = db.execute(
        select(CustomForm).where(CustomForm.id == form_id)
    ).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    form.fields_schema = None
    form.updated_at    = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/custom-forms/{form_id}/submit
# Submit a filled custom form (employee action)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{form_id}/submit",
    response_model=FormSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a filled custom form",
)
def submit_form(
    form_id: int,
    payload: FormSubmissionCreate,
    db: Session = Depends(get_db),
):
    form = db.execute(
        select(CustomForm).where(CustomForm.id == form_id)
    ).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if not form.is_active:
        raise HTTPException(status_code=400, detail="Form is not active")
    data = payload.model_dump()
    data["form_id"] = form_id
    submission = FormSubmission(**data)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/custom-forms/{form_id}/submissions
# List all submissions for a specific form
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{form_id}/submissions",
    response_model=List[FormSubmissionResponse],
    summary="List all submissions for a custom form",
)
def list_submissions(
    form_id: int,
    db: Session = Depends(get_db),
):
    form = db.execute(
        select(CustomForm).where(CustomForm.id == form_id)
    ).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return db.execute(
        select(FormSubmission).where(FormSubmission.form_id == form_id)
    ).scalars().all()