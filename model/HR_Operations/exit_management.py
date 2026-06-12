

from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Date, DateTime,
    Text, Numeric, Boolean, ForeignKey, JSON, Index,
)
from sqlalchemy.orm import relationship
from core.database import Base



class ExitType:
    RESIGNATION  = "Resignation"
    TERMINATION  = "Termination"
    RETIREMENT   = "Retirement"
    ABSCONDING   = "Absconding"
    CONTRACT_END = "Contract End"
    ALL = [RESIGNATION, TERMINATION, RETIREMENT, ABSCONDING, CONTRACT_END]


class ExitCaseStatus:
    INITIATED   = "Initiated"
    IN_PROGRESS = "In Progress"
    COMPLETED   = "Completed"
    CANCELLED   = "Cancelled"
    ALL = [INITIATED, IN_PROGRESS, COMPLETED, CANCELLED]


class ClearanceStatus:
    PENDING    = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED  = "Completed"
    WAIVED     = "Waived"
    ALL = [PENDING, IN_PROGRESS, COMPLETED, WAIVED]


class SettlementStatus:
    DRAFT             = "Draft"
    PENDING_APPROVAL  = "Pending Approval"
    APPROVED          = "Approved"
    PAID              = "Paid"
    ALL = [DRAFT, PENDING_APPROVAL, APPROVED, PAID]


class EngagementLevel:
    LOW    = "Low"
    MEDIUM = "Medium"
    HIGH   = "High"
    ALL    = [LOW, MEDIUM, HIGH]



class ExitCase(Base):

    __tablename__ = "exit_cases"

    id                   = Column(Integer, primary_key=True, index=True)
    employee_id          = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    exit_type            = Column(String(50),  nullable=False)   
    resignation_date     = Column(Date, nullable=False)
    last_working_date    = Column(Date, nullable=True)          
    expected_last_day    = Column(Date, nullable=True)          
    exit_reason          = Column(String(100), nullable=True)    
    reason_detail        = Column(Text, nullable=True)

    status               = Column(String(50), nullable=False, default=ExitCaseStatus.INITIATED)
    clearance_status     = Column(String(50), nullable=False, default=ClearanceStatus.PENDING)

    exit_interview_done  = Column(Boolean, nullable=False, default=False)
    exit_interview_date  = Column(Date, nullable=True)

    initiated_by         = Column(Integer, ForeignKey("employees.id"), nullable=True)  # HR user
    approved_by          = Column(Integer, ForeignKey("employees.id"), nullable=True)
    remarks              = Column(Text, nullable=True)

    created_at           = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clearance_items      = relationship("ClearanceItem",  back_populates="exit_case", cascade="all, delete-orphan")
    exit_interview       = relationship("ExitInterview",  back_populates="exit_case",  uselist=False, cascade="all, delete-orphan")
    settlement           = relationship("ExitSettlement", back_populates="exit_case",  uselist=False, cascade="all, delete-orphan")
    documents            = relationship("ExitDocument",   back_populates="exit_case",  cascade="all, delete-orphan")
    alumni_record        = relationship("AlumniRecord",   back_populates="exit_case",  uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_exit_cases_employee_status", "employee_id", "status"),
    )


