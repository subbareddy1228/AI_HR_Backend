from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.database import get_db
from typing import Optional
from datetime import datetime

from model.Forms_Workflows.custom_form import CustomForm, FormSubmission
from schema.Forms_Workflows.custom_form import (
    CustomFormCreate,
    CustomFormUpdate,
    CustomFormResponse,
    FormSubmissionCreate,
    FormSubmissionResponse,
)

router = APIRouter(prefix="/custom-forms", tags=["Forms & Workflows"])


# ── Form definitions ───────────────────────────────────────────────────────────

@router.post("/", response_model=CustomFormResponse, status_code=status.HTTP_201_CREATED)
def create_form(payload: CustomFormCreate, db: Session = Depends(get_db)):
    form = CustomForm(**payload.model_dump())
    db.add(form)
    db.commit()
    db.refresh(form)
    return form


@router.get("/", response_model=list[CustomFormResponse])
def list_forms(
    is_active: Optional[bool] = Query(None),
    form_category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(CustomForm)
    if is_active is not None:
        query = query.where(CustomForm.is_active == is_active)
    if form_category:
        query = query.where(CustomForm.form_category == form_category)
    return db.execute(query).scalars().all()


@router.get("/submissions/{submission_id}", response_model=FormSubmissionResponse)
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    sub = db.execute(
        select(FormSubmission).where(FormSubmission.id == submission_id)
    ).scalars().first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


@router.get("/{form_id}", response_model=CustomFormResponse)
def get_form(form_id: int, db: Session = Depends(get_db)):
    form = db.execute(select(CustomForm).where(CustomForm.id == form_id)).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form


@router.put("/{form_id}", response_model=CustomFormResponse)
def update_form(form_id: int, payload: CustomFormUpdate, db: Session = Depends(get_db)):
    form = db.execute(select(CustomForm).where(CustomForm.id == form_id)).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(form, field, value)
    form.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(form)
    return form


@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form(form_id: int, db: Session = Depends(get_db)):
    form = db.execute(select(CustomForm).where(CustomForm.id == form_id)).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    db.delete(form)
    db.commit()


# ── Submissions ────────────────────────────────────────────────────────────────

@router.post("/{form_id}/submit", response_model=FormSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_form(form_id: int, payload: FormSubmissionCreate, db: Session = Depends(get_db)):
    form = db.execute(select(CustomForm).where(CustomForm.id == form_id)).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if not form.is_active:
        raise HTTPException(status_code=400, detail="Form is not active")

    data = payload.model_dump()
    data["form_id"] = form_id  # ensure form_id from path takes precedence
    submission = FormSubmission(**data)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/{form_id}/submissions", response_model=list[FormSubmissionResponse])
def list_submissions(form_id: int, db: Session = Depends(get_db)):
    form = db.execute(select(CustomForm).where(CustomForm.id == form_id)).scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return db.execute(
        select(FormSubmission).where(FormSubmission.form_id == form_id)
    ).scalars().all()
