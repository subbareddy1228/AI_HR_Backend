from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from core.database import Base
from datetime import datetime


class CustomForm(Base):
    __tablename__ = "custom_forms"

    id = Column(Integer, primary_key=True, index=True)
    form_name = Column(String(255), nullable=False)
    form_category = Column(String(50), nullable=False)  # Onboarding/Leave/Expense/Survey/Other
    description = Column(Text, nullable=True)
    fields_schema = Column(JSON, nullable=True)  # array of field definitions
    is_active = Column(Boolean, default=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("custom_forms.id"), nullable=False)
    employee_id = Column(Integer, nullable=True)
    submitted_by = Column(String(100), nullable=True)
    form_data = Column(JSON, nullable=True)  # stores field values
    status = Column(String(50), default="Submitted")  # Draft/Submitted/Reviewed
    submitted_at = Column(DateTime, default=datetime.utcnow)
