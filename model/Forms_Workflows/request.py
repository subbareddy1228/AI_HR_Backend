# model/Forms_Workflows/request.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from core.database import Base
from datetime import datetime
import uuid


def generate_request_id():
    return f"REQ-{str(uuid.uuid4())[:4].upper()}"


class HRRequest(Base):
    __tablename__ = "hr_requests"

    id              = Column(Integer, primary_key=True, index=True)
    request_id      = Column(String(20), unique=True, index=True, default=generate_request_id)

    # Request info
    title           = Column(String(255), nullable=False)
    description     = Column(Text, nullable=True)
    request_type    = Column(String(100), nullable=False)   # Bank Account Change/WFH/Reimbursement etc.
    category        = Column(String(100), nullable=False)   # Personal Information/Work-Related/Administrative
                                                            # Financial/Travel & Expense/IT & Systems/Feedback
    # Location & Workflow
    location        = Column(String(100), nullable=True)
    workflow        = Column(String(100), nullable=True)

    # Employee info
    employee_id     = Column(Integer, nullable=True)
    employee_name   = Column(String(255), nullable=True)
    employee_email  = Column(String(255), nullable=True)
    department      = Column(String(100), nullable=True)
    submitted_by    = Column(String(100), nullable=True)

    # Assignment
    assigned_to     = Column(String(100), nullable=True)
    assigned_to_id  = Column(Integer, nullable=True)

    # Status & Priority
    status          = Column(String(30), default="Open")    # Open/In Progress/Approved/Rejected/Completed/Cancelled
    filter_status   = Column(String(30), nullable=True)     # Approved/In Progress/Rejected/Completed
    priority        = Column(String(20), default="Medium")  # Low/Medium/High/Critical

    # SLA
    sla             = Column(String(100), nullable=True)    # e.g. "2-3 business days"
    sla_due_date    = Column(DateTime, nullable=True)
    sla_breached    = Column(Boolean, default=False)

    # Auto-fill / Quick Action
    is_quick_action = Column(Boolean, default=False)
    auto_fill_data  = Column(JSON, nullable=True)

    # Additional data
    attachments     = Column(JSON, nullable=True)
    form_data       = Column(JSON, nullable=True)

    # Action
    action_by       = Column(String(100), nullable=True)
    action_taken_at = Column(DateTime, nullable=True)
    response        = Column(Text, nullable=True)
    comments        = Column(Text, nullable=True)

    # Timestamps
    submitted_date  = Column(DateTime, default=datetime.utcnow)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RequestTemplate(Base):
    __tablename__ = "request_templates"

    id              = Column(Integer, primary_key=True, index=True)
    title           = Column(String(255), nullable=False)
    description     = Column(Text, nullable=True)
    request_type    = Column(String(100), nullable=False)
    category        = Column(String(100), nullable=False)
    sla             = Column(String(100), nullable=True)
    priority        = Column(String(20), default="Medium")
    is_quick_action = Column(Boolean, default=False)        # Shows in Quick Actions section
    auto_description = Column(Boolean, default=False)       # Auto-fill description
    form_schema     = Column(JSON, nullable=True)           # Fields to fill
    workflow        = Column(String(100), nullable=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)