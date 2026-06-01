from sqlalchemy.orm import Session
from model.onboarding import bank_details
from model.onboarding.bank_details import BankDetails
from schema.onboarding.bank_details import BankDetailsCreate

def create_bank_details(db: Session, data: BankDetailsCreate):
    bank = BankDetails(**data.dict())
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank
