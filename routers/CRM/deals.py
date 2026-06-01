from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db 
from model import Deal
from schema.deal import  DealCreate, DealUpdate, DealOut
import crud_ops

router = APIRouter()


#  Create a deal
@router.post("/", response_model=DealOut, status_code=201)
def create_deal(payload: DealCreate, db: Session = Depends(get_db)):
    """Create a new deal."""
    deal = Deal(**payload.model_dump())
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal

#  List all deals (with optional search)
@router.get("/", response_model=List[DealOut])
def list_deals(db: Session = Depends(get_db), q: Optional[str] = None):
    """Get all deals, optionally filter by deal_name."""
    query = db.query(Deal)
    if q:
        query = query.filter(Deal.deal_name.ilike(f"%{q}%"))
    return query.all()

#  Get a single deal
@router.get("/{deal_id}", response_model=DealOut)
def get_deal(deal_id: int, db: Session = Depends(get_db)):
    """Fetch a deal by ID."""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal

#  Update a deal
@router.patch("/{deal_id}", response_model=DealOut)
def update_deal(deal_id: int, payload: DealUpdate, db: Session = Depends(get_db)):
    """Update an existing deal."""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(deal, key, value)

    db.commit()
    db.refresh(deal)
    return deal

#  Delete a deal
@router.delete("/{deal_id}", status_code=204, response_class=Response)
def delete_deal(deal_id: int, db: Session = Depends(get_db)):
    """Delete a deal by ID."""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    db.delete(deal)
    db.commit()
    return Response(status_code=204)
