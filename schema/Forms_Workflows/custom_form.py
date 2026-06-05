from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from core.database import Base
from datetime import datetime


class CustomForm(Base):
    __tablename__ = "custom_forms"

    id              = Column(Integer, primary_key=True, index=True)
    form_name       = Column(String(255), nullable=False)
    form_category   = Column(String(50), nullable=False)   # Onboarding/Leave/Expense/Survey/Exit/Other
    description     = Column(Text, nullable=True)
    fields_schema   = Column(JSON, nullable=True)          # list of field definitions
    is_active       = Column(Boolean, default=True)
    is_published    = Column(Boolean, default=False)
    version         = Column(Integer, default=1)
    created_by      = Column(String(100), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id              = Column(Integer, primary_key=True, index=True)
    form_id         = Column(Integer, ForeignKey("custom_forms.id"), nullable=False)
    employee_id     = Column(Integer, nullable=True)
    employee_name   = Column(String(255), nullable=True)
    submitted_by    = Column(String(100), nullable=True)
    form_data       = Column(JSON, nullable=True)          # field key → value
    status          = Column(String(50), default="Submitted")  # Draft/Submitted/Reviewed/Approved/Rejected
    reviewed_by     = Column(String(100), nullable=True)
    review_notes    = Column(Text, nullable=True)
    submitted_at    = Column(DateTime, default=datetime.utcnow)
    reviewed_at     = Column(DateTime, nullable=True)