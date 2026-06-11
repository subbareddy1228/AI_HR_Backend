

from __future__ import annotations
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Numeric, Index, UniqueConstraint, BigInteger,
)
from sqlalchemy.orm import relationship
from core.database import Base



class CustomForm(Base):
    __tablename__ = "custom_forms"

    id          = Column(Integer, primary_key=True, index=True)


    client_form_id = Column(String(64),  nullable=True, index=True)   # frontend-generated "form_<ts>"
    title          = Column(String(255), nullable=False)
    description    = Column(Text,        nullable=True)
    category       = Column(String(100), nullable=False, default="General")
  
    status         = Column(String(20), nullable=False, default="draft")
 
    version        = Column(Integer, nullable=False, default=1)
    is_active      = Column(Boolean, default=True, nullable=False)


    created_by     = Column(Integer, ForeignKey("users.id"), nullable=True)
    tenant_id      = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)


    is_deleted     = Column(Boolean, default=False, nullable=False)
    deleted_at     = Column(DateTime, nullable=True)

    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = Column(DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow, nullable=False)
    last_modified  = Column(DateTime, default=datetime.utcnow, nullable=False)

    pages          = relationship("FormPage",              back_populates="form",
                                  cascade="all, delete-orphan", order_by="FormPage.page_number")
    sections       = relationship("FormSection",           back_populates="form",
                                  cascade="all, delete-orphan")
    fields         = relationship("FormField",             back_populates="form",
                                  cascade="all, delete-orphan")
    configuration  = relationship("FormConfiguration",     back_populates="form",
                                  uselist=False, cascade="all, delete-orphan")
    version_history = relationship("FormVersionHistory",   back_populates="form",
                                  cascade="all, delete-orphan",
                                  order_by="FormVersionHistory.created_at")
    submissions    = relationship("FormSubmission",        back_populates="form",
                                  cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_custom_forms_tenant_status", "tenant_id", "status", "is_deleted"),
    )


