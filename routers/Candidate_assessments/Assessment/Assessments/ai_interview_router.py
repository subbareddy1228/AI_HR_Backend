from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from schema.ai_interview import (
    AIInterviewTemplateCreate,
    AIInterviewTemplateUpdate,
    AIInterviewTemplateOut,
)
from routers.Candidate_assessments.Assessment.Assessments.services import ai_interview_service
from core.dependencies import get_current_user
from model.models import User
from typing import List


router = APIRouter(prefix="/ai-interviews", tags=["AI Interviews"])

@router.get("/", response_model=List[AIInterviewTemplateOut])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all AI interview templates"""
    return ai_interview_service.list_templates(db, current_user.id)

@router.post("/", response_model=AIInterviewTemplateOut)
def create_template(
    data: AIInterviewTemplateCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ai_interview_service.create_template(db, data, current_user.id)

@router.get("/{template_id}", response_model=AIInterviewTemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db)):
    template = ai_interview_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.put("/{template_id}", response_model=AIInterviewTemplateOut)
def update_template(template_id: int, data: AIInterviewTemplateUpdate, db: Session = Depends(get_db)):
    return ai_interview_service.update_template(db, template_id, data)

@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    return ai_interview_service.delete_template(db, template_id)
