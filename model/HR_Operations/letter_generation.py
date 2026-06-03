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
HR Operations — Letters & Exit Management
Models: SQLModel/SQLAlchemy (matches existing platform stack)
"""
 
from datetime import datetime, date
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
 
 
# ─── Enums ───────────────────────────────────────────────────────────────────
 
class LetterType(str, Enum):
    APPOINTMENT       = "appointment"
    CONFIRMATION      = "confirmation"
    PROMOTION         = "promotion"
    INCREMENT         = "increment"
    WARNING           = "warning"
    TERMINATION       = "termination"
    EXPERIENCE        = "experience"
    RELIEVING         = "relieving"
    NOC               = "noc"
    TRANSFER          = "transfer"
    CUSTOM            = "custom"
 
 
class LetterStatus(str, Enum):
    DRAFT      = "draft"
    ISSUED     = "issued"
    SENT       = "sent"
    REVOKED    = "revoked"
 
 
class ResignationStatus(str, Enum):
    PENDING    = "pending"
    ACCEPTED   = "accepted"
    REVOKED    = "revoked"
    REJECTED   = "rejected"
 
 
class ClearanceStatus(str, Enum):
    PENDING    = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED  = "completed"
 
 
class ClearanceDepartment(str, Enum):
    IT       = "IT"
    FINANCE  = "Finance"
    ADMIN    = "Admin"
    HR       = "HR"
 
 
class SettlementStatus(str, Enum):
    DRAFT      = "draft"
    CALCULATED = "calculated"
    APPROVED   = "approved"
    PAID       = "paid"
 
 
# ─── HR Letter Template ───────────────────────────────────────────────────────
 
class HRLetterTemplate(SQLModel, table=True):
    __tablename__ = "hr_letter_templates"
 
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    letter_type: LetterType
    subject: str
    body_html: str                          # Jinja2-templated HTML body
    variables: Optional[str] = None        # JSON list of variable names expected
    is_active: bool = Field(default=True)
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)
 
    issued_letters: list["HRLetter"] = Relationship(back_populates="template")
 
 
# ─── Issued HR Letter ─────────────────────────────────────────────────────────
 
class HRLetter(SQLModel, table=True):
    __tablename__ = "hr_letters"
 
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="users.id", index=True)
    template_id: Optional[int] = Field(default=None, foreign_key="hr_letter_templates.id")
    letter_type: LetterType
    subject: str
    body_html: str                          # Rendered HTML (template + variables merged)
    pdf_path: Optional[str] = None         # S3 / local path
    status: LetterStatus = Field(default=LetterStatus.DRAFT)
    issued_by: int = Field(foreign_key="users.id")
    issued_on: Optional[date] = None
    sent_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)
 
    template: Optional[HRLetterTemplate] = Relationship(back_populates="issued_letters")
 
 
# ─── Resignation ─────────────────────────────────────────────────────────────
 
class Resignation(SQLModel, table=True):
    __tablename__ = "resignations"
 
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="users.id", index=True)
    resignation_date: date
    last_working_day: Optional[date] = None
    notice_period_days: int = Field(default=0)
    reason: Optional[str] = None
    status: ResignationStatus = Field(default=ResignationStatus.PENDING)
 
    accepted_by: Optional[int] = Field(default=None, foreign_key="users.id")
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    hr_remarks: Optional[str] = None
 
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)
 
 
# ─── Clearance Checklist ──────────────────────────────────────────────────────
 
class ClearanceChecklist(SQLModel, table=True):
    __tablename__ = "clearance_checklists"
 
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="users.id", index=True)
    resignation_id: int = Field(foreign_key="resignations.id")
    overall_status: ClearanceStatus = Field(default=ClearanceStatus.PENDING)
    initiated_by: int = Field(foreign_key="users.id")
    initiated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
 
    items: list["ClearanceItem"] = Relationship(back_populates="checklist")
 
 
class ClearanceItem(SQLModel, table=True):
    __tablename__ = "clearance_items"
 
    id: Optional[int] = Field(default=None, primary_key=True)
    checklist_id: int = Field(foreign_key="clearance_checklists.id", index=True)
    department: ClearanceDepartment
    task_description: str
    is_completed: bool = Field(default=False)
    completed_by: Optional[int] = Field(default=None, foreign_key="users.id")
    completed_at: Optional[datetime] = None
    remarks: Optional[str] = None
 
    checklist: Optional[ClearanceChecklist] = Relationship(back_populates="items")
 
 
# ─── Exit Interview ───────────────────────────────────────────────────────────
 
class ExitInterview(SQLModel, table=True):
    __tablename__ = "exit_interviews"
 
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="users.id", index=True)
    resignation_id: int = Field(foreign_key="resignations.id")
 
    # Structured responses (stored as JSON strings for flexibility)
    reason_for_leaving: Optional[str] = None
    job_satisfaction_score: Optional[int] = None     # 1-10
    management_score: Optional[int] = None           # 1-10
    work_environment_score: Optional[int] = None     # 1-10
    growth_opportunity_score: Optional[int] = None   # 1-10
    would_rejoin: Optional[bool] = None
    suggestions: Optional[str] = None
    additional_comments: Optional[str] = None
 
    # AI-generated
    sentiment_label: Optional[str] = None           # positive / neutral / negative
    sentiment_score: Optional[float] = None         # 0.0 – 1.0
    ai_summary: Optional[str] = None
 
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_by: Optional[int] = Field(default=None, foreign_key="users.id")
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
 
 
# ─── Full & Final Settlement ──────────────────────────────────────────────────
 
class FnFSettlement(SQLModel, table=True):
    __tablename__ = "fnf_settlements"
 
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="users.id", index=True)
    resignation_id: int = Field(foreign_key="resignations.id")
 
    # Earnings
    basic_salary: float = Field(default=0.0)
    hra: float = Field(default=0.0)
    other_allowances: float = Field(default=0.0)
    leave_encashment: float = Field(default=0.0)
    gratuity: float = Field(default=0.0)
    bonus_payout: float = Field(default=0.0)
    notice_period_payment: float = Field(default=0.0)   # payment in lieu of notice
 
    # Deductions
    notice_period_recovery: float = Field(default=0.0)  # if notice not served
    loan_recovery: float = Field(default=0.0)
    advance_recovery: float = Field(default=0.0)
    tax_deduction: float = Field(default=0.0)
    other_deductions: float = Field(default=0.0)
 
    # Computed
    gross_earnings: float = Field(default=0.0)
    total_deductions: float = Field(default=0.0)
    net_payable: float = Field(default=0.0)
 
    status: SettlementStatus = Field(default=SettlementStatus.DRAFT)
    calculated_by: Optional[int] = Field(default=None, foreign_key="users.id")
    calculated_at: Optional[datetime] = None
    approved_by: Optional[int] = Field(default=None, foreign_key="users.id")
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    pdf_path: Optional[str] = None
    remarks: Optional[str] = None
 
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)