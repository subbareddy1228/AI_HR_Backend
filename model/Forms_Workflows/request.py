# model/Forms_Workflows/request.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from core.database import Base
from datetime import datetime


class HRRequest(Base):
    __tablename__ = "hr_requests"

    id               = Column(Integer, primary_key=True, index=True)
    request_id       = Column(String(20), unique=True, index=True)  # REQ-1001

    # Request info
    title            = Column(String(255), nullable=False)
    description      = Column(Text, nullable=True)
    request_type     = Column(String(150), nullable=False)
    category         = Column(String(100), nullable=False)
    # Categories: Personal Information / Work-Related / Administrative /
    #             Financial / Travel & Expense / IT & Systems / Feedback

    # Location & Workflow
    location         = Column(String(100), nullable=True)
    workflow         = Column(String(100), nullable=True)

    # Employee info
    employee_id      = Column(Integer, nullable=True)
    employee_name    = Column(String(255), nullable=True)
    employee_email   = Column(String(255), nullable=True)
    department       = Column(String(100), nullable=True)
    submitted_by     = Column(String(100), nullable=True)

    # Assignment
    assigned_to      = Column(String(100), nullable=True)
    assigned_to_id   = Column(Integer, nullable=True)

    # Status
    # Open / In Progress / Approved / Rejected / Completed / Cancelled
    status           = Column(String(30), default="Open")
    filter_status    = Column(String(30), nullable=True)

    # Priority: Low / Medium / High / Critical
    priority         = Column(String(20), default="Medium")

    # SLA
    sla              = Column(String(100), nullable=True)   # e.g. "2-3 business days"
    sla_due_date     = Column(DateTime, nullable=True)
    sla_breached     = Column(Boolean, default=False)

    # Quick Action / Auto-fill
    is_quick_action  = Column(Boolean, default=False)
    auto_fill_data   = Column(JSON, nullable=True)
    auto_description = Column(Boolean, default=False)

    # Form & Attachments
    form_data        = Column(JSON, nullable=True)
    attachments      = Column(JSON, nullable=True)

    # Action tracking
    action_by        = Column(String(100), nullable=True)
    action_taken_at  = Column(DateTime, nullable=True)
    response         = Column(Text, nullable=True)
    comments         = Column(Text, nullable=True)

    # Timestamps
    submitted_date   = Column(DateTime, default=datetime.utcnow)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RequestTemplate(Base):
    __tablename__ = "request_templates"

    id               = Column(Integer, primary_key=True, index=True)
    title            = Column(String(255), nullable=False)
    description      = Column(Text, nullable=True)
    request_type     = Column(String(150), nullable=False)
    category         = Column(String(100), nullable=False)
    sla              = Column(String(100), nullable=True)
    priority         = Column(String(20), default="Medium")
    is_quick_action  = Column(Boolean, default=False)
    auto_description = Column(Boolean, default=False)
    form_schema      = Column(JSON, nullable=True)
    workflow         = Column(String(100), nullable=True)
    icon             = Column(String(100), nullable=True)
    color_tag        = Column(String(20), nullable=True)   # red/yellow/green/blue
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)