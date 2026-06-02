from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from core.dependencies import get_db
from core.config import settings
from utils.file_utils import save_file
from model.Company_Settings.policy import Policy
from schema.Company_Settings.policy import PolicyResponse

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.post("/", response_model=PolicyResponse)
def add_policy(
    title: str = Form(...),
    category: str = Form(...),
    version: str = Form(...),
    effective_date: date = Form(...),
    description: Optional[str] = Form(None),
    document: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    document_path = save_file(document, settings.UPLOAD_DIR) if document else None

    policy = Policy(
        title=title,
        category=category,
        version=version,
        effective_date=effective_date,
        description=description,
        document_path=document_path,
        status="Active"
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.put("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: int,
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    effective_date: Optional[date] = Form(None),
    description: Optional[str] = Form(None),
    document: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if title is not None:
        policy.title = title
    if category is not None:
        policy.category = category
    if version is not None:
        policy.version = version
    if effective_date is not None:
        policy.effective_date = effective_date
    if description is not None:
        policy.description = description
    if document:
        policy.document_path = save_file(document, settings.UPLOAD_DIR)

    db.commit()
    db.refresh(policy)
    return policy