class ClearanceItem(Base):

    __tablename__ = "exit_clearance_items"

    id              = Column(Integer, primary_key=True, index=True)
    exit_case_id    = Column(Integer, ForeignKey("exit_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    department      = Column(String(100), nullable=False)   # IT, Finance, HR, Admin, etc.
    item_name       = Column(String(200), nullable=False)   # e.g. "Laptop Return"
    assigned_to_id  = Column(Integer, ForeignKey("employees.id"), nullable=True)
    status          = Column(String(50), nullable=False, default=ClearanceStatus.PENDING)
    completed_at    = Column(DateTime, nullable=True)
    remarks         = Column(Text, nullable=True)
    is_mandatory    = Column(Boolean, nullable=False, default=True)
    sort_order      = Column(Integer, nullable=False, default=0)

    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    exit_case       = relationship("ExitCase", back_populates="clearance_items")

    __table_args__ = (
        Index("ix_clearance_items_case_dept", "exit_case_id", "department"),
    )

class ExitInterview(Base):

    __tablename__ = "exit_interviews"

    id                  = Column(Integer, primary_key=True, index=True)
    exit_case_id        = Column(Integer, ForeignKey("exit_cases.id", ondelete="CASCADE"), unique=True, nullable=False)

    interview_date      = Column(Date, nullable=True)
    interviewer_id      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    interview_mode      = Column(String(50), nullable=True)   

    overall_satisfaction = Column(Integer, nullable=True)     
    job_satisfaction     = Column(Integer, nullable=True)    
    management_rating    = Column(Integer, nullable=True)     
    culture_rating       = Column(Integer, nullable=True)     
    primary_reason       = Column(String(200), nullable=True) 
    would_recommend      = Column(Boolean, nullable=True)
    open_to_return       = Column(Boolean, nullable=True)

    responses            = Column(JSON, nullable=True, default=list)
    additional_comments  = Column(Text, nullable=True)

    created_at           = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    exit_case            = relationship("ExitCase", back_populates="exit_interview")


class ExitSettlement(Base):

    __tablename__ = "exit_settlements"

    id                          = Column(Integer, primary_key=True, index=True)
    exit_case_id                = Column(Integer, ForeignKey("exit_cases.id", ondelete="CASCADE"), unique=True, nullable=False)
    employee_id                 = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    basic_salary                = Column(Numeric(14, 2), nullable=False, default=0)
    last_month_salary           = Column(Numeric(14, 2), nullable=False, default=0)
    leave_encashment_days       = Column(Integer, nullable=False, default=0)
    leave_encashment_amount     = Column(Numeric(14, 2), nullable=False, default=0)
    gratuity_amount             = Column(Numeric(14, 2), nullable=False, default=0)
    bonus_amount                = Column(Numeric(14, 2), nullable=False, default=0)
    pending_reimbursements      = Column(Numeric(14, 2), nullable=False, default=0)
    other_earnings              = Column(Numeric(14, 2), nullable=False, default=0)

    notice_period_shortfall_days = Column(Integer, nullable=False, default=0)
    notice_recovery_amount      = Column(Numeric(14, 2), nullable=False, default=0)
    loan_recovery               = Column(Numeric(14, 2), nullable=False, default=0)
    asset_recovery              = Column(Numeric(14, 2), nullable=False, default=0)
    tds_deduction               = Column(Numeric(14, 2), nullable=False, default=0)
    other_deductions            = Column(Numeric(14, 2), nullable=False, default=0)

    total_earnings              = Column(Numeric(14, 2), nullable=False, default=0)
    total_deductions            = Column(Numeric(14, 2), nullable=False, default=0)
    net_payable                 = Column(Numeric(14, 2), nullable=False, default=0)

    settlement_status           = Column(String(50), nullable=False, default=SettlementStatus.DRAFT)
    payment_date                = Column(Date, nullable=True)
    payment_reference           = Column(String(200), nullable=True)
    approved_by_id              = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at                 = Column(DateTime, nullable=True)
    remarks                     = Column(Text, nullable=True)

    created_at                  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at                  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    exit_case                   = relationship("ExitCase", back_populates="settlement")



class AlumniRecord(Base):

    __tablename__ = "alumni_records"

    id                   = Column(Integer, primary_key=True, index=True)
    exit_case_id         = Column(Integer, ForeignKey("exit_cases.id", ondelete="CASCADE"), unique=True, nullable=False)
    employee_id          = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # Eligibility
    rehire_eligible      = Column(Boolean, nullable=False, default=True)
    rehire_notes         = Column(Text, nullable=True)
    blacklisted          = Column(Boolean, nullable=False, default=False)
    blacklist_reason     = Column(Text, nullable=True)


    boomerang_interest   = Column(Boolean, nullable=True)   
    boomerang_applied    = Column(Boolean, nullable=False, default=False)
    boomerang_hired      = Column(Boolean, nullable=False, default=False)
    boomerang_hire_date  = Column(Date, nullable=True)

  
    engagement_level     = Column(String(20), nullable=True) 
    last_contact_date    = Column(Date, nullable=True)
    referral_count       = Column(Integer, nullable=False, default=0)
    linkedin_url         = Column(String(500), nullable=True)
    current_company      = Column(String(200), nullable=True)
    current_designation  = Column(String(200), nullable=True)
    notes                = Column(Text, nullable=True)

    created_at           = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    exit_case            = relationship("ExitCase", back_populates="alumni_record")


class ExitDocument(Base):

    __tablename__ = "exit_documents"

    id              = Column(Integer, primary_key=True, index=True)
    exit_case_id    = Column(Integer, ForeignKey("exit_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False)
    document_type   = Column(String(100), nullable=False)   # Relieving Letter | Experience Letter | NOC | Settlement Statement
    file_name       = Column(String(255), nullable=False)
    file_path       = Column(Text, nullable=False)           # S3 key or local path
    file_size_bytes = Column(Integer, nullable=True)
    mime_type       = Column(String(100), nullable=True)
    generated_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    is_generated    = Column(Boolean, nullable=False, default=False)   # True = auto-generated
    issued_on       = Column(Date, nullable=True)
    remarks         = Column(Text, nullable=True)

    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    exit_case       = relationship("ExitCase", back_populates="documents")


class ClearanceTemplate(Base):

    __tablename__ = "exit_clearance_templates"

    id           = Column(Integer, primary_key=True, index=True)
    department   = Column(String(100), nullable=False)
    item_name    = Column(String(200), nullable=False)
    is_mandatory = Column(Boolean, nullable=False, default=True)
    sort_order   = Column(Integer, nullable=False, default=0)
    is_active    = Column(Boolean, nullable=False, default=True)

    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
