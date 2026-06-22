"""
model/HR_Operations/letter_generation.py

HR Letter Generation System
----------------------------
Two tables:

1. LetterTemplate   -> the 12 reusable templates shown on the dashboard
                       (Employment / Financial / Exit / Legal / Career / Disciplinary)

2. LetterRequest     -> the actual letter requests raised for employees
                        (LTR-REQ-2024-001 ... ) with workflow status
                        PENDING | APPROVED | REJECTED, AI/manual generated
                        body content, and approval audit trail.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
)
from core.database import Base
from datetime import datetime


# ======================================================
# 1. LETTER TEMPLATE
# ======================================================
class LetterTemplate(Base):
    __tablename__ = "letter_templates"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), nullable=False)              # "Experience Certificate"
    code = Column(String(50), unique=True, nullable=False, index=True)  # "EXPERIENCE_CERTIFICATE"

    # Employment | Financial | Exit | Legal | Career | Disciplinary
    category = Column(String(50), nullable=False, index=True)

    description = Column(String(255), nullable=True)

    # Body template with {{placeholders}} e.g. {{employee_name}}, {{designation}}
    template_body = Column(Text, nullable=False)

    # Default subject line, supports {{placeholders}} too
    subject_template = Column(String(255), nullable=False)

    is_ai_optimized = Column(Boolean, nullable=False, default=True)
    auto_approve = Column(Boolean, nullable=False, default=False)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ======================================================
# 2. LETTER REQUEST
# ======================================================
class LetterRequest(Base):
    __tablename__ = "letter_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Human readable id shown in UI -> "LTR-REQ-2024-008"
    request_code = Column(String(50), unique=True, nullable=False, index=True)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    template_id = Column(Integer, ForeignKey("letter_templates.id"), nullable=True, index=True)
    letter_type = Column(String(150), nullable=False)   # e.g. "Loan Sanction Letter"

    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)

    # PENDING | APPROVED | REJECTED | ISSUED
    status = Column(String(50), nullable=False, server_default="PENDING", index=True)

    generated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)   # who raised request
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)    # who approved/rejected
    rejection_reason = Column(Text, nullable=True)

    is_ai_generated = Column(Boolean, nullable=False, default=False)
    auto_approved = Column(Boolean, nullable=False, default=False)

    letter_date = Column(Date, nullable=False)
    approved_at = Column(DateTime, nullable=True)

    download_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
