

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Index, Text,
)
from core.database import Base


class CompanyLocation(Base):
    __tablename__ = "company_locations"

    id              = Column(Integer, primary_key=True, index=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

 
    name            = Column(String(255), nullable=False)   
    address         = Column(Text)
    city            = Column(String(100))
    state           = Column(String(100))
    country         = Column(String(100))
    postal_code     = Column(String(20))
    latitude        = Column(String(30))                   
    longitude       = Column(String(30))

    timezone        = Column(String(100), nullable=False)   
    working_hours_start = Column(String(10))                
    working_hours_end   = Column(String(10))                

   
    weekend_days    = Column(String(100))

   
    is_default      = Column(Boolean, default=False, nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)

    
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by      = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("ix_location_tenant_active", "tenant_id", "is_active"),
    )
