from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from core.database import Base
from datetime import datetime


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    reference_type = Column(String(50), nullable=False)  # leave/transfer/promotion/expense/exit/other
    reference_id = Column(Integer, nullable=False)
    employee_id = Column(Integer, nullable=True)
    employee_name = Column(String(255), nullable=True)
    request_summary = Column(String(500), nullable=False)
    requested_by = Column(String(100), nullable=True)
    assigned_to = Column(String(100), nullable=True)
    status = Column(String(50), default="Pending")  # Pending/Approved/Rejected/Escalated
    action_taken_at = Column(DateTime, nullable=True)
    action_by = Column(String(100), nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
