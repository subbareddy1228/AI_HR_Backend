from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from model.onboarding.onboarding import OnboardingForm
from schema.onboarding.onboarding import OnboardingCreate

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

@router.post("/")
def submit_onboarding(data: OnboardingCreate, db: Session = Depends(get_db)):
    form = OnboardingForm(**data.dict(), status="SUBMITTED")
    db.add(form)
    db.commit()
    db.refresh(form)
    return form
