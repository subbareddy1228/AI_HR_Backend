# backend/services/assessment_service.py
from sqlalchemy.orm import Session
from schema.assessment import AssessmentCreate   # absolute import
from model.models import Assessment, User
from typing import Optional
 # instead of 'app.schemas.assessment'

def create_assessment(db: Session, data: AssessmentCreate):
    assessment = Assessment(**data.dict())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment

def get_assessments(db: Session, skill: str = None, difficulty: str = None, role: str = None, user: Optional[User] = None):
    query = db.query(Assessment)
    
    # Filter by recruiter (unless admin)
    if user and user.role.lower() != "admin":
        query = query.filter(Assessment.created_by == user.id)
    
    if skill:
        query = query.filter(Assessment.skill == skill)
    if difficulty:
        query = query.filter(Assessment.difficulty == difficulty)
    if role:
        query = query.filter(Assessment.role == role)
    return query.all()

def get_assessment(db: Session, assessment_id: int):
    return db.query(Assessment).filter(Assessment.id == assessment_id).first()

def update_assessment(db: Session, assessment_id: int, data: dict):
    db.query(Assessment).filter(Assessment.id == assessment_id).update(data)
    db.commit()
    return get_assessment(db, assessment_id)

def delete_assessment(db: Session, assessment_id: int):
    db.query(Assessment).filter(Assessment.id == assessment_id).delete()
    db.commit()
