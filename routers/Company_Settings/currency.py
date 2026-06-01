from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from schema.Company_Settings.currency import CurrencySettingCreate, ExchangeRateCreate, ExchangeRateUpdate
from services.Company_Settings.currency_service import save_settings, add_rate, update_rate

router = APIRouter(prefix="/currency", tags=["Currency"])

@router.post("/settings")
def save_currency_settings(data: CurrencySettingCreate, db: Session = Depends(get_db)):
    return save_settings(db, data)

@router.post("/rate")
def create_exchange_rate(data: ExchangeRateCreate, db: Session = Depends(get_db)):
    return add_rate(db, data)

@router.put("/rate/{rate_id}")
def edit_exchange_rate(rate_id: int, data: ExchangeRateUpdate, db: Session = Depends(get_db)):
    rate = update_rate(db, rate_id, data)
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")
    return rate
