from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from model.HR_Automation.holiday import Holiday
from schema.HR_Automation.holiday import HolidayCreate, HolidayUpdate, HolidayResponse

router = APIRouter(prefix="/holidays", tags=["Holiday Calendar"])


@router.post("/", response_model=HolidayResponse, status_code=201)
def create_holiday(payload: HolidayCreate, db: Session = Depends(get_db)):
    existing = db.query(Holiday).filter(Holiday.holiday_date == payload.holiday_date).first()
    if existing:
        raise HTTPException(status_code=400, detail="A holiday already exists on this date")
    holiday = Holiday(**payload.model_dump())
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return holiday


@router.get("/", response_model=List[HolidayResponse])
def list_holidays(
    year: Optional[int] = Query(None),
    holiday_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Holiday).filter(Holiday.is_active == True)
    if year:
        from sqlalchemy import extract
        query = query.filter(extract("year", Holiday.holiday_date) == year)
    if holiday_type:
        query = query.filter(Holiday.holiday_type == holiday_type)
    return query.order_by(Holiday.holiday_date).all()


@router.get("/{holiday_id}", response_model=HolidayResponse)
def get_holiday(holiday_id: int, db: Session = Depends(get_db)):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    return holiday


@router.patch("/{holiday_id}", response_model=HolidayResponse)
def update_holiday(holiday_id: int, payload: HolidayUpdate, db: Session = Depends(get_db)):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(holiday, key, value)
    db.commit()
    db.refresh(holiday)
    return holiday


@router.delete("/{holiday_id}")
def delete_holiday(holiday_id: int, db: Session = Depends(get_db)):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    db.delete(holiday)
    db.commit()
    return {"message": "Holiday deleted successfully"}
