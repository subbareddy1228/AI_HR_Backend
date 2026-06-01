from sqlalchemy.orm import Session
from fastapi import HTTPException
from model.models import AIInterviewTemplate  
from schema.ai_interview import AIInterviewTemplateCreate, AIInterviewTemplateUpdate
from typing import List


def create_template(db: Session, data: AIInterviewTemplateCreate, user_id: int):
    # Convert Pydantic Question objects to dicts
    template_data = data.dict()
    if template_data.get('questions'):
        template_data['questions'] = [q if isinstance(q, dict) else q.dict() for q in template_data['questions']]
    
    # Add the authenticated user's ID
    template_data['created_by'] = user_id
    
    template = AIInterviewTemplate(**template_data)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template

def get_template(db: Session, template_id: int):
    return db.query(AIInterviewTemplate).filter(AIInterviewTemplate.id == template_id).first()

def list_templates(db: Session, user_id: int = None):
    """Get all AI interview templates, optionally filtered by user"""
    query = db.query(AIInterviewTemplate)
    if user_id:
        query = query.filter(AIInterviewTemplate.created_by == user_id)
    return query.order_by(AIInterviewTemplate.id.desc()).all()

def update_template(db: Session, template_id: int, data: AIInterviewTemplateUpdate):
    template = db.query(AIInterviewTemplate).filter(AIInterviewTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = data.dict(exclude_unset=True)  # ✅ only update provided fields
    
    # Convert questions to dicts if present
    if 'questions' in update_data and update_data['questions']:
        update_data['questions'] = [q if isinstance(q, dict) else q.dict() for q in update_data['questions']]
    
    for key, value in update_data.items():
        setattr(template, key, value)

    db.commit()
    db.refresh(template)
    return template

def delete_template(db: Session, template_id: int):
    template = db.query(AIInterviewTemplate).filter(AIInterviewTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()
    return {"message": "Template deleted successfully"}  # ✅ return JSON response
