from sqlalchemy.orm import Session
from model.onboarding.address import PermanentAddress
from schema.onboarding.address import AddressCreate

def create_address(db: Session, address: AddressCreate):
    new_address = PermanentAddress(**address.dict())
    db.add(new_address)
    db.commit()
    db.refresh(new_address)
    return new_address

def get_address(db: Session, address_id: int):
    return db.query(PermanentAddress).filter(PermanentAddress.id == address_id).first()
