"""
Final Settlement Processing Model
==================================
Covers every data entity visible in the UI:
  • Settlement header      (FinalSettlement)
  • Notice period block    (SettlementNoticePeriod)
  • Salary breakdown       (SettlementSalaryBreakdown)
  • Leave encashment       (SettlementLeaveEncashment)
  • Bonus pro-rata         (SettlementBonus)
  • Gratuity               (SettlementGratuity)
  • Asset tracking         (SettlementAsset)
  • Deductions             (SettlementDeduction)
  • Payment info           (SettlementPayment)
  • Document checklist     (SettlementDocument)
  • Approval workflow log  (SettlementApprovalLog)
  • Settlement Timeline    (SettlementTimeline)

Status lifecycle:
  Draft → Pending Approval → Approved → Paid
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from core.database import Base


# ──────────────────────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────────────────────

class SettlementStatus(str, enum.Enum):
    DRAFT            = "Draft"
    PENDING_APPROVAL = "Pending Approval"
    APPROVED         = "Approved"
    PAID             = "Paid"
    CANCELLED        = "Cancelled"


class ExitType(str, enum.Enum):
    RESIGNATION  = "Resignation"
    TERMINATION  = "Termination"
    RETIREMENT   = "Retirement"
    ABSCONDING   = "Absconding"
    CONTRACT_END = "Contract End"


class AssetReturnStatus(str, enum.Enum):
    PENDING  = "pending"
    RETURNED = "returned"
    LOST     = "lost"
    DAMAGED  = "damaged"


class AssetCondition(str, enum.Enum):
    GOOD    = "Good"
    DAMAGED = "Damaged"
    LOST    = "Lost"


class PaymentMethod(str, enum.Enum):
    BANK_TRANSFER = "Bank Transfer"
    CHEQUE        = "Cheque"
    CASH          = "Cash"
    NEFT          = "NEFT"
    RTGS          = "RTGS"
    IMPS          = "IMPS"


class PaymentStatus(str, enum.Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class TimelineEvent(str, enum.Enum):
    NOTICE_PERIOD_INITIATED = "Notice Period Initiated"
    DOCUMENT_COLLECTION     = "Document Collection"
    SETTLEMENT_CALCULATION  = "Settlement Calculation"
    PAYMENT_PROCESSING      = "Payment Processing"
    COMPLETED               = "Completed"


class ApprovalAction(str, enum.Enum):
    SUBMITTED  = "Submitted"
    APPROVED   = "Approved"
    REJECTED   = "Rejected"
    RECALCULATED = "Recalculated"
    PAID       = "Paid"
    CANCELLED  = "Cancelled"


# ──────────────────────────────────────────────────────────────────────────────
# Main Settlement Header
# ──────────────────────────────────────────────────────────────────────────────

class FinalSettlement(Base):
    """
    One record per employee exit.  All child blocks reference this via
    settlement_id FK, making partial lazy-loads cheap.
    """
    __tablename__ = "final_settlements"

    id                   = Column(Integer, primary_key=True, index=True)
    settlement_code      = Column(String(30), unique=True, nullable=False, index=True)
    # e.g. FS-2024-0001

    # ── Employee snapshot (denormalised for auditability) ─────────────────────
    employee_id          = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"),
                                  nullable=False, index=True)
    employee_code        = Column(String(50),  nullable=False)
    employee_name        = Column(String(255), nullable=False)
    department           = Column(String(150), nullable=True)
    designation          = Column(String(150), nullable=True)
    date_of_joining      = Column(Date, nullable=True)
    uan_number           = Column(String(30),  nullable=True)
    pf_number            = Column(String(50),  nullable=True)
    pan_number           = Column(String(20),  nullable=True)

    # ── Exit context ──────────────────────────────────────────────────────────
    exit_type            = Column(Enum(ExitType), nullable=False,
                                  default=ExitType.RESIGNATION)
    resignation_date     = Column(Date, nullable=True)
    last_working_date    = Column(Date, nullable=False)
    notice_period_required_days = Column(Integer, default=90)

    # ── Computed totals (updated on every recalculate) ────────────────────────
    total_additions      = Column(Numeric(14, 2), default=0)
    total_deductions     = Column(Numeric(14, 2), default=0)
    net_settlement       = Column(Numeric(14, 2), default=0)   # additions - deductions

    # ── Workflow ───────────────────────────────────────────────────────────────
    status               = Column(Enum(SettlementStatus), nullable=False,
                                  default=SettlementStatus.DRAFT, index=True)
    initiated_by         = Column(Integer, ForeignKey("employees.id"), nullable=True)
    initiated_by_name    = Column(String(255), nullable=True)
    initiated_date       = Column(Date, nullable=True)
    approved_by          = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_by_name     = Column(String(255), nullable=True)
    approved_date        = Column(Date, nullable=True)
    rejection_reason     = Column(Text, nullable=True)
    remarks              = Column(Text, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    last_calculated_at   = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at           = Column(DateTime, default=datetime.utcnow,
                                  onupdate=datetime.utcnow, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    notice_period   = relationship("SettlementNoticePeriod",  back_populates="settlement",
                                   uselist=False, cascade="all, delete-orphan")
    salary_breakdown = relationship("SettlementSalaryBreakdown", back_populates="settlement",
                                    uselist=False, cascade="all, delete-orphan")
    leave_encashment = relationship("SettlementLeaveEncashment", back_populates="settlement",
                                    uselist=False, cascade="all, delete-orphan")
    bonus            = relationship("SettlementBonus", back_populates="settlement",
                                    uselist=False, cascade="all, delete-orphan")
    gratuity         = relationship("SettlementGratuity", back_populates="settlement",
                                    uselist=False, cascade="all, delete-orphan")
    deduction        = relationship("SettlementDeduction", back_populates="settlement",
                                    uselist=False, cascade="all, delete-orphan")
    assets           = relationship("SettlementAsset", back_populates="settlement",
                                    cascade="all, delete-orphan")
    payment          = relationship("SettlementPayment", back_populates="settlement",
                                    uselist=False, cascade="all, delete-orphan")
    documents        = relationship("SettlementDocument", back_populates="settlement",
                                    cascade="all, delete-orphan")
    timeline         = relationship("SettlementTimeline", back_populates="settlement",
                                    cascade="all, delete-orphan",
                                    order_by="SettlementTimeline.event_date")
    approval_logs    = relationship("SettlementApprovalLog", back_populates="settlement",
                                    cascade="all, delete-orphan",
                                    order_by="SettlementApprovalLog.actioned_at")

    __table_args__ = (
        Index("ix_final_settlements_employee_status", "employee_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<FinalSettlement {self.settlement_code} | {self.employee_name} | {self.status}>"


# ──────────────────────────────────────────────────────────────────────────────
# Notice Period Block
# ──────────────────────────────────────────────────────────────────────────────

class SettlementNoticePeriod(Base):
    __tablename__ = "settlement_notice_periods"

    id                   = Column(Integer, primary_key=True, index=True)
    settlement_id        = Column(Integer, ForeignKey("final_settlements.id",
                                  ondelete="CASCADE"), unique=True, nullable=False)

    verified             = Column(Boolean, default=False)
    days_served          = Column(Integer, default=0)
    required_days        = Column(Integer, default=90)
    shortfall_days       = Column(Integer, default=0)    # computed: required - served
    recovery_amount      = Column(Numeric(12, 2), default=0)  # shortfall × daily rate
    verification_date    = Column(Date, nullable=True)
    verified_by_name     = Column(String(255), nullable=True)
    waiver_approved      = Column(Boolean, default=False)
    waiver_remarks       = Column(Text, nullable=True)

    settlement = relationship("FinalSettlement", back_populates="notice_period")


# ──────────────────────────────────────────────────────────────────────────────
# Salary Breakdown
# ──────────────────────────────────────────────────────────────────────────────

class SettlementSalaryBreakdown(Base):
    __tablename__ = "settlement_salary_breakdowns"

    id                   = Column(Integer, primary_key=True, index=True)
    settlement_id        = Column(Integer, ForeignKey("final_settlements.id",
                                  ondelete="CASCADE"), unique=True, nullable=False)

    basic                = Column(Numeric(12, 2), default=0)
    hra                  = Column(Numeric(12, 2), default=0)
    special_allowance    = Column(Numeric(12, 2), default=0)
    other_allowances     = Column(Numeric(12, 2), default=0)
    days_worked          = Column(Integer, default=0)
    working_days_in_month = Column(Integer, default=30)
    daily_rate           = Column(Numeric(12, 2), default=0)   # gross / working_days
    salary_for_days      = Column(Numeric(12, 2), default=0)   # daily_rate × days_worked
    arrears              = Column(Numeric(12, 2), default=0)
    last_working_day     = Column(Date, nullable=True)
    payment_due_date     = Column(Date, nullable=True)

    settlement = relationship("FinalSettlement", back_populates="salary_breakdown")


# ──────────────────────────────────────────────────────────────────────────────
# Leave Encashment
# ──────────────────────────────────────────────────────────────────────────────

class SettlementLeaveEncashment(Base):
    __tablename__ = "settlement_leave_encashments"

    id                    = Column(Integer, primary_key=True, index=True)
    settlement_id         = Column(Integer, ForeignKey("final_settlements.id",
                                   ondelete="CASCADE"), unique=True, nullable=False)

    earned_leave_balance  = Column(Numeric(6, 2), default=0)
    casual_leave_balance  = Column(Numeric(6, 2), default=0)
    sick_leave_balance    = Column(Numeric(6, 2), default=0)
    encashment_rate       = Column(Numeric(12, 2), default=0)   # per day
    # Only earned leave is encashable (by policy)
    encashable_days       = Column(Numeric(6, 2), default=0)
    total_encashment      = Column(Numeric(12, 2), default=0)
    encashment_policy     = Column(String(255), default="Earned leave only")

    settlement = relationship("FinalSettlement", back_populates="leave_encashment")


# ──────────────────────────────────────────────────────────────────────────────
# Bonus / Pro-Rata
# ──────────────────────────────────────────────────────────────────────────────

class SettlementBonus(Base):
    __tablename__ = "settlement_bonuses"

    id                   = Column(Integer, primary_key=True, index=True)
    settlement_id        = Column(Integer, ForeignKey("final_settlements.id",
                                  ondelete="CASCADE"), unique=True, nullable=False)

    annual_bonus         = Column(Numeric(12, 2), default=0)
    pro_rata_days        = Column(Integer, default=0)
    pro_rata_bonus       = Column(Numeric(12, 2), default=0)   # (annual / 365) × days
    is_eligible          = Column(Boolean, default=True)
    calculation_method   = Column(String(255), default="Pro-rata based on days worked")
    remarks              = Column(Text, nullable=True)

    settlement = relationship("FinalSettlement", back_populates="bonus")


# ──────────────────────────────────────────────────────────────────────────────
# Gratuity
# ──────────────────────────────────────────────────────────────────────────────

class SettlementGratuity(Base):
    __tablename__ = "settlement_gratuities"

    id                   = Column(Integer, primary_key=True, index=True)
    settlement_id        = Column(Integer, ForeignKey("final_settlements.id",
                                  ondelete="CASCADE"), unique=True, nullable=False)

    completed_years      = Column(Numeric(5, 2), default=0)
    last_drawn_basic     = Column(Numeric(12, 2), default=0)
    gratuity_amount      = Column(Numeric(12, 2), default=0)
    # Formula: (basic / 26) × 15 × completed_years  (only if >= 5 years)
    is_eligible          = Column(Boolean, default=False)
    eligibility_years    = Column(Integer, default=5)
    remarks              = Column(Text, nullable=True)

    settlement = relationship("FinalSettlement", back_populates="gratuity")


# ──────────────────────────────────────────────────────────────────────────────
# Deductions Block (aggregated)
# ──────────────────────────────────────────────────────────────────────────────

class SettlementDeduction(Base):
    __tablename__ = "settlement_deductions"

    id                     = Column(Integer, primary_key=True, index=True)
    settlement_id          = Column(Integer, ForeignKey("final_settlements.id",
                                    ondelete="CASCADE"), unique=True, nullable=False)

    loan_outstanding       = Column(Numeric(12, 2), default=0)
    advance_amount         = Column(Numeric(12, 2), default=0)
    notice_period_recovery = Column(Numeric(12, 2), default=0)   # computed from notice block
    asset_penalty          = Column(Numeric(12, 2), default=0)   # computed from asset block
    id_card_deduction      = Column(Numeric(12, 2), default=0)
    uniform_deduction      = Column(Numeric(12, 2), default=0)
    other_deductions       = Column(Numeric(12, 2), default=0)
    tds_deduction          = Column(Numeric(12, 2), default=0)
    penalty_amount         = Column(Numeric(12, 2), default=0)
    total_deductions       = Column(Numeric(12, 2), default=0)   # sum of all above
    deduction_remarks      = Column(Text, nullable=True)

    settlement = relationship("FinalSettlement", back_populates="deduction")


# ──────────────────────────────────────────────────────────────────────────────
# Asset Return Tracking
# ──────────────────────────────────────────────────────────────────────────────

class SettlementAsset(Base):
    __tablename__ = "settlement_assets"

    id             = Column(Integer, primary_key=True, index=True)
    settlement_id  = Column(Integer, ForeignKey("final_settlements.id",
                            ondelete="CASCADE"), nullable=False, index=True)

    asset_id       = Column(String(50),  nullable=False)      # e.g. AST001
    asset_name     = Column(String(255), nullable=False)
    asset_tag      = Column(String(100), nullable=True)
    category       = Column(String(100), nullable=True)       # Laptop, Mobile, etc.
    return_status  = Column(Enum(AssetReturnStatus), default=AssetReturnStatus.PENDING)
    return_date    = Column(Date, nullable=True)
    condition      = Column(Enum(AssetCondition), nullable=True)
    penalty        = Column(Numeric(10, 2), default=0)
    remarks        = Column(Text, nullable=True)

    settlement = relationship("FinalSettlement", back_populates="assets")

    __table_args__ = (
        Index("ix_settlement_assets_settlement", "settlement_id"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Payment Info
# ──────────────────────────────────────────────────────────────────────────────

class SettlementPayment(Base):
    __tablename__ = "settlement_payments"

    id                = Column(Integer, primary_key=True, index=True)
    settlement_id     = Column(Integer, ForeignKey("final_settlements.id",
                               ondelete="CASCADE"), unique=True, nullable=False)

    payment_method    = Column(Enum(PaymentMethod), default=PaymentMethod.BANK_TRANSFER)
    payment_mode      = Column(String(20), default="NEFT")          # NEFT / RTGS / IMPS
    account_number    = Column(String(30), nullable=True)
    ifsc_code         = Column(String(20), nullable=True)
    bank_name         = Column(String(150), nullable=True)
    payment_date      = Column(Date, nullable=True)
    status            = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    reference_number  = Column(String(100), nullable=True)
    utr_number        = Column(String(100), nullable=True)
    processed_by_name = Column(String(255), nullable=True)
    processed_date    = Column(DateTime, nullable=True)
    payment_proof_url = Column(Text, nullable=True)
    remarks           = Column(Text, nullable=True)

    settlement = relationship("FinalSettlement", back_populates="payment")


# ──────────────────────────────────────────────────────────────────────────────
# Document Checklist
# ──────────────────────────────────────────────────────────────────────────────

class SettlementDocument(Base):
    __tablename__ = "settlement_documents"

    id              = Column(Integer, primary_key=True, index=True)
    settlement_id   = Column(Integer, ForeignKey("final_settlements.id",
                             ondelete="CASCADE"), nullable=False, index=True)

    document_type   = Column(String(100), nullable=False)
    # Form16 / Form19 / Form10C / Experience Letter / Relieving Letter
    generated       = Column(Boolean, default=False)
    generated_date  = Column(DateTime, nullable=True)
    issued          = Column(Boolean, default=False)
    issued_date     = Column(DateTime, nullable=True)
    financial_year  = Column(String(10), nullable=True)    # for Form16
    pf_account_no   = Column(String(50), nullable=True)    # for Form19 / Form10C
    download_url    = Column(Text, nullable=True)
    generated_by    = Column(String(255), nullable=True)

    settlement = relationship("FinalSettlement", back_populates="documents")


# ──────────────────────────────────────────────────────────────────────────────
# Timeline
# ──────────────────────────────────────────────────────────────────────────────

class SettlementTimeline(Base):
    __tablename__ = "settlement_timelines"

    id            = Column(Integer, primary_key=True, index=True)
    settlement_id = Column(Integer, ForeignKey("final_settlements.id",
                           ondelete="CASCADE"), nullable=False, index=True)

    event         = Column(Enum(TimelineEvent), nullable=False)
    event_date    = Column(Date, nullable=True)
    is_completed  = Column(Boolean, default=False)
    notes         = Column(Text, nullable=True)

    settlement = relationship("FinalSettlement", back_populates="timeline")


# ──────────────────────────────────────────────────────────────────────────────
# Approval Audit Log
# ──────────────────────────────────────────────────────────────────────────────

class SettlementApprovalLog(Base):
    __tablename__ = "settlement_approval_logs"

    id            = Column(Integer, primary_key=True, index=True)
    settlement_id = Column(Integer, ForeignKey("final_settlements.id",
                           ondelete="CASCADE"), nullable=False, index=True)

    action        = Column(Enum(ApprovalAction), nullable=False)
    actioned_by   = Column(Integer, ForeignKey("employees.id"), nullable=True)
    actioned_by_name = Column(String(255), nullable=True)
    actioned_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    from_status   = Column(String(50), nullable=True)
    to_status     = Column(String(50), nullable=True)
    remarks       = Column(Text, nullable=True)

    settlement = relationship("FinalSettlement", back_populates="approval_logs")

    __table_args__ = (
        Index("ix_settlement_approval_logs_settlement", "settlement_id"),
    )
