from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from datetime import datetime
from core.database import Base

class CurrencySetting(Base):
    __tablename__ = "currency_settings"
    id = Column(Integer, primary_key=True)
    primary_currency = Column(String(10), nullable=False)
    secondary_currency = Column(String(10))
    multi_currency_enabled = Column(Boolean, default=False)
    auto_update = Column(Boolean, default=False)
    update_frequency = Column(String(20))
    last_updated = Column(DateTime, default=datetime.utcnow)

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    id = Column(Integer, primary_key=True)
    from_currency = Column(String(10), nullable=False)
    to_currency = Column(String(10), nullable=False)
    rate = Column(Float, nullable=False)
    effective_date = Column(DateTime)
    status = Column(String(20), default="active")
    last_updated = Column(DateTime, default=datetime.utcnow)
