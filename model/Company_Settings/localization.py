

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, UniqueConstraint,
)
from core.database import Base


class LocalizationPreference(Base):
    __tablename__ = "localization_preferences"

    id                  = Column(Integer, primary_key=True, index=True)
    tenant_id           = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

  
    default_language    = Column(String(50), nullable=False)    
    default_timezone    = Column(String(100), nullable=False)   
    date_format         = Column(String(30), nullable=False)    
    time_format         = Column(String(30), nullable=False)    
    number_format       = Column(String(30), nullable=False)    
    decimal_places      = Column(Integer, nullable=False, default=2)
    currency_format     = Column(String(30), nullable=False)   
    first_day_of_week   = Column(String(15), nullable=False)    

    is_active           = Column(Boolean, default=True, nullable=False)

   
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by          = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_localization_tenant"),
    )
