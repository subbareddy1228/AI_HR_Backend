from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from model.HR_Operations.notice_period import NoticePeriod
from schema.HR_Operations.notice_period import (
    NoticePeriodCreate,
    NoticePeriodUpdate,
    NoticePeriodResponse,
)

router = APIRouter(prefix="/notice-period", tags=["Notice Period"])


@router.post("/", response_model=NoticePeriodResponse)
def create_notice_period(payload: NoticePeriodCreate, db: Session = Depends(get_db)):
    record = NoticePeriod(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[NoticePeriodResponse])
def list_notice_periods(db: Session = Depends(get_db)):
    return db.query(NoticePeriod).order_by(NoticePeriod.created_at.desc()).all()


@router.get("/{notice_id}", response_model=NoticePeriodResponse)
def get_notice_period(notice_id: int, db: Session = Depends(get_db)):
    record = db.query(NoticePeriod).filter(NoticePeriod.id == notice_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Notice period record not found")
    return record


@router.patch("/{notice_id}", response_model=NoticePeriodResponse)
def update_notice_period(notice_id: int, payload: NoticePeriodUpdate, db: Session = Depends(get_db)):
    record = db.query(NoticePeriod).filter(NoticePeriod.id == notice_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Notice period record not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{notice_id}")
def delete_notice_period(notice_id: int, db: Session = Depends(get_db)):
    record = db.query(NoticePeriod).filter(NoticePeriod.id == notice_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Notice period record not found")
    db.delete(record)
    db.commit()
    return {"message": "Notice period record deleted successfully"}
