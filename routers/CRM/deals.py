from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from core.dependencies import get_current_user
from model.models import User
from model import Deal
from schema.deal import DealCreate, DealUpdate, DealOut

router = APIRouter()


@router.post("/", response_model=DealOut, status_code=201)
def create_deal(payload: DealCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new deal."""
    deal = Deal(**payload.model_dump(), tenant_id=current_user.tenant_id)
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@router.get("/", response_model=List[DealOut])
def list_deals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), q: Optional[str] = None):
    """Get all deals for the current company, optionally filter by deal_name."""
    query = db.query(Deal)
    if current_user.tenant_id is not None:
        query = query.filter(Deal.tenant_id == current_user.tenant_id)
    if q:
        query = query.filter(Deal.deal_name.ilike(f"%{q}%"))
    return query.all()


def _get_scoped_deal(db: Session, deal_id: int, current_user: User) -> Deal:
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal or (current_user.tenant_id is not None and deal.tenant_id != current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(deal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch a deal by ID, scoped to the current company."""
    return _get_scoped_deal(db, deal_id, current_user)


@router.patch("/{deal_id}", response_model=DealOut)
def update_deal(deal_id: int, payload: DealUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update an existing deal, scoped to the current company."""
    deal = _get_scoped_deal(db, deal_id, current_user)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(deal, key, value)

    db.commit()
    db.refresh(deal)
    return deal


@router.delete("/{deal_id}", status_code=204, response_class=Response)
def delete_deal(deal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a deal by ID, scoped to the current company."""
    deal = _get_scoped_deal(db, deal_id, current_user)
    db.delete(deal)
    db.commit()
    return Response(status_code=204)