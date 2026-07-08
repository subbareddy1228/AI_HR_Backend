from sqlalchemy.orm import Session
from model.onboarding.basic_details import BasicDetails
from schema.onboarding.basic_details import BasicDetailsCreate


def create_basic_details(db: Session, data: BasicDetailsCreate):
    record = BasicDetails(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_basic_details(db: Session, record_id: int):
    return db.query(BasicDetails).filter(BasicDetails.id == record_id).first()
