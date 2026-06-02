from sqlalchemy.orm import Session
from fastapi import HTTPException
from schema.onboarding.statutory import StatutoryCreate
from model.onboarding.statutory import StatutoryDetails
from schema.onboarding.statutory import StatutoryResponse
from utils.validators import validate_pan, validate_aadhaar

def create_statutory_details(db: Session, data: StatutoryCreate):
    if not validate_pan(data.pan_number):
        raise HTTPException(status_code=400, detail="Invalid PAN")

    if not validate_aadhaar(data.aadhaar_number):
        raise HTTPException(status_code=400, detail="Invalid Aadhaar")

    obj = StatutoryDetails(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
