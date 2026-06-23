from sqlalchemy import (
    Column, Integer, String, Float, Date,
    DateTime, Text, Boolean, ForeignKey, func
)
from sqlalchemy.orm import relationship

from core.database import Base


class BankTransferSettings(Base):
    """
    Payment Settings modal — single-row config table.
    Security, Backup & Retention, Default Payment Settings.
    """
    __tablename__ = "bank_transfer_settings"

    id                          = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Security Settings
    auto_file_encryption        = Column(Boolean, nullable=False, default=True)
    payment_notifications       = Column(Boolean, nullable=False, default=True)
    auto_reconciliation         = Column(Boolean, nullable=False, default=False)

    # Backup & Retention
    auto_backup                 = Column(Boolean, nullable=False, default=True)
    data_retention_days         = Column(Integer, nullable=False, default=90)   # 90 days

    # Default Payment Settings
    default_payment_type        = Column(String(20), nullable=False, default="NEFT")
    # NEFT | RTGS | IMPS

    created_at                  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at                  = Column(DateTime(timezone=True), server_default=func.now(),
                                         onupdate=func.now(), nullable=False)


class PaymentFile(Base):
    """
    Payment Files table — each row is one batch payment file
    e.g. SALARY_OCT_2024_SBI, BONUS_OCT_2024_ALL
    """
    __tablename__ = "payment_files"

    id                  = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # File identification
    file_name           = Column(String(255), nullable=False, index=True)
    # SALARY_OCT_2024_SBI
    reference_number    = Column(String(100), unique=True, nullable=False, index=True)
    # REF20241025SBI001
    batch_id            = Column(String(50), nullable=False, index=True)
    # BATCH001

    # Bank & payment info
    bank_name           = Column(String(100), nullable=False)
    # State Bank of India | HDFC Bank | ICICI Bank | All Banks
    payment_type        = Column(String(20), nullable=False)
    # NEFT | RTGS | IMPS
    payment_sub_type    = Column(String(100), nullable=True)
    # Bulk Transfer | Bonus Payment

    # Financials
    total_amount        = Column(Float, nullable=False, default=0.0)
    employee_count      = Column(Integer, nullable=False, default=0)
    failed_count        = Column(Integer, nullable=False, default=0)

    # Status: GENERATED | PROCESSED | FAILED | PARTIALLY_FAILED
    status              = Column(String(50), nullable=False, default="GENERATED", index=True)

    # Dates
    file_date           = Column(Date, nullable=False)
    processed_at        = Column(DateTime(timezone=True), nullable=True)

    # Payroll linkage
    # payroll_id          = Column(Integer, ForeignKey("payrolls.id"), nullable=True)
    # payroll             = relationship("Payroll", back_populates="payment_files")
    payroll_id          = Column(Integer, nullable=True)

    created_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(),
                                 onupdate=func.now(), nullable=False)

    # Transactions in this file
    transactions        = relationship(
        "PaymentTransaction",
        back_populates="payment_file",
        cascade="all, delete-orphan",
        order_by="PaymentTransaction.id",
    )
    # Reconciliation records
    reconciliations     = relationship(
        "BankReconciliation",
        back_populates="payment_file",
        cascade="all, delete-orphan",
    )


class PaymentTransaction(Base):
    """
    Individual employee payment within a payment file.
    Also represents Pending Payments section rows.
    """
    __tablename__ = "payment_transactions"

    id                  = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_number  = Column(String(50), unique=True, nullable=False, index=True)
    # TXN001, TXN002 ...

    payment_file_id     = Column(Integer, ForeignKey("payment_files.id"), nullable=False, index=True)
    payment_file        = relationship("PaymentFile", back_populates="transactions")

    # Employee
    employee_id         = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    employee            = relationship("Employee", back_populates="payment_transactions",
                                       foreign_keys=[employee_id])
    employee_level_id   = Column(String(20), nullable=True)    # LEV101, LEV102 ...

    # Bank account (masked in UI: XXXX-XXXX-1234)
    bank_name           = Column(String(100), nullable=False)
    account_number      = Column(String(50), nullable=False)   # stored masked

    # Financials
    amount              = Column(Float, nullable=False)

    # Status: PENDING | SUCCESS | FAILED | RETRY
    status              = Column(String(50), nullable=False, default="PENDING", index=True)

    # Failure details (Pending Payments section)
    failure_reason      = Column(String(255), nullable=True)
    # Insufficient balance | Account validation failed | Bank server error
    retry_count         = Column(Integer, nullable=False, default=0)
    days_pending        = Column(Integer, nullable=False, default=0)

    # Timestamps
    processed_at        = Column(DateTime(timezone=True), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(),
                                 onupdate=func.now(), nullable=False)


class BankReconciliation(Base):
    """
    Bank Statement Reconciliation modal —
    Each row maps a bank transaction to a payment transaction.
    """
    __tablename__ = "bank_reconciliations"

    id                  = Column(Integer, primary_key=True, index=True, autoincrement=True)

    payment_file_id     = Column(Integer, ForeignKey("payment_files.id"), nullable=False, index=True)
    payment_file        = relationship("PaymentFile", back_populates="reconciliations")

    transaction_number  = Column(String(50), nullable=False)   # TXN001
    reference_number    = Column(String(100), nullable=True)   # REF20241025SBI001
    employee_id         = Column(Integer, ForeignKey("employees.id"), nullable=True)
    employee            = relationship("Employee", foreign_keys=[employee_id])
    bank_account        = Column(String(50), nullable=True)    # 40579942875
    amount              = Column(Float, nullable=False)

    # Status: MATCHED | UNMATCHED | PENDING
    reconciliation_status = Column(String(50), nullable=False, default="PENDING")

    reconciled_at       = Column(DateTime(timezone=True), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(),
                                 onupdate=func.now(), nullable=False)

#Alias
BankTransfer = PaymentFile