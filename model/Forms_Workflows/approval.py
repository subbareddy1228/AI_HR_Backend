from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date
from core.database import Base
from datetime import datetime


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id              = Column(Integer, primary_key=True, index=True)

    # Request info
    title           = Column(String(255), nullable=False)
    description     = Column(Text, nullable=True)
    reference_type  = Column(String(50), nullable=False)   # leave/transfer/promotion/expense/exit/other
    reference_id    = Column(Integer, nullable=True)

    # Employee info
    employee_id     = Column(Integer, nullable=True)
    employee_name   = Column(String(255), nullable=True)
    requested_by    = Column(String(100), nullable=True)

    # Assignee (manager/approver)
    assigned_to     = Column(String(100), nullable=True)
    assigned_to_id  = Column(Integer, nullable=True)

    # Status & Priority
    status          = Column(String(50), default="Pending")   # Pending/Approved/Rejected/Cancelled/Escalated
    priority        = Column(String(20), default="Medium")    # Low/Medium/High/Critical

    # Date range (for leave etc.)
    start_date      = Column(Date, nullable=True)
    end_date        = Column(Date, nullable=True)

    # SLA
    sla_due_date    = Column(DateTime, nullable=True)
    sla_breached    = Column(Boolean, default=False)

    # Action
    action_by       = Column(String(100), nullable=True)
    action_taken_at = Column(DateTime, nullable=True)
    comments        = Column(Text, nullable=True)

    # Timestamps
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)