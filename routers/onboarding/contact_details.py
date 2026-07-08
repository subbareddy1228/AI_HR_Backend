from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from schema.onboarding.contact_details import ContactDetailsCreate, ContactDetailsResponse
from services.contact_details_service import create_contact_details, get_contact_details

router = APIRouter(prefix="/contact-details", tags=["Contact Details"])


@router.post("/", response_model=ContactDetailsResponse)
def submit_contact_details(payload: ContactDetailsCreate, db: Session = Depends(get_db)):
    return create_contact_details(db, payload)


@router.get("/{record_id}", response_model=ContactDetailsResponse)
def read_contact_details(record_id: int, db: Session = Depends(get_db)):
    record = get_contact_details(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Contact details not found")
    return record
