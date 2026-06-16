from sqlalchemy import (
    Column, Integer, String, Float, Date,
    DateTime, Text, Boolean, ForeignKey, func
)
from sqlalchemy.orm import relationship

from core.database import Base


class ReimbursementType(Base):
    """Master table — Reimbursement Types (Master tab)"""
    __tablename__ = "reimbursement_types"

    id            = Column(Integer, primary_key=True, index=True, autoincrement=True)
    component     = Column(String(200), nullable=False)        # Medical Reimbursement
    description   = Column(Text, nullable=True)                # Medical expenses reimbursement
    category      = Column(String(100), nullable=False)        # Health / Communication / Travel / Education / Other
    limit_amount  = Column(Float, nullable=False)              # ₹20,000
    frequency     = Column(String(50), nullable=False)         # Monthly / Yearly / Quarterly / Ad-hoc
    is_taxable    = Column(Boolean, nullable=False, default=False)  # Taxable / Non-Taxable
    is_active     = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(),
                           onupdate=func.now(), nullable=False)

    claims        = relationship("ReimbursementClaim", back_populates="reimbursement_type")
    balances      = relationship("ReimbursementBalance", back_populates="reimbursement_type")


class ReimbursementClaim(Base):
    """Claims table — Claims tab"""
    __tablename__ = "reimbursement_claims"

    id                    = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id           = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    reimbursement_type_id = Column(Integer, ForeignKey("reimbursement_types.id"), nullable=False)

    amount                = Column(Float, nullable=False)
    claim_date            = Column(Date, nullable=False)
    description           = Column(Text, nullable=True)
    receipt_url           = Column(String(500), nullable=True)
    receipt_filename      = Column(String(255), nullable=True)

    # Status: PENDING | FINANCE_REVIEW | APPROVED | REJECTED
    status                = Column(String(50), nullable=False, default="PENDING")

    # Two-stage approval — Manager then Finance
    manager_status        = Column(String(50), nullable=False, default="PENDING")   # PENDING | APPROVED | REJECTED
    manager_approved_by   = Column(String(255), nullable=True)
    manager_approved_date = Column(Date, nullable=True)
    manager_remarks       = Column(Text, nullable=True)

    finance_status        = Column(String(50), nullable=False, default="PENDING")   # PENDING | APPROVED | REJECTED
    finance_approved_by   = Column(String(255), nullable=True)
    finance_approved_date = Column(Date, nullable=True)
    finance_remarks       = Column(Text, nullable=True)

    # Payroll linkage
    payroll_id            = Column(Integer, ForeignKey("payrolls.id"), nullable=True)
    payroll_processed_date = Column(Date, nullable=True)

    # Tax
    is_taxable            = Column(Boolean, nullable=False, default=False)
    tax_amount            = Column(Float, nullable=False, default=0.0)

    created_at            = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at            = Column(DateTime(timezone=True), server_default=func.now(),
                                   onupdate=func.now(), nullable=False)

    employee              = relationship("Employee", back_populates="reimbursement_claims",
                                         foreign_keys=[employee_id])
    reimbursement_type    = relationship("ReimbursementType", back_populates="claims")
    payroll               = relationship("Payroll", back_populates="reimbursement_claims")


class ReimbursementBalance(Base):
    """Balances per employee per type per period — Balances tab"""
    __tablename__ = "reimbursement_balances"

    id                    = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id           = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    reimbursement_type_id = Column(Integer, ForeignKey("reimbursement_types.id"), nullable=False)

    period                = Column(String(20), nullable=False)   # "2024" for Yearly, "2024-04" for Monthly
    limit_amount          = Column(Float, nullable=False)
    used_amount           = Column(Float, nullable=False, default=0.0)
    remaining_amount      = Column(Float, nullable=False, default=0.0)  # limit - used

    created_at            = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at            = Column(DateTime(timezone=True), server_default=func.now(),
                                   onupdate=func.now(), nullable=False)

    employee              = relationship("Employee", back_populates="reimbursement_balances",
                                         foreign_keys=[employee_id])
    reimbursement_type    = relationship("ReimbursementType", back_populates="balances")


# Temporary alias for old imports
Reimbursement = ReimbursementClaim