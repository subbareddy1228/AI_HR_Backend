from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schema.Company_Settings.localization import LocalizationCreate, LocalizationResponse
from services.Company_Settings.localization_service import create_localization, get_localization
from core.dependencies import get_db

router = APIRouter(prefix="/localization",tags=["Localization"])

@router.post("/", response_model=LocalizationResponse)
def create(payload: LocalizationCreate, db: Session = Depends(get_db)):
    return create_localization(db, payload)

@router.get("/", response_model=LocalizationResponse)
def read(db: Session = Depends(get_db)):
    return get_localization(db)
