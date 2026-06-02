from sqlalchemy.orm import Session
from model.onboarding.present_address import PresentAddress
from schema.onboarding.present_address import PresentAddressBase, PresentAddressCreate
from utils.validators import validate_pincode

def create_present_address(db: Session, data: PresentAddressCreate):
    validate_pincode(data.pincode)
    address = PresentAddress(**data.dict())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address

def get_present_address(db: Session, address_id: int):
    return db.query(PresentAddress).filter(PresentAddress.id == address_id).first()



