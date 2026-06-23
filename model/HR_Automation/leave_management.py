"""
models/leave_management.py
All ORM models for Leave Management System — all 7 tabs.
"""

import uuid
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time,
    ForeignKey, Text, Enum as SAEnum, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from core.database import Base


# ─────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────

class AccrualTypeEnum(str, enum.Enum):
    monthly    = "monthly"
    quarterly  = "quarterly"
    annual     = "annual"
    on_joining = "on-joining"


class ApplicationStatusEnum(str, enum.Enum):
    pending   = "pending"
    approved  = "approved"
    rejected  = "rejected"
    withdrawn = "withdrawn"


class AdjustmentTypeEnum(str, enum.Enum):
    credit = "credit"
    debit  = "debit"


class CompOffSourceEnum(str, enum.Enum):
    holiday = "holiday"
    weekend = "weekend"


class CompOffPolicyEnum(str, enum.Enum):
    compOff  = "compOff"
    overtime = "overtime"


class CompOffStatusEnum(str, enum.Enum):
    available = "available"
    applied   = "applied"
    expired   = "expired"


class CampaignStatusEnum(str, enum.Enum):
    active   = "active"
    inactive = "inactive"


class CampaignPeriodEnum(str, enum.Enum):
    quarterly = "quarterly"
    annual    = "annual"


# ─────────────────────────────────────────────────────────
# TAB 1 — LEAVE TYPE
# ─────────────────────────────────────────────────────────

class LeaveType(Base):
    __tablename__ = "leave_types"

    id                      = Column(Integer, primary_key=True, index=True)
    name                    = Column(String(100), nullable=False)
    code                    = Column(String(10),  nullable=False, unique=True, index=True)
    description             = Column(Text,        default="")
    is_paid                 = Column(Boolean,     default=True)
    is_active               = Column(Boolean,     default=True, index=True)

    # Accrual
    accrual_type            = Column(SAEnum(AccrualTypeEnum), default=AccrualTypeEnum.monthly)
    accrual_amount          = Column(Float, default=1.0)
    max_accrual             = Column(Float, default=12.0)

    # Carry Forward
    carry_forward_enabled      = Column(Boolean, default=False)
    carry_forward_max_days     = Column(Integer, default=0)
    carry_forward_expiry_months= Column(Integer, default=0)

    # Encashment
    encashment_enabled      = Column(Boolean, default=False)
    encashment_max_days     = Column(Integer, default=0)
    encashment_rate         = Column(Float,   default=0.0)

    # Behaviour toggles
    allow_half_day          = Column(Boolean, default=True)
    allow_negative          = Column(Boolean, default=False)
    probation_applicable    = Column(Boolean, default=False)
    sandwich_leave          = Column(Boolean, default=True)
    allow_backdated         = Column(Boolean, default=False)
    allow_short_leave       = Column(Boolean, default=False)
    is_optional             = Column(Boolean, default=False)
    usage_limit             = Column(Integer, nullable=True)

    # Proration + Approval workflow (JSONB)
    proration               = Column(JSONB, default={"enabled": True, "method": "proportional"})
    approval_workflow       = Column(JSONB, default={
        "levels": 1,
        "approvers": [{"level": 1, "role": "Manager", "required": True}]
    })

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by  = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)

    balances     = relationship("LeaveBalance",     back_populates="leave_type")
    applications = relationship("LeaveApplication", back_populates="leave_type")


# ─────────────────────────────────────────────────────────
# TAB 2 — LEAVE BALANCE
# ─────────────────────────────────────────────────────────

class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id                     = Column(Integer, primary_key=True, index=True)
    employee_id            = Column(String(20), ForeignKey("employees.id", ondelete="CASCADE"),
                                     nullable=False, index=True)
    leave_type_id          = Column(Integer, ForeignKey("leave_types.id", ondelete="CASCADE"),
                                     nullable=False)
    year                   = Column(Integer, nullable=False)

    opening_balance        = Column(Float, default=0.0)
    accrued                = Column(Float, default=0.0)
    carry_forward          = Column(Float, default=0.0)
    used                   = Column(Float, default=0.0)
    encashed               = Column(Float, default=0.0)
    balance                = Column(Float, default=0.0)

    last_accrual_date      = Column(DateTime(timezone=True), nullable=True)
    last_carry_forward_date= Column(DateTime(timezone=True), nullable=True)
    joining_date           = Column(Date, nullable=True)
    exit_date              = Column(Date, nullable=True)

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    employee   = relationship("Employee",  back_populates="leave_balances")
    leave_type = relationship("LeaveType", back_populates="balances")

    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_balance"),
    )


