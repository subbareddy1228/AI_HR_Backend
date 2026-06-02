from sqlalchemy.orm import Session
from model.Company_Settings.currency import CurrencySetting, ExchangeRate

def save_settings(db: Session, data):
    setting = CurrencySetting(**data.dict())
    db.add(setting)
    db.commit()
    return setting

def add_rate(db: Session, data):
    rate = ExchangeRate(**data.dict())
    db.add(rate)
    db.commit()
    return rate

def update_rate(db: Session, rate_id: int, data):
    rate = db.query(ExchangeRate).get(rate_id)
    if not rate:
        return None
    for k, v in data.dict().items():
        setattr(rate, k, v)
    db.commit()
    return rate
