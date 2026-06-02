from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schema.onboarding.statutory import StatutoryCreate, StatutoryResponse
from services.statutory_service import create_statutory_details

router = APIRouter(prefix="/statutory", tags=["Statutory Details"])

@router.post("/", response_model=StatutoryResponse)
def add_statutory(payload: StatutoryCreate, db: Session = Depends(get_db)):
    return create_statutory_details(db, payload)
