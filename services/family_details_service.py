from sqlalchemy.orm import Session
from model.onboarding.family_details import FamilyDetails
from schema.onboarding.family_details import FamilyDetailsCreate

def create_family_details(db: Session, data: FamilyDetailsCreate):
    family = FamilyDetails(**data.dict())
    db.add(family)
    db.commit()
    db.refresh(family)
    return family
