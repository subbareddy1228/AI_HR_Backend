from sqlalchemy import (
    Column, Integer, String, Float, Date,
    DateTime, Text, Boolean, ForeignKey, func
)
from sqlalchemy.orm import relationship

from core.database import Base


class FinalSettlement(Base):
    """
    Core final settlement record per employee resignation / termination.
    Covers the full UI: dashboard cards, employee info, settlement timeline,
    additions, deductions, and approval workflow.
    """
    __tablename__ = "final_settlements"

    id                   = Column(Integer, primary_key=True, index=True, autoincrement=True)
    settlement_number    = Column(String(50), unique=True, nullable=False, index=True)
    # e.g. FS-2024-0001

    # ── Employee ──────────────────────────────────────────────────────────────
    employee_id          = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    employee             = relationship("Employee", back_populates="final_settlements",
                                        foreign_keys=[employee_id])

    # ── Employment dates (shown in Employee Information card) ─────────────────
    date_of_joining      = Column(Date, nullable=False)       # 2022-03-15
    last_working_day     = Column(Date, nullable=False)       # 2024-06-30

    # ── Settlement Timeline dates ─────────────────────────────────────────────
    notice_period_initiated_date = Column(Date, nullable=True)   # 15 June 2024
    document_collection_date     = Column(Date, nullable=True)   # 20 June 2024
    settlement_calculation_date  = Column(Date, nullable=True)   # 25 June 2024
    payment_processing_date      = Column(Date, nullable=True)   # Pending → filled on payment

    # ── Financial summary (dashboard cards) ───────────────────────────────────
    current_settlement   = Column(Float, nullable=False, default=0.0)   # ₹4,812
    total_additions      = Column(Float, nullable=False, default=0.0)   # ₹1,12,312
    total_deductions     = Column(Float, nullable=False, default=0.0)   # ₹1,07,500
    net_settlement       = Column(Float, nullable=False, default=0.0)   # current + additions - deductions

    # ── Status / Approval ─────────────────────────────────────────────────────
    # PENDING | APPROVED | REJECTED | PAID | CANCELLED
    status               = Column(String(50), nullable=False, default="PENDING", index=True)
    approved_by          = Column(String(255), nullable=True)
    approved_at          = Column(DateTime(timezone=True), nullable=True)
    rejected_by          = Column(String(255), nullable=True)
    rejected_at          = Column(DateTime(timezone=True), nullable=True)
    rejection_reason     = Column(Text, nullable=True)
    remarks              = Column(Text, nullable=True)

    # ── Payment ───────────────────────────────────────────────────────────────
    payment_mode         = Column(String(100), nullable=True)   # Bank Transfer / Cheque / Cash
    payment_reference    = Column(String(100), nullable=True)
    paid_at              = Column(DateTime(timezone=True), nullable=True)

    # ── Payroll linkage ───────────────────────────────────────────────────────
    # payroll_id           = Column(Integer, ForeignKey("payrolls.id"), nullable=True)
    # payroll              = relationship("Payroll", back_populates="final_settlements")
    payroll_id           = Column(Integer, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at           = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at           = Column(DateTime(timezone=True), server_default=func.now(),
                                  onupdate=func.now(), nullable=False)

    # ── Line-item relationships ───────────────────────────────────────────────
    additions            = relationship(
        "SettlementAddition",
        back_populates="settlement",
        cascade="all, delete-orphan",
        order_by="SettlementAddition.id",
    )
    deductions           = relationship(
        "SettlementDeduction",
        back_populates="settlement",
        cascade="all, delete-orphan",
        order_by="SettlementDeduction.id",
    )


class SettlementAddition(Base):
    """
    Individual addition line items that sum to total_additions.
    Examples: Leave Encashment, Gratuity, Bonus, Notice Pay, Arrears,
              Reimbursements, Ex-gratia.
    """
    __tablename__ = "settlement_additions"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    settlement_id   = Column(Integer, ForeignKey("final_settlements.id"), nullable=False, index=True)
    settlement      = relationship("FinalSettlement", back_populates="additions")

    component_name  = Column(String(200), nullable=False)   # Leave Encashment, Gratuity ...
    description     = Column(Text, nullable=True)
    amount          = Column(Float, nullable=False, default=0.0)
    is_taxable      = Column(Boolean, nullable=False, default=False)

    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                             onupdate=func.now(), nullable=False)


class SettlementDeduction(Base):
    """
    Individual deduction line items that sum to total_deductions.
    Examples: Loan Recovery, Notice Period Shortfall, Tax (TDS),
              PF Recovery, Salary Advance Recovery.
    """
    __tablename__ = "settlement_deductions"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    settlement_id   = Column(Integer, ForeignKey("final_settlements.id"), nullable=False, index=True)
    settlement      = relationship("FinalSettlement", back_populates="deductions")

    component_name  = Column(String(200), nullable=False)   # Loan Recovery, TDS ...
    description     = Column(Text, nullable=True)
    amount          = Column(Float, nullable=False, default=0.0)
    is_taxable      = Column(Boolean, nullable=False, default=False)

    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                             onupdate=func.now(), nullable=False)