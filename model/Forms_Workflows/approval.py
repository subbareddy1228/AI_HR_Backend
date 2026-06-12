# model/Forms_Workflows/approval.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date
from core.database import Base
from datetime import datetime


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id               = Column(Integer, primary_key=True, index=True)

    # Request info
    title            = Column(String(255), nullable=False)
    description      = Column(Text, nullable=True)
    reference_type   = Column(String(50), nullable=False)
    # leave/expense/transfer/promotion/exit/other

    reference_id     = Column(Integer, nullable=True)

    # Employee info — Employee View shows "John Smith" badge
    employee_id      = Column(Integer, nullable=True)
    employee_name    = Column(String(255), nullable=True)
    employee_email   = Column(String(255), nullable=True)

    # Approver info — Manager View shows "Approver" badge
    assigned_to      = Column(String(100), nullable=True)
    assigned_to_id   = Column(Integer, nullable=True)
    approver_role    = Column(String(50), nullable=True)  # "Approver" badge text

    # Status
    # Pending / Approved / Rejected / Cancelled / Escalated
    status           = Column(String(30), default="Pending")

    # Priority: Low / Medium / High / Critical
    priority         = Column(String(20), default="Medium")

    # Date range — shown as "Mar 15, 2024 - Mar 19, 2024"
    start_date       = Column(Date, nullable=True)
    end_date         = Column(Date, nullable=True)

    # SLA — shown as "SLA Breached" red badge, "Due: Mar 8, 2024 (-824d)"
    sla_due_date     = Column(DateTime, nullable=True)
    sla_breached     = Column(Boolean, default=False)

    # Action tracking
    action_by        = Column(String(100), nullable=True)
    action_taken_at  = Column(DateTime, nullable=True)
    comments         = Column(Text, nullable=True)

    # Timestamps — "Submitted: Mar 1, 2024"
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)