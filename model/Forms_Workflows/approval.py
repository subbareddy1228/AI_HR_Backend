from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from core.database import Base
from datetime import datetime


class ApprovalRequest(Base):
    """
    Stores every approval request raised by an employee.

    Frontend - Approvals Dashboard:
    ─────────────────────────────────────────────────────────────
    Employee View → employee sees their own requests
    Manager View  → manager sees team queue, can Approve / Reject

    Stat cards : Total Requests | Pending | Approved | Rejected
    Table cols : Request Details | Status | Priority | SLA Status |
                 Submitted | Actions
    """

    __tablename__ = "approval_requests"

    id              = Column(Integer, primary_key=True, index=True)

    # What is being approved
    reference_type  = Column(String(500), nullable=False)   # Leave | Expense | Asset …
    reference_id    = Column(Integer,      nullable=True)    # FK to originating record

    # Who raised it
    employee_id     = Column(Integer,      nullable=False)
    employee_name   = Column(String(500),  nullable=False)
    requested_by    = Column(String(500),  nullable=False)

    # Request content
    request_summary = Column(Text,         nullable=True)

    # Routing
    assigned_to     = Column(String(500),  nullable=True)    # approver email / id

    # Lifecycle
    status          = Column(String(500),  default="Pending")

    # Action
    action_taken_at = Column(DateTime,     nullable=True)
    action_by       = Column(String(500),  nullable=True)
    comments        = Column(Text,         nullable=True)

    # Audit
    created_at      = Column(DateTime,     default=datetime.utcnow)