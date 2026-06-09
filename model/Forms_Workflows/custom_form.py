# model/Forms_Workflows/custom_form.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from core.database import Base
from datetime import datetime


class CustomForm(Base):
    __tablename__ = "custom_forms"

    id                         = Column(Integer, primary_key=True, index=True)
    form_name                  = Column(String(255), nullable=False)
    form_category              = Column(String(100), nullable=True)
    description                = Column(Text, nullable=True)

    # Multi-page structure
    pages                      = Column(JSON, nullable=True)
    fields_schema              = Column(JSON, nullable=True)

    # Pre-populate from Employee Master
    prepopulate_fields         = Column(JSON, nullable=True)

    # Form config
    allow_multiple_submissions = Column(Boolean, default=False)
    require_approval           = Column(Boolean, default=False)
    approver_role              = Column(String(100), nullable=True)
    show_progress_bar          = Column(Boolean, default=True)
    allow_save_draft           = Column(Boolean, default=True)

    # Status
    status                     = Column(String(20), default="Draft")  # Draft/Published/Archived
    is_active                  = Column(Boolean, default=True)
    is_published               = Column(Boolean, default=False)
    version                    = Column(Integer, default=1)

    # Meta
    created_by                 = Column(String(100), nullable=True)
    created_at                 = Column(DateTime, default=datetime.utcnow)
    updated_at                 = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id             = Column(Integer, primary_key=True, index=True)
    form_id        = Column(Integer, nullable=False, index=True)
    form_version   = Column(Integer, nullable=True)

    # Submitter info
    employee_id    = Column(Integer, nullable=True)
    employee_name  = Column(String(255), nullable=True)
    employee_email = Column(String(255), nullable=True)
    department     = Column(String(100), nullable=True)
    submitted_by   = Column(String(100), nullable=True)

    # Data
    form_data      = Column(JSON, nullable=True)
    page_data      = Column(JSON, nullable=True)

    # Status
    status         = Column(String(30), default="Submitted")

    # Review
    reviewed_by    = Column(String(100), nullable=True)
    review_notes   = Column(Text, nullable=True)
    reviewed_at    = Column(DateTime, nullable=True)

    # Timestamps
    submitted_at   = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FormVersion(Base):
    __tablename__ = "form_versions"

    id             = Column(Integer, primary_key=True, index=True)
    form_id        = Column(Integer, nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    pages          = Column(JSON, nullable=True)
    fields_schema  = Column(JSON, nullable=True)
    changed_by     = Column(String(100), nullable=True)
    change_notes   = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)