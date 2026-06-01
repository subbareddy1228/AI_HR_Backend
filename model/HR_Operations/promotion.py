from sqlalchemy import Column, Integer, String, Date, Text, DateTime, Numeric, ForeignKey
from core.database import Base
from datetime import datetime


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    from_designation = Column(String(150), nullable=False)
    to_designation = Column(String(150), nullable=False)
    from_grade = Column(String(50), nullable=True)
    to_grade = Column(String(50), nullable=True)
    effective_date = Column(Date, nullable=False)
    revised_salary = Column(Numeric(12, 2), nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, server_default="PENDING")  # PENDING | APPROVED | REJECTED
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
