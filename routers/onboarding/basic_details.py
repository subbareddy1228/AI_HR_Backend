from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from schema.onboarding.basic_details import BasicDetailsCreate, BasicDetailsResponse
from services.basic_details_service import create_basic_details, get_basic_details

router = APIRouter(prefix="/basic-details", tags=["Basic Details"])


@router.post("/", response_model=BasicDetailsResponse)
def submit_basic_details(payload: BasicDetailsCreate, db: Session = Depends(get_db)):
    return create_basic_details(db, payload)


@router.get("/{record_id}", response_model=BasicDetailsResponse)
def read_basic_details(record_id: int, db: Session = Depends(get_db)):
    record = get_basic_details(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Basic details not found")
    return record
