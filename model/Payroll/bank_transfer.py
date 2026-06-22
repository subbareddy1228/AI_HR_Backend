"""
model/Payroll/bank_transfer.py
-------------------------------
Database models for Bank Transfer & Payment Processing module.

Covers:
  - PaymentFile          : batch payment files per bank (SALARY_OCT_2024_SBI, etc.)
  - PaymentFileEntry     : individual employee records inside a payment file
  - PendingPayment       : payments requiring manual attention / retry
  - BankTransfer         : single transfer record with full audit trail
  - PaymentSettings      : org-level payment configuration
  - BankReconciliation   : reconciliation session header
  - BankReconciliationEntry : per-transaction reconciliation detail
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from core.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────


class PaymentType(str, enum.Enum):
    NEFT = "NEFT"
    RTGS = "RTGS"
    IMPS = "IMPS"
    CHEQUE = "CHEQUE"
    CASH = "CASH"


class PaymentFileStatus(str, enum.Enum):
    GENERATED = "Generated"
    PROCESSED = "Processed"
    FAILED = "Failed"
    PENDING = "Pending"
    CANCELLED = "Cancelled"


class TransferStatus(str, enum.Enum):
    PENDING = "Pending"
    INITIATED = "Initiated"
    PROCESSED = "Processed"
    SUCCESS = "Success"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class ReconciliationStatus(str, enum.Enum):
    MATCHED = "Matched"
    UNMATCHED = "Unmatched"
    PENDING = "Pending"
    DISPUTED = "Disputed"


class PaymentCategory(str, enum.Enum):
    SALARY = "Salary"
    BONUS = "Bonus"
    REIMBURSEMENT = "Reimbursement"
    ADVANCE = "Advance"
    SETTLEMENT = "Settlement"


class DataRetentionDays(str, enum.Enum):
    DAYS_30 = "30 days"
    DAYS_60 = "60 days"
    DAYS_90 = "90 days"
    DAYS_180 = "180 days"
    DAYS_365 = "365 days"


# ─────────────────────────────────────────────────────────────────────────────
# PaymentFile  (e.g. SALARY_OCT_2024_SBI)
# ─────────────────────────────────────────────────────────────────────────────


class PaymentFile(Base):
    """
    Represents a bank-specific payment file generated per payroll run.
    One file per bank per payroll run (e.g. SALARY_OCT_2024_SBI – SBI NEFT).
    """

    __tablename__ = "payment_files"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    file_name = Column(String(255), nullable=False, index=True)
    batch_reference = Column(String(100), nullable=False, unique=True, index=True)  # BATCH001
    reference_number = Column(String(100), nullable=True, index=True)  # REF20241025SBI001

    # Linkage
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)

    # Bank info
    bank_name = Column(String(255), nullable=False)
    bank_code = Column(String(50), nullable=True)  # SBI, HDFC, ICICI, ALL

    # Payment details
    payment_type = Column(Enum(PaymentType), nullable=False, default=PaymentType.NEFT)
    payment_category = Column(Enum(PaymentCategory), nullable=False, default=PaymentCategory.SALARY)
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)
    total_employees = Column(Integer, nullable=False, default=0)

    # Status
    status = Column(Enum(PaymentFileStatus), nullable=False, default=PaymentFileStatus.GENERATED)
    failed_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    pending_count = Column(Integer, nullable=False, default=0)

    # Dates
    generated_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_date = Column(DateTime, nullable=True)
    value_date = Column(DateTime, nullable=True)

    # Audit
    generated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_payment_files_bank_status", "bank_name", "status"),
        Index("ix_payment_files_payroll_run", "payroll_run_id"),
        Index("ix_payment_files_generated_date", "generated_date"),
    )

    def __repr__(self) -> str:
        return f"<PaymentFile {self.file_name} | {self.bank_name} | {self.status}>"


# ─────────────────────────────────────────────────────────────────────────────
# PaymentFileEntry  (individual employee rows inside a PaymentFile)
# ─────────────────────────────────────────────────────────────────────────────


class PaymentFileEntry(Base):
    """
    Individual employee payment entry within a PaymentFile.
    Tracks per-employee transfer status with full bank details.
    """

    __tablename__ = "payment_file_entries"

    id = Column(Integer, primary_key=True, index=True)

    payment_file_id = Column(Integer, ForeignKey("payment_files.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    employee_code = Column(String(100), nullable=False)
    employee_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    designation = Column(String(255), nullable=True)

    # Bank details (snapshot at time of file generation)
    bank_name = Column(String(255), nullable=False)
    bank_account = Column(String(100), nullable=False)
    ifsc_code = Column(String(20), nullable=False)

    # Payment
    gross_salary = Column(Numeric(10, 2), nullable=True)
    deductions = Column(Numeric(10, 2), nullable=True, default=0)
    net_pay = Column(Numeric(10, 2), nullable=False)

    # Transfer outcome
    status = Column(Enum(TransferStatus), nullable=False, default=TransferStatus.PENDING)
    utr_number = Column(String(100), nullable=True)
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    transfer_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_pfe_payment_file_status", "payment_file_id", "status"),
        Index("ix_pfe_employee", "employee_id"),
    )

    def __repr__(self) -> str:
        return f"<PaymentFileEntry emp={self.employee_id} net={self.net_pay} status={self.status}>"


# ─────────────────────────────────────────────────────────────────────────────
# BankTransfer  (individual atomic transfer record with full audit trail)
# ─────────────────────────────────────────────────────────────────────────────


class BankTransfer(Base):
    """
    Atomic bank transfer record.  Can be linked to a PaymentFile or standalone.
    Maintains a full history of status transitions.
    """

    __tablename__ = "bank_transfers"

    id = Column(Integer, primary_key=True, index=True)

    # Linkage
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)
    payment_file_id = Column(Integer, ForeignKey("payment_files.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    # Snapshot fields (denormalised for audit)
    employee_code = Column(String(100), nullable=True)
    employee_name = Column(String(255), nullable=False)

    # Bank details
    bank_name = Column(String(255), nullable=False)
    bank_code = Column(String(50), nullable=True)
    bank_account = Column(String(100), nullable=False)
    ifsc_code = Column(String(20), nullable=False)

    # Payment
    payment_type = Column(Enum(PaymentType), nullable=False, default=PaymentType.NEFT)
    transfer_amount = Column(Numeric(10, 2), nullable=False)
    transfer_date = Column(DateTime, nullable=False)
    value_date = Column(DateTime, nullable=True)

    # Outcome
    status = Column(Enum(TransferStatus), nullable=False, default=TransferStatus.PENDING)
    utr_number = Column(String(100), nullable=True, index=True)
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_retry_at = Column(DateTime, nullable=True)

    # Metadata
    remarks = Column(Text, nullable=True)
    initiated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    initiated_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_bt_employee_status", "employee_id", "status"),
        Index("ix_bt_payroll_run", "payroll_run_id"),
        Index("ix_bt_transfer_date", "transfer_date"),
        Index("ix_bt_utr", "utr_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<BankTransfer id={self.id} emp={self.employee_id} "
            f"amount={self.transfer_amount} status={self.status}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PendingPayment  (requires manual attention or retry)
# ─────────────────────────────────────────────────────────────────────────────


class PendingPayment(Base):
    """
    Tracks payments that are blocked (insufficient balance, validation error,
    server error) and need operator action before being retried.
    """

    __tablename__ = "pending_payments"

    id = Column(Integer, primary_key=True, index=True)

    bank_transfer_id = Column(Integer, ForeignKey("bank_transfers.id"), nullable=True)
    payment_file_id = Column(Integer, ForeignKey("payment_files.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    employee_code = Column(String(100), nullable=True)
    employee_name = Column(String(255), nullable=False)

    # Bank info
    bank_name = Column(String(255), nullable=False)
    bank_account = Column(String(100), nullable=False)

    # Payment
    payment_type = Column(Enum(PaymentType), nullable=False, default=PaymentType.NEFT)
    amount = Column(Numeric(10, 2), nullable=False)

    # Failure details
    failure_reason = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    last_retry_at = Column(DateTime, nullable=True)
    days_pending = Column(Integer, nullable=False, default=0)

    # Status
    is_resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    resolution_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_pp_employee_resolved", "employee_id", "is_resolved"),
        Index("ix_pp_payment_file", "payment_file_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<PendingPayment emp={self.employee_id} amount={self.amount} "
            f"retries={self.retry_count} resolved={self.is_resolved}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PaymentSettings  (org-level configuration – singleton row)
# ─────────────────────────────────────────────────────────────────────────────


class PaymentSettings(Base):
    """
    Organisation-wide payment settings (one row per org).
    Maps to the Payment Settings modal in the UI.
    """

    __tablename__ = "payment_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Security Settings
    auto_file_encryption = Column(Boolean, nullable=False, default=True)
    payment_notifications = Column(Boolean, nullable=False, default=True)
    auto_reconciliation = Column(Boolean, nullable=False, default=False)

    # Backup & Retention
    auto_backup = Column(Boolean, nullable=False, default=True)
    data_retention_period = Column(
        Enum(DataRetentionDays),
        nullable=False,
        default=DataRetentionDays.DAYS_90,
    )

    # Default Payment Settings
    default_payment_type = Column(
        Enum(PaymentType),
        nullable=False,
        default=PaymentType.NEFT,
    )

    # Audit
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<PaymentSettings default_type={self.default_payment_type}>"


# ─────────────────────────────────────────────────────────────────────────────
# BankReconciliation  (reconciliation session header)
# ─────────────────────────────────────────────────────────────────────────────


class BankReconciliation(Base):
    """
    Header record for a bank statement reconciliation run.
    Aggregates matched / unmatched / pending counts.
    """

    __tablename__ = "bank_reconciliations"

    id = Column(Integer, primary_key=True, index=True)

    payment_file_id = Column(Integer, ForeignKey("payment_files.id"), nullable=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)
    bank_name = Column(String(255), nullable=True)

    # Totals
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)
    matched_count = Column(Integer, nullable=False, default=0)
    unmatched_count = Column(Integer, nullable=False, default=0)
    pending_count = Column(Integer, nullable=False, default=0)
    success_rate = Column(Numeric(5, 2), nullable=True)  # e.g. 98.10

    # State
    is_verified = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Statement file meta
    statement_file_name = Column(String(255), nullable=True)
    statement_date = Column(DateTime, nullable=True)

    run_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    run_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_br_payment_file", "payment_file_id"),
        Index("ix_br_run_at", "run_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<BankReconciliation id={self.id} matched={self.matched_count} "
            f"unmatched={self.unmatched_count} verified={self.is_verified}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# BankReconciliationEntry  (per-transaction reconciliation line)
# ─────────────────────────────────────────────────────────────────────────────


class BankReconciliationEntry(Base):
    """
    Stores the reconciliation result for each individual transaction
    within a BankReconciliation session.
    """

    __tablename__ = "bank_reconciliation_entries"

    id = Column(Integer, primary_key=True, index=True)

    reconciliation_id = Column(Integer, ForeignKey("bank_reconciliations.id"), nullable=False)
    bank_transfer_id = Column(Integer, ForeignKey("bank_transfers.id"), nullable=True)

    # Transaction identity
    transaction_id = Column(String(100), nullable=False)      # TXN001
    reference_number = Column(String(100), nullable=True)     # REF20241025SBI001

    # Employee details
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    employee_code = Column(String(100), nullable=True)         # LEV098
    employee_name = Column(String(255), nullable=False)

    # Bank details
    bank_name = Column(String(255), nullable=True)
    bank_account = Column(String(100), nullable=True)

    # Amounts
    expected_amount = Column(Numeric(10, 2), nullable=True)
    actual_amount = Column(Numeric(10, 2), nullable=False)

    # Reconciliation outcome
    status = Column(
        Enum(ReconciliationStatus),
        nullable=False,
        default=ReconciliationStatus.PENDING,
    )
    mismatch_reason = Column(Text, nullable=True)

    # Statement date
    statement_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_bre_recon_status", "reconciliation_id", "status"),
        Index("ix_bre_transaction_id", "transaction_id"),
        Index("ix_bre_employee", "employee_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<BankReconciliationEntry txn={self.transaction_id} "
            f"emp={self.employee_name} status={self.status}>"
        )