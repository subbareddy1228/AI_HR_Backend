

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Date, Text, Boolean,
    DateTime, ForeignKey, Index, BigInteger,
)
from core.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id                  = Column(Integer, primary_key=True, index=True)
    tenant_id           = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    
    title               = Column(String(255), nullable=False)
    category            = Column(String(100), nullable=False)   
    version             = Column(String(20), nullable=False)    
    effective_date      = Column(Date, nullable=False)
    status              = Column(String(50), default="Draft", nullable=False)   
    description         = Column(Text)

    document_path       = Column(String(500))
    document_original_name = Column(String(255))
    document_size_bytes = Column(BigInteger)                    

    
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow,
                                  onupdate=datetime.utcnow, nullable=False)
    updated_by          = Column(Integer, ForeignKey("users.id"), nullable=True)

   
    is_deleted          = Column(Boolean, default=False, nullable=False)
    deleted_at          = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_policy_tenant_status", "tenant_id", "status", "is_deleted"),
    )
