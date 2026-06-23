

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


class PaymentFile(Base):

    __tablename__ = "payment_files"

    id = Column(Integer, primary_key=True, index=True)

    file_name = Column(String(255), nullable=False, index=True)
    batch_reference = Column(String(100), nullable=False, unique=True, index=True)  # BATCH001
    reference_number = Column(String(100), nullable=True, index=True)  # REF20241025SBI001

    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)

    bank_name = Column(String(255), nullable=False)
    bank_code = Column(String(50), nullable=True)  # SBI, HDFC, ICICI, ALL

    payment_type = Column(Enum(PaymentType), nullable=False, default=PaymentType.NEFT)
    payment_category = Column(Enum(PaymentCategory), nullable=False, default=PaymentCategory.SALARY)
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)
    total_employees = Column(Integer, nullable=False, default=0)

    status = Column(Enum(PaymentFileStatus), nullable=False, default=PaymentFileStatus.GENERATED)
    failed_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    pending_count = Column(Integer, nullable=False, default=0)

    generated_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_date = Column(DateTime, nullable=True)
    value_date = Column(DateTime, nullable=True)

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


class PaymentFileEntry(Base):

    __tablename__ = "payment_file_entries"

    id = Column(Integer, primary_key=True, index=True)

    payment_file_id = Column(Integer, ForeignKey("payment_files.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    employee_code = Column(String(100), nullable=False)
    employee_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    designation = Column(String(255), nullable=True)

    bank_name = Column(String(255), nullable=False)
    bank_account = Column(String(100), nullable=False)
    ifsc_code = Column(String(20), nullable=False)

    gross_salary = Column(Numeric(10, 2), nullable=True)
    deductions = Column(Numeric(10, 2), nullable=True, default=0)
    net_pay = Column(Numeric(10, 2), nullable=False)

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



class BankTransfer(Base):

    __tablename__ = "bank_transfers"

    id = Column(Integer, primary_key=True, index=True)

    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)
    payment_file_id = Column(Integer, ForeignKey("payment_files.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    employee_code = Column(String(100), nullable=True)
    employee_name = Column(String(255), nullable=False)
    bank_name = Column(String(255), nullable=False)
    bank_code = Column(String(50), nullable=True)
    bank_account = Column(String(100), nullable=False)
    ifsc_code = Column(String(20), nullable=False)

    payment_type = Column(Enum(PaymentType), nullable=False, default=PaymentType.NEFT)
    transfer_amount = Column(Numeric(10, 2), nullable=False)
    transfer_date = Column(DateTime, nullable=False)
    value_date = Column(DateTime, nullable=True)

    status = Column(Enum(TransferStatus), nullable=False, default=TransferStatus.PENDING)
    utr_number = Column(String(100), nullable=True, index=True)
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_retry_at = Column(DateTime, nullable=True)
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


class PendingPayment(Base):

    __tablename__ = "pending_payments"

    id = Column(Integer, primary_key=True, index=True)

    bank_transfer_id = Column(Integer, ForeignKey("bank_transfers.id"), nullable=True)
    payment_file_id = Column(Integer, ForeignKey("payment_files.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    employee_code = Column(String(100), nullable=True)
    employee_name = Column(String(255), nullable=False)


    bank_name = Column(String(255), nullable=False)
    bank_account = Column(String(100), nullable=False)

    payment_type = Column(Enum(PaymentType), nullable=False, default=PaymentType.NEFT)
    amount = Column(Numeric(10, 2), nullable=False)
    failure_reason = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    last_retry_at = Column(DateTime, nullable=True)
    days_pending = Column(Integer, nullable=False, default=0)

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



class PaymentSettings(Base):

    __tablename__ = "payment_settings"

    id = Column(Integer, primary_key=True, index=True)
    auto_file_encryption = Column(Boolean, nullable=False, default=True)
    payment_notifications = Column(Boolean, nullable=False, default=True)
    auto_reconciliation = Column(Boolean, nullable=False, default=False)

    auto_backup = Column(Boolean, nullable=False, default=True)
    data_retention_period = Column(
        Enum(DataRetentionDays),
        nullable=False,
        default=DataRetentionDays.DAYS_90,
    )

    default_payment_type = Column(
        Enum(PaymentType),
        nullable=False,
        default=PaymentType.NEFT,
    )

    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<PaymentSettings default_type={self.default_payment_type}>"



class BankReconciliation(Base):

    __tablename__ = "bank_reconciliations"
    id = Column(Integer, primary_key=True, index=True)
    payment_file_id = Column(Integer, ForeignKey("payment_files.id"), nullable=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)
    bank_name = Column(String(255), nullable=True)
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)
    matched_count = Column(Integer, nullable=False, default=0)
    unmatched_count = Column(Integer, nullable=False, default=0)
    pending_count = Column(Integer, nullable=False, default=0)
    success_rate = Column(Numeric(5, 2), nullable=True)  # e.g. 98.10
    is_verified = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
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



class BankReconciliationEntry(Base):

    __tablename__ = "bank_reconciliation_entries"

    id = Column(Integer, primary_key=True, index=True)
    reconciliation_id = Column(Integer, ForeignKey("bank_reconciliations.id"), nullable=False)
    bank_transfer_id = Column(Integer, ForeignKey("bank_transfers.id"), nullable=True)
    transaction_id = Column(String(100), nullable=False)      
    reference_number = Column(String(100), nullable=True)    
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    employee_code = Column(String(100), nullable=True)         
    employee_name = Column(String(255), nullable=False)
    bank_name = Column(String(255), nullable=True)
    bank_account = Column(String(100), nullable=True)
    expected_amount = Column(Numeric(10, 2), nullable=True)
    actual_amount = Column(Numeric(10, 2), nullable=False)

    status = Column(
        Enum(ReconciliationStatus),
        nullable=False,
        default=ReconciliationStatus.PENDING,
    )
    mismatch_reason = Column(Text, nullable=True)


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