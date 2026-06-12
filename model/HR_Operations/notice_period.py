
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from core.database import Base


class NoticeStatus(str, enum.Enum):
    SERVING       = "SERVING"
    COMPLETED     = "COMPLETED"
    WAIVED        = "WAIVED"
    BUYOUT        = "BUYOUT"
    EXTENDED      = "EXTENDED"
    ABSCONDED     = "ABSCONDED"
    CANCELLED     = "CANCELLED"


class ApprovalStatus(str, enum.Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ON_HOLD  = "ON_HOLD"


class ResignationWorkflowStep(str, enum.Enum):
    RESIGNATION_SUBMITTED    = "RESIGNATION_SUBMITTED"
    MANAGER_ACKNOWLEDGED     = "MANAGER_ACKNOWLEDGED"
    HR_REVIEWED              = "HR_REVIEWED"
    COUNTER_OFFER_SENT       = "COUNTER_OFFER_SENT"
    COUNTER_OFFER_RESPONDED  = "COUNTER_OFFER_RESPONDED"
    NOTICE_SERVING           = "NOTICE_SERVING"
    CLEARANCE_INITIATED      = "CLEARANCE_INITIATED"
    FULL_AND_FINAL_PROCESSED = "FULL_AND_FINAL_PROCESSED"
    EXIT_COMPLETED           = "EXIT_COMPLETED"


class ResignationReason(str, enum.Enum):
    BETTER_OPPORTUNITY  = "BETTER_OPPORTUNITY"
    PERSONAL_REASONS    = "PERSONAL_REASONS"
    RELOCATION          = "RELOCATION"
    HIGHER_EDUCATION    = "HIGHER_EDUCATION"
    HEALTH_ISSUES       = "HEALTH_ISSUES"
    WORK_LIFE_BALANCE   = "WORK_LIFE_BALANCE"
    COMPENSATION        = "COMPENSATION"
    GROWTH_OPPORTUNITY  = "GROWTH_OPPORTUNITY"
    FAMILY_REASONS      = "FAMILY_REASONS"
    OTHER               = "OTHER"


class CounterOfferStatus(str, enum.Enum):
    PENDING  = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED  = "EXPIRED"


class NoticePeriod(Base):

    __tablename__ = "notice_periods"
    __table_args__ = (
        CheckConstraint("notice_period_days > 0", name="ck_notice_period_days_positive"),
        CheckConstraint(
            "notice_end_date >= notice_start_date",
            name="ck_notice_dates_order",
        ),
        Index("ix_notice_periods_employee_status", "employee_id", "status"),
    )

    id                   = Column(Integer, primary_key=True, index=True)
    employee_id          = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)

    resignation_date     = Column(Date, nullable=False)
    resignation_reason   = Column(Enum(ResignationReason), nullable=True)
    resignation_letter   = Column(Text, nullable=True)         

    notice_start_date    = Column(Date, nullable=False)
    notice_end_date      = Column(Date, nullable=False)      
    notice_period_days   = Column(Integer, nullable=False)       
    actual_lwd           = Column(Date, nullable=True)           

    serving_days         = Column(Integer, nullable=True, default=0)
    days_remaining       = Column(Integer, nullable=True)

    manager_acknowledged = Column(Boolean, nullable=False, default=False)
    hr_reviewed          = Column(Boolean, nullable=False, default=False)

    monthly_salary       = Column(Numeric(14, 2), nullable=True)  
    buyout_amount        = Column(Numeric(14, 2), nullable=True)

    status               = Column(
        Enum(NoticeStatus), nullable=False, default=NoticeStatus.SERVING, index=True
    )
    remarks              = Column(Text, nullable=True)


    created_by           = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


    buyout_requests    = relationship("NoticeBuyoutRequest",    back_populates="notice_period", cascade="all, delete-orphan")
    waiver_requests    = relationship("NoticeWaiverRequest",    back_populates="notice_period", cascade="all, delete-orphan")
    counter_offers     = relationship("NoticeCounterOffer",     back_populates="notice_period", cascade="all, delete-orphan")
    extension_requests = relationship("NoticeExtensionRequest", back_populates="notice_period", cascade="all, delete-orphan")
    workflow_steps     = relationship("NoticeResignationWorkflow", back_populates="notice_period", cascade="all, delete-orphan", order_by="NoticeResignationWorkflow.step_date")
    calculations       = relationship("NoticeCalculation",      back_populates="notice_period", cascade="all, delete-orphan")


class NoticeBuyoutRequest(Base):

    __tablename__ = "notice_buyout_requests"
    __table_args__ = (
        CheckConstraint("days_to_buyout > 0", name="ck_buyout_days_positive"),
        CheckConstraint("buyout_amount > 0",   name="ck_buyout_amount_positive"),
    )

    id               = Column(Integer, primary_key=True, index=True)
    notice_period_id = Column(Integer, ForeignKey("notice_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id      = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)

    requested_date   = Column(Date, nullable=False)
    days_to_buyout   = Column(Integer, nullable=False)           # remaining notice days to buy out
    monthly_salary   = Column(Numeric(14, 2), nullable=False)
    buyout_amount    = Column(Numeric(14, 2), nullable=False)    # = (monthly_salary / 30) * days_to_buyout
    requested_lwd    = Column(Date, nullable=False)              # desired last working day

    approval_status  = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING, index=True)
    approved_by      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at      = Column(DateTime, nullable=True)


    manager_status   = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    hr_status        = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    finance_status   = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)

    rejection_reason = Column(Text, nullable=True)
    remarks          = Column(Text, nullable=True)

    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    notice_period    = relationship("NoticePeriod", back_populates="buyout_requests")


