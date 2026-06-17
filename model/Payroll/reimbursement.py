
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class ReimbursementType(Base):
    __tablename__ = "reimbursement_types"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(255), nullable=False, unique=True, index=True)
    description  = Column(Text, nullable=True)
    category     = Column(String(50), nullable=False, default="OTHER")
    limit_amount = Column(Numeric(14, 2), nullable=False)
    frequency    = Column(String(20), nullable=False, default="MONTHLY")
    is_taxable   = Column(Boolean, nullable=False, default=False)
    is_active    = Column(Boolean, nullable=False, default=True)
    created_at   = Column(DateTime, nullable=False, default=_utcnow)
    updated_at   = Column(DateTime, nullable=False, default=_utcnow,
                          onupdate=_utcnow)

    claims   = relationship("ReimbursementClaim",   back_populates="rtype",
                            lazy="select")
    balances = relationship("ReimbursementBalance", back_populates="rtype",
                            lazy="select")

class ReimbursementClaim(Base):

    __tablename__ = "reimbursement_claims"

    id = Column(Integer, primary_key=True, index=True)
    employee_id    = Column(
        Integer, ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    employee_code  = Column(String(50),  nullable=False)
    employee_name  = Column(String(255), nullable=False)

    type_id        = Column(
        Integer, ForeignKey("reimbursement_types.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
 
    type_name      = Column(String(255), nullable=False)
    frequency      = Column(String(20),  nullable=False)
    claimed_amount = Column(Numeric(14, 2), nullable=False)
    tax_amount     = Column(Numeric(12, 2), nullable=False, default=0)
    net_amount     = Column(Numeric(12, 2), nullable=False)   
    claim_date       = Column(DateTime, nullable=False, default=_utcnow)
    description      = Column(Text, nullable=True)
    receipt_path     = Column(String(500), nullable=True)  
    receipt_filename = Column(String(255), nullable=True)    
    status = Column(String(30), nullable=False, default="PENDING", index=True)
    manager_approval_status = Column(String(20), nullable=False, default="PENDING")
    manager_approved_by     = Column(String(255), nullable=True)
    manager_approved_at     = Column(DateTime,    nullable=True)
    manager_remarks         = Column(Text,        nullable=True)
    finance_approval_status = Column(String(20), nullable=False, default="PENDING")
    finance_approved_by     = Column(String(255), nullable=True)
    finance_approved_at     = Column(DateTime,    nullable=True)
    finance_remarks         = Column(Text,        nullable=True)
    payroll_processed      = Column(Boolean,  nullable=False, default=False)
    payroll_run_id         = Column(
        Integer, ForeignKey("payroll_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    payroll_processed_date = Column(DateTime, nullable=True)
    balance_used      = Column(Numeric(14, 2), nullable=True)
    balance_remaining = Column(Numeric(14, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow,
                        onupdate=_utcnow)

   
    rtype = relationship("ReimbursementType", back_populates="claims")
    logs  = relationship(
        "ClaimApprovalLog", back_populates="claim",
        order_by="ClaimApprovalLog.created_at",
        lazy="select",
    )


class ReimbursementBalance(Base):

    __tablename__ = "reimbursement_balances"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "type_id", "period",
            name="uq_balance_employee_type_period",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    employee_id    = Column(
        Integer, ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    employee_code  = Column(String(50),  nullable=False)
    employee_name  = Column(String(255), nullable=False)

    type_id        = Column(
        Integer, ForeignKey("reimbursement_types.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    type_name      = Column(String(255), nullable=False)

    period         = Column(String(20), nullable=False)
    limit_amount    = Column(Numeric(14, 2), nullable=False)
    used_amount     = Column(Numeric(14, 2), nullable=False, default=0)
    remaining_amount = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow,
                        onupdate=_utcnow)

    rtype = relationship("ReimbursementType", back_populates="balances")


class ClaimApprovalLog(Base):

    __tablename__ = "claim_approval_logs"

    id = Column(Integer, primary_key=True, index=True)

    claim_id = Column(
        Integer, ForeignKey("reimbursement_claims.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    from_status    = Column(String(30),  nullable=True)   
    to_status      = Column(String(30),  nullable=False)
    action_by_role = Column(String(30),  nullable=False)
    action_by_name = Column(String(255), nullable=True)
    remarks        = Column(Text,        nullable=True)

    created_at = Column(DateTime, nullable=False, default=_utcnow)
    claim = relationship("ReimbursementClaim", back_populates="logs")