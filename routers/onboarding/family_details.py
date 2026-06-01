from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schema.onboarding.family_details import FamilyDetailsCreate, FamilyDetailsResponse
from services.family_details_service import create_family_details

router = APIRouter(prefix="/family-details", tags=["Family Details"])

@router.post("/", response_model=FamilyDetailsResponse)
def submit_family_details(payload: FamilyDetailsCreate, db: Session = Depends(get_db)):
    return create_family_details(db, payload)
