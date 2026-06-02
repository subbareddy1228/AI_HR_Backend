from sqlalchemy import Column, Integer, String, DateTime, Text
from core.database import Base
from datetime import datetime


class HRRequest(Base):
    __tablename__ = "hr_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, nullable=True)
    request_type = Column(String(100), nullable=False)  # Certificate/Asset Request/Policy Clarification/Training/Other
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default="Medium")  # Low/Medium/High
    status = Column(String(50), default="Open")  # Open/In Progress/Resolved/Closed
    assigned_to = Column(String(100), nullable=True)
    response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
