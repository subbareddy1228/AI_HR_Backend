from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey
from core.database import Base
from datetime import datetime


class LetterGeneration(Base):
    __tablename__ = "letter_generation"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    letter_type = Column(String(100), nullable=False)   # OFFER | APPOINTMENT | CONFIRMATION | RELIEVING | EXPERIENCE | SALARY | WARNING | TERMINATION
    letter_date = Column(Date, nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    generated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    status = Column(String(50), nullable=False, server_default="DRAFT")  # DRAFT | ISSUED | REVOKED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
