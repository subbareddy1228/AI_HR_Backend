

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, UniqueConstraint,
)
from core.database import Base


class FinancialYear(Base):
    __tablename__ = "financial_years"

    id                  = Column(Integer, primary_key=True, index=True)
    tenant_id           = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

   
    start_month         = Column(String(20), nullable=False)    
    start_day           = Column(Integer, nullable=False)        
    end_month           = Column(String(20), nullable=False)    
    end_day             = Column(Integer, nullable=False)        
    period_type         = Column(String(50), nullable=False)    
    tax_year_alignment  = Column(String(50), nullable=False)    

   
    current_year        = Column(String(20), nullable=False)    
    previous_year       = Column(String(20), nullable=False)    
    next_year           = Column(String(20), nullable=False)    

   
    is_active           = Column(Boolean, default=True, nullable=False)

    
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by          = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "current_year", name="uq_fy_tenant_year"),
    )
