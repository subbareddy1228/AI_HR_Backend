
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Date, Text,
    Boolean, DateTime, ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from core.database import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    company_name         = Column(String(255), nullable=False)
    company_type         = Column(String(100))          
    company_website      = Column(String(500))
    email                = Column(String(255))
    phone                = Column(String(50))
    address              = Column(Text)
    about_company        = Column(Text)
    registration_number  = Column(String(100))
    tax_id               = Column(String(100))
    vat_gst_number       = Column(String(100))
    industry             = Column(String(150))
    legal_entity_name    = Column(String(255))
    year_founded         = Column(Integer)
    registration_date    = Column(Date)
    registration_authority = Column(String(255))
    incorporation_number = Column(String(100))
    logo_path            = Column(String(500))
    logo_original_name   = Column(String(255))
    logo_size_bytes      = Column(Integer)             
    created_at           = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at           = Column(DateTime, default=datetime.utcnow,
                                  onupdate=datetime.utcnow, nullable=False)
    updated_by           = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_deleted           = Column(Boolean, default=False, nullable=False)
    deleted_at           = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_company_profile_tenant", "tenant_id", "is_deleted"),
    )
