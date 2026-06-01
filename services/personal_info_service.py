from sqlalchemy.orm import Session
from model.onboarding.personal_info import PersonalInfo

def create_personal_info(db: Session, data):
    record = PersonalInfo(**data.dict())
    db.add(record)
    db.commit()
    return record
