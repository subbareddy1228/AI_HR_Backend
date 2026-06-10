
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean,
    Text, ForeignKey, Date, Numeric
)
from core.database import Base
from datetime import datetime


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"

    id = Column(Integer, primary_key=True, index=True)
    employee_id   = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    document_name = Column(String(255), nullable=False)                
    document_type = Column(String(100), nullable=False)                
    category      = Column(String(50), nullable=False, server_default="Other")
    is_mandatory  = Column(Boolean, nullable=False, default=False)
    file_path     = Column(String(500), nullable=False)
    file_format   = Column(String(20),  nullable=True)   
    file_size_mb  = Column(Numeric(6, 2), nullable=True)  
    version       = Column(String(20), nullable=False, server_default="v1.0") 
    version_notes = Column(Text, nullable=True)
    upload_date   = Column(Date, nullable=True)          
    expiry_date   = Column(Date, nullable=True)          
    uploaded_at   = Column(DateTime, default=datetime.utcnow)
    status        = Column(String(30), nullable=False, server_default="PENDING")
    reviewed_by   = Column(Integer, ForeignKey("employees.id"), nullable=True)
    reviewed_at   = Column(DateTime, nullable=True)
    review_notes  = Column(Text, nullable=True)
    is_verified   = Column(Boolean, default=False)
    verified_by   = Column(String(255), nullable=True)
    notes         = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