class NoticeWaiverRequest(Base):

    __tablename__ = "notice_waiver_requests"
    __table_args__ = (
        CheckConstraint("waiver_days > 0", name="ck_waiver_days_positive"),
    )

    id               = Column(Integer, primary_key=True, index=True)
    notice_period_id = Column(Integer, ForeignKey("notice_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id      = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)

    requested_date   = Column(Date, nullable=False)
    waiver_days      = Column(Integer, nullable=False)           # days to be waived
    reason           = Column(Text, nullable=False)
    document_urls    = Column(Text, nullable=True)               # JSON-encoded list of file paths/URLs

    approval_status  = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING, index=True)
    approved_by      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at      = Column(DateTime, nullable=True)

    manager_status   = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    hr_status        = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    director_status  = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)

    rejection_reason = Column(Text, nullable=True)
    remarks          = Column(Text, nullable=True)

    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    notice_period    = relationship("NoticePeriod", back_populates="waiver_requests")


class NoticeCounterOffer(Base):

    __tablename__ = "notice_counter_offers"
    __table_args__ = (
        CheckConstraint("hike_percentage >= 0", name="ck_counter_hike_positive"),
        CheckConstraint("offered_salary > 0",   name="ck_counter_salary_positive"),
    )

    id                     = Column(Integer, primary_key=True, index=True)
    notice_period_id       = Column(Integer, ForeignKey("notice_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id            = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)

    current_salary         = Column(Numeric(14, 2), nullable=False)
    offered_salary         = Column(Numeric(14, 2), nullable=False)
    hike_percentage        = Column(Numeric(5, 2), nullable=True)   # auto-computed
    additional_benefits    = Column(Text, nullable=True)             # JSON or plain text
    role_change            = Column(String(200), nullable=True)
    retention_probability  = Column(Integer, nullable=True)          # 0–100, AI-predicted

    offer_date             = Column(Date, nullable=False)
    expiry_date            = Column(Date, nullable=True)

    status                 = Column(Enum(CounterOfferStatus), nullable=False, default=CounterOfferStatus.PENDING, index=True)
    employee_response      = Column(Text, nullable=True)
    responded_at           = Column(DateTime, nullable=True)

    created_by             = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at             = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at             = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    notice_period          = relationship("NoticePeriod", back_populates="counter_offers")


class NoticeExtensionRequest(Base):

    __tablename__ = "notice_extension_requests"
    __table_args__ = (
        CheckConstraint("extension_days > 0", name="ck_extension_days_positive"),
    )

    id                  = Column(Integer, primary_key=True, index=True)
    notice_period_id    = Column(Integer, ForeignKey("notice_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id         = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)

    requested_by        = Column(String(20), nullable=False)     # "EMPLOYEE" | "COMPANY"
    requested_date      = Column(Date, nullable=False)
    extension_days      = Column(Integer, nullable=False)
    new_end_date        = Column(Date, nullable=False)           # original LWD + extension_days
    reason              = Column(Text, nullable=False)

    approval_status     = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING, index=True)
    approved_by         = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at         = Column(DateTime, nullable=True)
    rejection_reason    = Column(Text, nullable=True)
    remarks             = Column(Text, nullable=True)

    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    notice_period       = relationship("NoticePeriod", back_populates="extension_requests")


class NoticeResignationWorkflow(Base):

    __tablename__ = "notice_resignation_workflow"

    id               = Column(Integer, primary_key=True, index=True)
    notice_period_id = Column(Integer, ForeignKey("notice_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id      = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)

    step             = Column(Enum(ResignationWorkflowStep), nullable=False)
    step_date        = Column(DateTime, nullable=False, default=datetime.utcnow)
    performed_by     = Column(Integer, ForeignKey("employees.id"), nullable=True)   # actor (HR / manager)
    comments         = Column(Text, nullable=True)
    is_current_step  = Column(Boolean, nullable=False, default=True)

    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)

    notice_period    = relationship("NoticePeriod", back_populates="workflow_steps")


class NoticeCalculation(Base):

    __tablename__ = "notice_calculations"

    id               = Column(Integer, primary_key=True, index=True)
    notice_period_id = Column(Integer, ForeignKey("notice_periods.id", ondelete="CASCADE"), nullable=True, index=True)

    calc_type        = Column(String(30), nullable=False)        # LWD | BUYOUT | WAIVER | SHORTFALL | EXTENSION
    input_data       = Column(Text, nullable=False)              # JSON snapshot of inputs
    result_data      = Column(Text, nullable=False)              # JSON snapshot of outputs
    calculated_by    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    calculated_at    = Column(DateTime, default=datetime.utcnow, nullable=False)

    notice_period    = relationship("NoticePeriod", back_populates="calculations")
