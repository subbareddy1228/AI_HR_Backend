from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from model.HR_Operations.letter_generation import LetterGeneration
from schema.HR_Operations.letter_generation import (
    LetterGenerationCreate,
    LetterGenerationUpdate,
    LetterGenerationResponse,
)

router = APIRouter(prefix="/letter-generation", tags=["Letter Generation"])


@router.post("/", response_model=LetterGenerationResponse)
def create_letter(payload: LetterGenerationCreate, db: Session = Depends(get_db)):
    record = LetterGeneration(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[LetterGenerationResponse])
def list_letters(db: Session = Depends(get_db)):
    return db.query(LetterGeneration).order_by(LetterGeneration.created_at.desc()).all()


@router.get("/{letter_id}", response_model=LetterGenerationResponse)
def get_letter(letter_id: int, db: Session = Depends(get_db)):
    record = db.query(LetterGeneration).filter(LetterGeneration.id == letter_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Letter not found")
    return record


@router.patch("/{letter_id}", response_model=LetterGenerationResponse)
def update_letter(letter_id: int, payload: LetterGenerationUpdate, db: Session = Depends(get_db)):
    record = db.query(LetterGeneration).filter(LetterGeneration.id == letter_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Letter not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{letter_id}")
def delete_letter(letter_id: int, db: Session = Depends(get_db)):
    record = db.query(LetterGeneration).filter(LetterGeneration.id == letter_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Letter not found")
    db.delete(record)
    db.commit()
    return {"message": "Letter deleted successfully"}
