# from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey
# from core.database import Base
# from datetime import datetime


# class ExitManagement(Base):
#     __tablename__ = "exit_management"

#     id = Column(Integer, primary_key=True, index=True)
#     employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
#     resignation_date = Column(Date, nullable=False)
#     last_working_date = Column(Date, nullable=True)
#     exit_type = Column(String(50), nullable=False)          # RESIGNATION | TERMINATION | RETIREMENT | ABSCONDING
#     reason = Column(Text, nullable=True)
#     status = Column(String(50), nullable=False, server_default="INITIATED")  # INITIATED | IN_PROGRESS | COMPLETED | CANCELLED
#     exit_interview_done = Column(String(10), nullable=False, server_default="NO")  # YES | NO
#     clearance_status = Column(String(50), nullable=False, server_default="PENDING")  # PENDING | PARTIAL | COMPLETED
#     remarks = Column(Text, nullable=True)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
"""
model/exit_management.py
SQLModel table definitions for Employee Separation & Exit Management
Tables: Resignation, ClearanceChecklist, ClearanceItem, ExitInterview, FnFSettlement
"""

from datetime import datetime, date
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


# ═══════════════════════════════════════════════════════════════════════════════
#  RESIGNATION
# ═══════════════════════════════════════════════════════════════════════════════

class Resignation(SQLModel, table=True):
    __tablename__ = "resignations"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    resignation_date: date = Field(nullable=False)
    last_working_day: Optional[date] = Field(default=None)
    notice_period_days: int = Field(default=0, nullable=False)
    reason: Optional[str] = Field(default=None)

    # Status: pending / accepted / revoked / rejected
    status: str = Field(default="pending", nullable=False)

    accepted_by: Optional[int] = Field(default=None, foreign_key="users.id")
    accepted_at: Optional[datetime] = Field(default=None)
    revoked_at: Optional[datetime] = Field(default=None)
    hr_remarks: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships
    clearance_checklists: List["ClearanceChecklist"] = Relationship(back_populates="resignation")
    exit_interviews: List["ExitInterview"] = Relationship(back_populates="resignation")
    fnf_settlements: List["FnFSettlement"] = Relationship(back_populates="resignation")


# ═══════════════════════════════════════════════════════════════════════════════
#  CLEARANCE CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════

class ClearanceChecklist(SQLModel, table=True):
    __tablename__ = "clearance_checklists"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    resignation_id: int = Field(foreign_key="resignations.id", nullable=False)

    # Status: pending / in_progress / completed
    overall_status: str = Field(default="pending", nullable=False)

    initiated_by: int = Field(foreign_key="users.id", nullable=False)
    initiated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    completed_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    resignation: Optional[Resignation] = Relationship(back_populates="clearance_checklists")
    items: List["ClearanceItem"] = Relationship(back_populates="checklist")


class ClearanceItem(SQLModel, table=True):
    __tablename__ = "clearance_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    checklist_id: int = Field(foreign_key="clearance_checklists.id", index=True, nullable=False)

    # Department: IT / Finance / Admin / HR
    department: str = Field(nullable=False)
    task_description: str = Field(nullable=False)

    is_completed: bool = Field(default=False, nullable=False)
    completed_by: Optional[int] = Field(default=None, foreign_key="users.id")
    completed_at: Optional[datetime] = Field(default=None)
    remarks: Optional[str] = Field(default=None)

    # Relationship
    checklist: Optional[ClearanceChecklist] = Relationship(back_populates="items")


# ═══════════════════════════════════════════════════════════════════════════════
#  EXIT INTERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

class ExitInterview(SQLModel, table=True):
    __tablename__ = "exit_interviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    resignation_id: int = Field(foreign_key="resignations.id", nullable=False)

    # Employee responses
    reason_for_leaving: Optional[str] = Field(default=None)
    job_satisfaction_score: Optional[int] = Field(default=None)       # 1–10
    management_score: Optional[int] = Field(default=None)             # 1–10
    work_environment_score: Optional[int] = Field(default=None)       # 1–10
    growth_opportunity_score: Optional[int] = Field(default=None)     # 1–10
    would_rejoin: Optional[bool] = Field(default=None)
    suggestions: Optional[str] = Field(default=None)
    additional_comments: Optional[str] = Field(default=None)

    # AI-generated fields (filled asynchronously by GPT-4)
    sentiment_label: Optional[str] = Field(default=None)    # positive / neutral / negative
    sentiment_score: Optional[float] = Field(default=None)  # 0.0 – 1.0
    ai_summary: Optional[str] = Field(default=None)

    submitted_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    reviewed_by: Optional[int] = Field(default=None, foreign_key="users.id")
    reviewed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationship
    resignation: Optional[Resignation] = Relationship(back_populates="exit_interviews")


# ═══════════════════════════════════════════════════════════════════════════════
#  FULL & FINAL SETTLEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class FnFSettlement(SQLModel, table=True):
    __tablename__ = "fnf_settlements"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    resignation_id: int = Field(foreign_key="resignations.id", nullable=False)

    # ── Earnings ──────────────────────────────────────────────────────────────
    basic_salary: float = Field(default=0.0)
    hra: float = Field(default=0.0)
    other_allowances: float = Field(default=0.0)
    leave_encashment: float = Field(default=0.0)
    gratuity: float = Field(default=0.0)
    bonus_payout: float = Field(default=0.0)
    notice_period_payment: float = Field(default=0.0)   # payment in lieu of notice

    # ── Deductions ────────────────────────────────────────────────────────────
    notice_period_recovery: float = Field(default=0.0)  # if notice not fully served
    loan_recovery: float = Field(default=0.0)
    advance_recovery: float = Field(default=0.0)
    tax_deduction: float = Field(default=0.0)
    other_deductions: float = Field(default=0.0)

    # ── Computed Totals ───────────────────────────────────────────────────────
    gross_earnings: float = Field(default=0.0)
    total_deductions: float = Field(default=0.0)
    net_payable: float = Field(default=0.0)

    # ── Status: draft / calculated / approved / paid ──────────────────────────
    status: str = Field(default="draft", nullable=False)

    calculated_by: Optional[int] = Field(default=None, foreign_key="users.id")
    calculated_at: Optional[datetime] = Field(default=None)
    approved_by: Optional[int] = Field(default=None, foreign_key="users.id")
    approved_at: Optional[datetime] = Field(default=None)
    paid_at: Optional[datetime] = Field(default=None)
    pdf_path: Optional[str] = Field(default=None)
    remarks: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationship
    resignation: Optional[Resignation] = Relationship(back_populates="fnf_settlements")