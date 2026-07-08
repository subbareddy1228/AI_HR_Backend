from sqlalchemy.orm import Session
from model.onboarding.contact_details import ContactDetails
from schema.onboarding.contact_details import ContactDetailsCreate


def create_contact_details(db: Session, data: ContactDetailsCreate):
    record = ContactDetails(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_contact_details(db: Session, record_id: int):
    return db.query(ContactDetails).filter(ContactDetails.id == record_id).first()
