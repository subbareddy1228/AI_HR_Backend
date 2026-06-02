from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, Text
from core.database import Base
from datetime import datetime


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    holiday_name = Column(String(255), nullable=False)
    holiday_date = Column(Date, nullable=False, unique=True)
    holiday_type = Column(String(50), nullable=False)   # NATIONAL | REGIONAL | OPTIONAL | RESTRICTED
    description = Column(Text, nullable=True)
    applicable_location = Column(String(150), nullable=True)   # NULL = all locations
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
