"""
model/HR_Operations/exit_management.py
SQLModel table definitions for Employee Separation & Exit Management
"""

from datetime import datetime, date
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Resignation(SQLModel, table=True):
    __tablename__ = "resignations"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(index=True)
    resignation_date: date
    last_working_day: Optional[date] = None
    notice_period_days: int = Field(default=0)
    reason: Optional[str] = None
    status: str = Field(default="pending")
    accepted_by: Optional[int] = None
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    hr_remarks: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)

    clearance_checklists: List["ClearanceChecklist"] = Relationship(back_populates="resignation")
    exit_interviews: List["ExitInterview"] = Relationship(back_populates="resignation")
    fnf_settlements: List["FnFSettlement"] = Relationship(back_populates="resignation")


class ClearanceChecklist(SQLModel, table=True):
    __tablename__ = "clearance_checklists"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(index=True)
    resignation_id: int = Field(foreign_key="resignations.id")
    overall_status: str = Field(default="pending")
    initiated_by: int
    initiated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    resignation: Optional[Resignation] = Relationship(back_populates="clearance_checklists")
    items: List["ClearanceItem"] = Relationship(back_populates="checklist")


class ClearanceItem(SQLModel, table=True):
    __tablename__ = "clearance_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    checklist_id: int = Field(foreign_key="clearance_checklists.id", index=True)
    department: str
    task_description: str
    is_completed: bool = Field(default=False)
    completed_by: Optional[int] = None
    completed_at: Optional[datetime] = None
    remarks: Optional[str] = None

    checklist: Optional[ClearanceChecklist] = Relationship(back_populates="items")


class ExitInterview(SQLModel, table=True):
    __tablename__ = "exit_interviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(index=True)
    resignation_id: int = Field(foreign_key="resignations.id")
    reason_for_leaving: Optional[str] = None
    job_satisfaction_score: Optional[int] = None
    management_score: Optional[int] = None
    work_environment_score: Optional[int] = None
    growth_opportunity_score: Optional[int] = None
    would_rejoin: Optional[bool] = None
    suggestions: Optional[str] = None
    additional_comments: Optional[str] = None
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    ai_summary: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    resignation: Optional[Resignation] = Relationship(back_populates="exit_interviews")


class FnFSettlement(SQLModel, table=True):
    __tablename__ = "fnf_settlements"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(index=True)
    resignation_id: int = Field(foreign_key="resignations.id")
    basic_salary: float = Field(default=0.0)
    hra: float = Field(default=0.0)
    other_allowances: float = Field(default=0.0)
    leave_encashment: float = Field(default=0.0)
    gratuity: float = Field(default=0.0)
    bonus_payout: float = Field(default=0.0)
    notice_period_payment: float = Field(default=0.0)
    notice_period_recovery: float = Field(default=0.0)
    loan_recovery: float = Field(default=0.0)
    advance_recovery: float = Field(default=0.0)
    tax_deduction: float = Field(default=0.0)
    other_deductions: float = Field(default=0.0)
    gross_earnings: float = Field(default=0.0)
    total_deductions: float = Field(default=0.0)
    net_payable: float = Field(default=0.0)
    status: str = Field(default="draft")
    calculated_by: Optional[int] = None
    calculated_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    pdf_path: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    resignation: Optional[Resignation] = Relationship(back_populates="fnf_settlements")