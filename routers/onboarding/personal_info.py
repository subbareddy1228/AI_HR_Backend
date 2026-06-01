from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schema.onboarding.personal_info import PersonalInfoCreate
from services.personal_info_service import create_personal_info

router = APIRouter(prefix="/personal-info",tags=["Personal Info"])

@router.post("/")
def create(data: PersonalInfoCreate, db: Session = Depends(get_db)):
    return create_personal_info(db, data)
