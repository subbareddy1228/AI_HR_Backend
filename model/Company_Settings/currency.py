

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Float,
    DateTime, ForeignKey, UniqueConstraint, Index,
)
from core.database import Base


class CurrencySetting(Base):
    __tablename__ = "currency_settings"

    id                      = Column(Integer, primary_key=True, index=True)
    tenant_id               = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    primary_currency        = Column(String(10), nullable=False)
    secondary_currency      = Column(String(10))
    multi_currency_enabled  = Column(Boolean, default=False, nullable=False)
    auto_update             = Column(Boolean, default=False, nullable=False)
    update_frequency        = Column(String(20))        

  
    last_updated            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at              = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by              = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_currency_settings_tenant"),
    )


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id              = Column(Integer, primary_key=True, index=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    from_currency   = Column(String(10), nullable=False)
    to_currency     = Column(String(10), nullable=False)
    rate            = Column(Float, nullable=False)
    effective_date  = Column(DateTime, nullable=False)
    status          = Column(String(20), default="active")  
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by      = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "from_currency", "to_currency",
                         name="uq_exchange_rate_pair"),
        Index("ix_exchange_rate_tenant_status", "tenant_id", "status"),
    )
