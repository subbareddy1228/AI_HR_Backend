from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from core.database import Base
from datetime import datetime


class HRHelpdesk(Base):
    __tablename__ = "hr_helpdesk"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False)   # PAYROLL | LEAVE | POLICY | ONBOARDING | OTHER
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, server_default="MEDIUM")  # LOW | MEDIUM | HIGH | URGENT
    status = Column(String(50), nullable=False, server_default="OPEN")      # OPEN | IN_PROGRESS | RESOLVED | CLOSED
    assigned_to = Column(Integer, ForeignKey("employees.id"), nullable=True)
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
