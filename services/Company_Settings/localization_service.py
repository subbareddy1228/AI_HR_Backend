from sqlalchemy.orm import Session
from model.Company_Settings.localization import LocalizationPreference

def create_localization(db: Session, data):
    obj = LocalizationPreference(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_localization(db: Session):
    return db.query(LocalizationPreference).first()