class FormPage(Base):
    __tablename__ = "form_pages"

    id          = Column(Integer, primary_key=True, index=True)
    form_id     = Column(Integer, ForeignKey("custom_forms.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    title       = Column(String(255), nullable=True)    # e.g. "Page 1"

    form = relationship("CustomForm", back_populates="pages")

    __table_args__ = (
        UniqueConstraint("form_id", "page_number", name="uq_form_page"),
        Index("ix_form_pages_form", "form_id"),
    )


class FormSection(Base):
    __tablename__ = "form_sections"

    id              = Column(Integer, primary_key=True, index=True)
    form_id         = Column(Integer, ForeignKey("custom_forms.id"), nullable=False, index=True)
    client_id       = Column(String(64),  nullable=True)   # frontend "section_<ts>"
    page_number     = Column(Integer, nullable=False, default=1)
    title           = Column(String(255), nullable=False, default="Section")
    description     = Column(Text, nullable=True)
    display_order   = Column(Integer, nullable=False, default=0)

    form = relationship("CustomForm", back_populates="sections")

    __table_args__ = (
        Index("ix_form_sections_form_page", "form_id", "page_number"),
    )

class FormField(Base):

    __tablename__ = "form_fields"

    id              = Column(Integer, primary_key=True, index=True)
    form_id         = Column(Integer, ForeignKey("custom_forms.id"), nullable=False, index=True)
    client_field_id = Column(String(64),  nullable=True, index=True)   # "field_<ts>"

    page_number     = Column(Integer, nullable=False, default=1)
    section_id      = Column(Integer, ForeignKey("form_sections.id"), nullable=True)
    display_order   = Column(Integer, nullable=False, default=0)

  
    field_type      = Column(String(50), nullable=False)

 
    label           = Column(String(255), nullable=False)
    placeholder     = Column(String(500), nullable=True)
    help_text       = Column(Text,        nullable=True)
    default_value   = Column(String(500), nullable=True)

  
    options         = Column(JSON, nullable=True)  


    is_required     = Column(Boolean, nullable=False, default=False)

   
    validation      = Column(JSON, nullable=True)

   
    conditional     = Column(JSON, nullable=True)

  
    pre_populate      = Column(Boolean, nullable=False, default=False)
    pre_populate_type = Column(String(100), nullable=True)
    
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow,
                             onupdate=datetime.utcnow, nullable=False)

    form    = relationship("CustomForm",   back_populates="fields")
    section = relationship("FormSection")

    __table_args__ = (
        Index("ix_form_fields_form_page", "form_id", "page_number"),
        Index("ix_form_fields_client_id", "client_field_id"),
    )


class FormConfiguration(Base):

    __tablename__ = "form_configurations"

    id          = Column(Integer, primary_key=True, index=True)
    form_id     = Column(Integer, ForeignKey("custom_forms.id"),
                          nullable=False, unique=True, index=True)

 
    availability        = Column(String(20), nullable=False, default="all")
 
    departments         = Column(JSON, nullable=True)  
    grades              = Column(JSON, nullable=True)  

 
    submission_window   = Column(String(20), nullable=False, default="always")

    start_date          = Column(String(20), nullable=True)   
    end_date            = Column(String(20), nullable=True)


    submission_type     = Column(String(20), nullable=False, default="single")
 
    submission_limit    = Column(Integer, nullable=False, default=1)


    anonymous_submission = Column(Boolean, nullable=False, default=False)
    auto_save            = Column(Boolean, nullable=False, default=True)
    confirmation_message = Column(Text,    nullable=True,
                                  default="Thank you for your submission!")

  
    post_action_email        = Column(Boolean, nullable=False, default=False)
    post_action_notification = Column(Boolean, nullable=False, default=True)
    post_action_update_data  = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    form = relationship("CustomForm", back_populates="configuration")


class FormVersionHistory(Base):
 
    __tablename__ = "form_version_histories"

    id          = Column(Integer, primary_key=True, index=True)
    form_id     = Column(Integer, ForeignKey("custom_forms.id"), nullable=False, index=True)
    version     = Column(Integer, nullable=False)
    action      = Column(String(500), nullable=False)   # "Added Text field to Page 1"
    changed_by  = Column(String(100), nullable=True, default="System")
    actor_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    form = relationship("CustomForm", back_populates="version_history")

    __table_args__ = (
        Index("ix_form_version_history_form", "form_id"),
    )

class FormSubmission(Base):
  
    __tablename__ = "form_submissions"

    id              = Column(Integer, primary_key=True, index=True)
    form_id         = Column(Integer, ForeignKey("custom_forms.id"), nullable=False, index=True)

    # Submitter
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=True)
    submitted_by    = Column(Integer, ForeignKey("users.id"),     nullable=True)
    anonymous       = Column(Boolean, nullable=False, default=False)

 
    status          = Column(String(20), nullable=False, default="draft")
    employee_snapshot = Column(JSON, nullable=True)

    started_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at    = Column(DateTime, nullable=True)
    reviewed_at     = Column(DateTime, nullable=True)
    reviewed_by     = Column(Integer, ForeignKey("users.id"), nullable=True)

    form    = relationship("CustomForm",          back_populates="submissions")
    answers = relationship("FormSubmissionAnswer", back_populates="submission",
                           cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_form_submission_form_status", "form_id", "status"),
        Index("ix_form_submission_employee",    "employee_id"),
    )


class FormSubmissionAnswer(Base):
   
    __tablename__ = "form_submission_answers"

    id              = Column(Integer, primary_key=True, index=True)
    submission_id   = Column(Integer, ForeignKey("form_submissions.id"),
                              nullable=False, index=True)
    field_id        = Column(Integer, ForeignKey("form_fields.id"),
                              nullable=False)
    client_field_id = Column(String(64), nullable=True)   # redundant for easier lookup

  
    value           = Column(JSON, nullable=True)

    field      = relationship("FormField")
    submission = relationship("FormSubmission", back_populates="answers")

    __table_args__ = (
        UniqueConstraint("submission_id", "field_id", name="uq_submission_field"),
        Index("ix_submission_answers_sub", "submission_id"),
    )