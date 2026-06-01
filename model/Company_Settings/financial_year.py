from sqlalchemy import Column, Integer, String, Boolean
from core.database import Base

class FinancialYear(Base):
    __tablename__ = "financial_years"

    id = Column(Integer, primary_key=True, index=True)
    start_month = Column(String, nullable=False)
    start_day = Column(Integer, nullable=False)
    end_month = Column(String, nullable=False)
    end_day = Column(Integer, nullable=False)
    period_type = Column(String, nullable=False)
    tax_year_alignment = Column(String, nullable=False)
    current_year = Column(String, nullable=False)
    previous_year = Column(String, nullable=False)
    next_year = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
