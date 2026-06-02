from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from core.database import get_db

# Import ALL schema classes directly
from schema.deal import DealOut
from schema.lead import LeadRead
from schema.contact import ContactBase
from schema.company import CompanyBase
from schema.activity import Activity

import crud_ops
import model

router = APIRouter()

# Deals Analytics
@router.get("/deals", response_model=List[DealOut])
def list_deals(db: Session = Depends(get_db), q: Optional[str] = None):
    query = db.query(model.Deal)
    if q:
        query = query.filter(model.Deal.deal_name.ilike(f"%{q}%"))
    return query.all()

@router.get("/deals/{deal_id}", response_model=DealOut)
def get_deal(deal_id: int, db: Session = Depends(get_db)):
    deal = db.query(model.Deal).filter(model.Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal

# Leads Analytics
@router.get("/leads", response_model=List[LeadRead])
def read_leads(skip: int = 0, limit: int = Query(100, le=1000), db: Session = Depends(get_db)):
    return crud_ops.get_leads(db, skip=skip, limit=limit)


@router.get("/leads/{lead_id}", response_model=LeadRead)
def read_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = crud_ops.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

# Contacts Analytics
@router.get("/recent-contacts", response_model=List[ContactBase])
def recent_contacts(limit: int = 10, db: Session = Depends(get_db)):
    if hasattr(model.Contact, "created_at"):
        return (
            db.query(model.Contact)
            .order_by(model.Contact.created_at.desc())
            .limit(limit)
            .all()
        )
    return db.query(model.Contact).limit(limit).all()

# Companies Analytics
@router.get("/recent-companies", response_model=List[CompanyBase])
def recent_companies(limit: int = 10, db: Session = Depends(get_db)):
    if hasattr(model.Company, "created_at"):
        return (
            db.query(model.Company)
            .order_by(model.Company.created_at.desc())
            .limit(limit)
            .all()
        )
    return db.query(model.Company).limit(limit).all()

# Activities Analytics
@router.get("/activities", response_model=List[Activity])
def read_activities(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return crud_ops.get_activities(db, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-activities", response_model=List[Activity])
def recent_activities(limit: int = 10, db: Session = Depends(get_db)):
    if hasattr(model.Activity, "created_at"):
        return (
            db.query(model.Activity)
            .order_by(model.Activity.created_at.desc())
            .limit(limit)
            .all()
        )
    return db.query(model.Activity).limit(limit).all()
