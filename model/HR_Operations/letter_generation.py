# from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey
# from core.database import Base
# from datetime import datetime


# class LetterGeneration(Base):
#     __tablename__ = "letter_generation"

#     id = Column(Integer, primary_key=True, index=True)
#     employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
#     letter_type = Column(String(100), nullable=False)   # OFFER | APPOINTMENT | CONFIRMATION | RELIEVING | EXPERIENCE | SALARY | WARNING | TERMINATION
#     letter_date = Column(Date, nullable=False)
#     subject = Column(String(255), nullable=False)
#     body = Column(Text, nullable=False)
#     generated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
#     status = Column(String(50), nullable=False, server_default="DRAFT")  # DRAFT | ISSUED | REVOKED
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
"""
model/HR_Operations/letter_generation.py
SQLModel table definitions for HR Letters ONLY
(Resignation, Clearance, ExitInterview, FnFSettlement live in exit_management.py)
"""

from datetime import datetime, date
from typing import Optional, List
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship


# ─── Enums ────────────────────────────────────────────────────────────────────

class LetterType(str, Enum):
    APPOINTMENT  = "appointment"
    CONFIRMATION = "confirmation"
    PROMOTION    = "promotion"
    INCREMENT    = "increment"
    WARNING      = "warning"
    TERMINATION  = "termination"
    EXPERIENCE   = "experience"
    RELIEVING    = "relieving"
    NOC          = "noc"
    TRANSFER     = "transfer"
    CUSTOM       = "custom"


class LetterStatus(str, Enum):
    DRAFT   = "draft"
    ISSUED  = "issued"
    SENT    = "sent"
    REVOKED = "revoked"


# ─── HR Letter Template ───────────────────────────────────────────────────────

class HRLetterTemplate(SQLModel, table=True):
    __tablename__ = "hr_letter_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    letter_type: LetterType
    subject: str
    body_html: str
    variables: Optional[str] = None        # JSON list of variable names
    is_active: bool = Field(default=True)
    created_by: int = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)

    issued_letters: List["HRLetter"] = Relationship(back_populates="template")


# ─── Issued HR Letter ─────────────────────────────────────────────────────────

class HRLetter(SQLModel, table=True):
    __tablename__ = "hr_letters"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(index=True)
    template_id: Optional[int] = Field(default=None, foreign_key="hr_letter_templates.id")
    letter_type: LetterType
    subject: str
    body_html: str
    pdf_path: Optional[str] = None
    status: LetterStatus = Field(default=LetterStatus.DRAFT)
    issued_by: int = Field()
    issued_on: Optional[date] = None
    sent_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)

    template: Optional[HRLetterTemplate] = Relationship(back_populates="issued_letters")