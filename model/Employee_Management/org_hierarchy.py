
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float
from core.database import Base
from datetime import datetime
 
 
class Department(Base):
    __tablename__ = "departments"
 
    id                    = Column(Integer, primary_key=True, index=True)
    name                  = Column(String(255), unique=True, nullable=False)
    code                  = Column(String(50), unique=True, nullable=True)
    parent_department_id  = Column(Integer, ForeignKey("departments.id"), nullable=True)
    head_employee_id      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    description           = Column(Text, nullable=True)
    location              = Column(String(255), nullable=True)
    is_active             = Column(Boolean, default=True)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
 
class ReportingRelationship(Base):
   
    __tablename__ = "reporting_relationships"
 
    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False)
    manager_id      = Column(Integer, ForeignKey("employees.id"), nullable=False)
    # DIRECT | DOTTED_LINE | MATRIX
    relationship_type = Column(String(50), nullable=False, default="DIRECT")
    effective_date  = Column(DateTime, nullable=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
 
class HierarchyChangeRequest(Base):
   
    __tablename__ = "hierarchy_change_requests"
 
    id              = Column(Integer, primary_key=True, index=True)
    requested_by    = Column(Integer, ForeignKey("employees.id"), nullable=False)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False)
    change_type     = Column(String(100), nullable=False)   # DEPARTMENT_CHANGE | MANAGER_CHANGE | DESIGNATION_CHANGE
    from_value      = Column(String(255), nullable=True)
    to_value        = Column(String(255), nullable=True)
    # PENDING | APPROVED | REJECTED
    status          = Column(String(50), nullable=False, default="PENDING")
    remarks         = Column(Text, nullable=True)
    approved_by     = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
 
class HierarchyHistory(Base):
   
    __tablename__ = "hierarchy_history"
 
    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False)
    department_id   = Column(Integer, ForeignKey("departments.id"), nullable=True)
    manager_id      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    designation     = Column(String(255), nullable=True)
    location        = Column(String(255), nullable=True)
    effective_from  = Column(DateTime, nullable=False)
    effective_to    = Column(DateTime, nullable=True)   # NULL means current record
    changed_by      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)