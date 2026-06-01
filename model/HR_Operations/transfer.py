from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey
from core.database import Base
from datetime import datetime


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    from_department = Column(String(150), nullable=False)
    to_department = Column(String(150), nullable=False)
    from_location = Column(String(150), nullable=True)
    to_location = Column(String(150), nullable=True)
    transfer_type = Column(String(50), nullable=False)   # INTER_DEPARTMENT | INTER_LOCATION | INTER_COMPANY
    effective_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, server_default="PENDING")  # PENDING | APPROVED | REJECTED | COMPLETED
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
