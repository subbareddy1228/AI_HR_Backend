from sqlalchemy.orm import Session
from model.models import OfferTemplate, User
from schema.offer_template import OfferTemplateCreate, OfferTemplateUpdate
from datetime import datetime
from typing import List, Optional

def create_offer_template(db: Session, data: OfferTemplateCreate) -> OfferTemplate:
    """Create a new offer template"""
    template = OfferTemplate(**data.dict())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template

def get_offer_templates(
    db: Session,
    position: Optional[str] = None,
    department: Optional[str] = None,
    user: Optional[User] = None
) -> List[OfferTemplate]:
    """Get all offer templates with optional filters, filtered by recruiter"""
    query = db.query(OfferTemplate)
    
    # Filter by recruiter (unless admin)
    if user and user.role.lower() != "admin":
        query = query.filter(OfferTemplate.created_by == user.id)
    
    if position:
        query = query.filter(OfferTemplate.position.ilike(f"%{position}%"))
    if department:
        query = query.filter(OfferTemplate.department.ilike(f"%{department}%"))
    
    return query.order_by(OfferTemplate.created_at.desc()).all()

def get_offer_template(db: Session, template_id: int) -> Optional[OfferTemplate]:
    """Get a specific offer template by ID"""
    return db.query(OfferTemplate).filter(OfferTemplate.id == template_id).first()

def update_offer_template(
    db: Session,
    template_id: int,
    update_dict: dict
) -> Optional[OfferTemplate]:
    """Update an offer template"""
    template = get_offer_template(db, template_id)
    if not template:
        return None
    
    update_dict['updated_at'] = datetime.utcnow()
    
    for key, value in update_dict.items():
        setattr(template, key, value)
    
    db.commit()
    db.refresh(template)
    return template

def delete_offer_template(db: Session, template_id: int) -> bool:
    """Delete an offer template"""
    template = get_offer_template(db, template_id)
    if not template:
        return False
    
    db.delete(template)
    db.commit()
    return True

