from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey
from core.database import Base
from datetime import datetime


class EmployeeConfirmation(Base):
    __tablename__ = "employee_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    probation_start_date = Column(Date, nullable=False)
    probation_end_date = Column(Date, nullable=False)
    confirmation_date = Column(Date, nullable=True)
    performance_rating = Column(String(20), nullable=True)   # EXCELLENT | GOOD | SATISFACTORY | POOR
    status = Column(String(50), nullable=False, server_default="PENDING")  # PENDING | CONFIRMED | EXTENDED | TERMINATED
    extended_till = Column(Date, nullable=True)
    remarks = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
