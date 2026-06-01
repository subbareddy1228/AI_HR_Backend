from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schema.Company_Settings.financial_year import FinancialYearCreate, FinancialYearResponse
from services.Company_Settings.financial_year_service import create_or_update_financial_year, get_active_financial_year

router = APIRouter(prefix="/financial-year", tags=["Financial Year"])

@router.post("/", response_model=FinancialYearResponse)
def save_financial_year(payload: FinancialYearCreate, db: Session = Depends(get_db)):
    return create_or_update_financial_year(db, payload)

@router.get("/current", response_model=FinancialYearResponse)
def fetch_current_financial_year(db: Session = Depends(get_db)):
    return get_active_financial_year(db)
