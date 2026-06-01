from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from model.HR_Operations.promotion import Promotion
from schema.HR_Operations.promotion import (
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
)

router = APIRouter(prefix="/promotions", tags=["Promotions"])


@router.post("/", response_model=PromotionResponse)
def create_promotion(payload: PromotionCreate, db: Session = Depends(get_db)):
    record = Promotion(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[PromotionResponse])
def list_promotions(db: Session = Depends(get_db)):
    return db.query(Promotion).order_by(Promotion.created_at.desc()).all()


@router.get("/{promotion_id}", response_model=PromotionResponse)
def get_promotion(promotion_id: int, db: Session = Depends(get_db)):
    record = db.query(Promotion).filter(Promotion.id == promotion_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Promotion record not found")
    return record


@router.patch("/{promotion_id}", response_model=PromotionResponse)
def update_promotion(promotion_id: int, payload: PromotionUpdate, db: Session = Depends(get_db)):
    record = db.query(Promotion).filter(Promotion.id == promotion_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Promotion record not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{promotion_id}")
def delete_promotion(promotion_id: int, db: Session = Depends(get_db)):
    record = db.query(Promotion).filter(Promotion.id == promotion_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Promotion record not found")
    db.delete(record)
    db.commit()
    return {"message": "Promotion record deleted successfully"}
