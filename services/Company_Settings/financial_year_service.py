from sqlalchemy.orm import Session
from model.Company_Settings.financial_year import FinancialYear
from utils.date_utils import calculate_financial_year

MONTH_MAP = {
    "January": 1, "February": 2, "March": 3,
    "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9,
    "October": 10, "November": 11, "December": 12
}

def create_or_update_financial_year(db: Session, data):
    start_month_num = MONTH_MAP[data.start_month]
    current, previous, next_ = calculate_financial_year(start_month_num)
    db.query(FinancialYear).update({FinancialYear.is_active: False})

    fy = FinancialYear(
        **data.dict(),
        current_year=current,
        previous_year=previous,
        next_year=next_,
        is_active=True
    )
    db.add(fy)
    db.commit()
    db.refresh(fy)
    return fy

def get_active_financial_year(db: Session):
    return db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
