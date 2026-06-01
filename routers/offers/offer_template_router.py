from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_user
from model.models import User
from .services.offer_template_service import (create_offer_template,get_offer_templates,get_offer_template,update_offer_template,delete_offer_template)
from schema.offer_template import OfferTemplateCreate, OfferTemplateOut, OfferTemplateUpdate
from typing import List, Optional

router = APIRouter(prefix="/offer-templates", tags=["Offer Templates"])

@router.post("/", response_model=OfferTemplateOut)
def create_template(data: OfferTemplateCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Create a new offer template"""
    if not data.created_by:
        data.created_by = user.id
    return create_offer_template(db, data)

@router.get("/", response_model=List[OfferTemplateOut])
def list_templates(
    position: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get all offer templates with optional filters, filtered by recruiter"""
    return get_offer_templates(db, position, department, user)

@router.get("/{template_id}", response_model=OfferTemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get a specific offer template"""
    template = get_offer_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Offer template not found")
    
    if user.role.lower() != "admin" and template.created_by != user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    return template

@router.put("/{template_id}", response_model=OfferTemplateOut)
def update_template(
    template_id: int,
    data: OfferTemplateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Update an offer template"""
    template = get_offer_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Offer template not found")
    
    if user.role.lower() != "admin" and template.created_by != user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    update_dict = data.dict(exclude_unset=True)
    updated = update_offer_template(db, template_id, update_dict)
    if not updated:
        raise HTTPException(status_code=404, detail="Offer template not found")
    return updated

@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete an offer template"""
    template = get_offer_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Offer template not found")

    if user.role.lower() != "admin" and template.created_by != user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    success = delete_offer_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Offer template not found")
    return {"message": "Offer template deleted successfully"}

