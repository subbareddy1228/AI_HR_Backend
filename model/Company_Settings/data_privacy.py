
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date,
    ForeignKey, UniqueConstraint,
)
from core.database import Base


class DataPrivacySetting(Base):
    __tablename__ = "data_privacy_settings"

    id                              = Column(Integer, primary_key=True, index=True)
    tenant_id                       = Column(Integer, ForeignKey("tenants.id"),
                                             nullable=False, index=True)


    data_retention_period_years     = Column(Integer, default=7, nullable=False)
    inactive_account_period_days    = Column(Integer, default=365, nullable=False)


    auto_delete_inactive_accounts   = Column(Boolean, default=True, nullable=False)
    gdpr_compliance_enabled         = Column(Boolean, default=True, nullable=False)
    require_data_processing_consent = Column(Boolean, default=True, nullable=False)
    allow_data_export               = Column(Boolean, default=True, nullable=False)    
    enable_data_anonymization       = Column(Boolean, default=False, nullable=False)    

  
    consent_marketing               = Column(Boolean, default=True, nullable=False)
    consent_data_sharing            = Column(Boolean, default=True, nullable=False)
    consent_analytics               = Column(Boolean, default=True, nullable=False)
    consent_third_party             = Column(Boolean, default=True, nullable=False)
    consent_profiling               = Column(Boolean, default=False, nullable=False)
    consent_automated_decisions     = Column(Boolean, default=False, nullable=False)

  
    privacy_policy_version          = Column(String(20), nullable=False, default="1.0")
    last_consent_update             = Column(Date, nullable=True)
    privacy_policy_url              = Column(String(500), nullable=True)


    created_at                      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at                      = Column(DateTime, default=datetime.utcnow,
                                             onupdate=datetime.utcnow, nullable=False)
    updated_by                      = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_data_privacy_tenant"),
    )
