from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from core.database import Base


class Ticket(Base):
    __tablename__ = "hr_helpdesk_tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    category = Column(String(50), nullable=False)
    # Payroll queries, Leave and attendance issues, Policy clarifications,
    # IT access issues, Document requests, Reimbursement queries,
    # Personal data updates, General HR queries, Grievances and complaints

    priority = Column(String(10), nullable=False, default="Medium")
    # Low, Medium, High

    status = Column(String(20), nullable=False, default="Open")
    # Open, In-Progress, Resolved, Closed

    employee_name = Column(String(150), nullable=True)

    assigned_agent = Column(String(100), nullable=True)
    # John HR, Priya Kumar, IT Support, Admin Team, Finance Team

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)