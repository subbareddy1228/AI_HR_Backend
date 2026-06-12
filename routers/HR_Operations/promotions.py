from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from core.database import get_db
from model.HR_Operations.promotion import Promotion
from schema.HR_Operations.promotion import (
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
)

router = APIRouter(prefix="/api/hr-operations/promotions", tags=["HR Operations - Promotions"])


# ──────────────────────────────────────────────
# CREATE Promotion
# ──────────────────────────────────────────────
@router.post("/", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
def create_promotion(payload: PromotionCreate, db: Session = Depends(get_db)):
    """Initiate a promotion request for an employee."""
    promotion = Promotion(**payload.model_dump())
    db.add(promotion)
    db.commit()
    db.refresh(promotion)
    return promotion


# ──────────────────────────────────────────────
# LIST ALL Promotions
# ──────────────────────────────────────────────
@router.get("/", response_model=List[PromotionResponse])
def list_promotions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Retrieve all promotion records, newest first."""
    promotions = (
        db.query(Promotion)
        .order_by(Promotion.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return promotions


# ──────────────────────────────────────────────
# GET Promotion by Employee ID
# ──────────────────────────────────────────────
@router.get("/employee/{employee_id}", response_model=List[PromotionResponse])
def get_promotions_by_employee(employee_id: int, db: Session = Depends(get_db)):
    """Retrieve all promotions for a specific employee."""
    promotions = (
        db.query(Promotion)
        .filter(Promotion.employee_id == employee_id)
        .order_by(Promotion.created_at.desc())
        .all()
    )
    return promotions


# ──────────────────────────────────────────────
# GET Promotion by ID
# ──────────────────────────────────────────────
@router.get("/{promotion_id}", response_model=PromotionResponse)
def get_promotion(promotion_id: int, db: Session = Depends(get_db)):
    """Retrieve a single promotion record by ID."""
    promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion record not found")
    return promotion


# ──────────────────────────────────────────────
# UPDATE Promotion (approve / reject / remarks)
# ──────────────────────────────────────────────
@router.patch("/{promotion_id}", response_model=PromotionResponse)
def update_promotion(
    promotion_id: int,
    payload: PromotionUpdate,
    db: Session = Depends(get_db),
):
    """Update promotion status, approver, salary or remarks."""
    promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion record not found")

    valid_statuses = {"PENDING", "APPROVED", "REJECTED"}
    if payload.status and payload.status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {valid_statuses}",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(promotion, field, value)

    promotion.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(promotion)
    return promotion


# ──────────────────────────────────────────────
# DELETE Promotion
# ──────────────────────────────────────────────
@router.delete("/{promotion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_promotion(promotion_id: int, db: Session = Depends(get_db)):
    """Delete a promotion record (only if still PENDING)."""
    promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion record not found")
    if promotion.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Only PENDING promotions can be deleted",
        )
    db.delete(promotion)
    db.commit()