class LeaveAdjustment(Base):
    __tablename__ = "leave_adjustments"

    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(String(20), ForeignKey("employees.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    leave_type_id   = Column(Integer, ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False)
    adjustment_type = Column(SAEnum(AdjustmentTypeEnum), nullable=False)
    amount          = Column(Float, nullable=False)
    reason          = Column(Text, default="")
    effective_date  = Column(Date, nullable=False)
    approved_by     = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────────────────
# TAB 3 — LEAVE APPLICATION
# ─────────────────────────────────────────────────────────

class LeaveApplication(Base):
    __tablename__ = "leave_applications"

    id               = Column(Integer, primary_key=True, index=True)
    employee_id      = Column(String(20), ForeignKey("employees.id", ondelete="CASCADE"),
                               nullable=False, index=True)
    leave_type_id    = Column(Integer, ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=True)
    leave_type_name  = Column(String(100), default="")
    is_comp_off      = Column(Boolean, default=False)
    comp_off_id      = Column(Integer, ForeignKey("comp_offs.id", ondelete="SET NULL"), nullable=True)

    start_date       = Column(Date, nullable=False, index=True)
    end_date         = Column(Date, nullable=True)
    days             = Column(Float, nullable=False, default=1.0)
    half_day         = Column(Boolean, default=False)
    half_day_type    = Column(String(10), nullable=True)  # first | second

    reason           = Column(Text, default="")
    attachment_path  = Column(String(500), nullable=True)

    status           = Column(SAEnum(ApplicationStatusEnum),
                               default=ApplicationStatusEnum.pending, index=True)
    is_auto_approved = Column(Boolean, default=False)
    is_bulk          = Column(Boolean, default=False)
    bulk_employee_ids= Column(JSONB, default=[])

    applied_at       = Column(DateTime(timezone=True), server_default=func.now())
    applied_by       = Column(String(100), default="")
    current_balance  = Column(Float, default=0.0)

    approved_at      = Column(DateTime(timezone=True), nullable=True)
    approved_by      = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    rejected_at      = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    withdrawn_at     = Column(DateTime(timezone=True), nullable=True)

    approval_workflow= Column(JSONB, default=[])

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    employee   = relationship("Employee",  back_populates="leave_applications")
    leave_type = relationship("LeaveType", back_populates="applications")

    __table_args__ = (
        Index("ix_leave_app_dates",  "start_date", "end_date"),
    )


# ─────────────────────────────────────────────────────────
# TAB 5 — COMP-OFF
# ─────────────────────────────────────────────────────────

class CompOff(Base):
    __tablename__ = "comp_offs"

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(String(20), ForeignKey("employees.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    earned_date  = Column(Date,    nullable=False)
    hours        = Column(Float,   nullable=False)
    expiry_date  = Column(Date,    nullable=True)
    source       = Column(SAEnum(CompOffSourceEnum), default=CompOffSourceEnum.holiday)
    policy_type  = Column(SAEnum(CompOffPolicyEnum), default=CompOffPolicyEnum.compOff)
    description  = Column(Text, default="")
    status       = Column(SAEnum(CompOffStatusEnum), default=CompOffStatusEnum.available, index=True)
    applied      = Column(Boolean, default=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    created_by   = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)

    employee     = relationship("Employee")


# ─────────────────────────────────────────────────────────
# TAB 6 — LEAVE PLANNING CAMPAIGN
# ─────────────────────────────────────────────────────────

class LeavePlanningCampaign(Base):
    __tablename__ = "leave_planning_campaigns"

    id                 = Column(Integer, primary_key=True, index=True)
    name               = Column(String(200), nullable=False)
    period             = Column(SAEnum(CampaignPeriodEnum), default=CampaignPeriodEnum.quarterly)
    start_date         = Column(Date, nullable=False)
    end_date           = Column(Date, nullable=False)
    target_department  = Column(String(100), default="All")
    message            = Column(Text, default="")
    status             = Column(SAEnum(CampaignStatusEnum), default=CampaignStatusEnum.active)
    created_by         = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────────────────
# TAB 7 — APPROVAL DELEGATION
# ─────────────────────────────────────────────────────────

class ApprovalDelegation(Base):
    __tablename__ = "approval_delegations"

    id             = Column(Integer, primary_key=True, index=True)
    from_approver  = Column(String(100), nullable=False)
    to_approver    = Column(String(100), nullable=False)
    start_date     = Column(Date, nullable=False)
    end_date       = Column(Date, nullable=False)
    reason         = Column(Text, default="")
    is_active      = Column(Boolean, default=True, index=True)
    created_by     = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
