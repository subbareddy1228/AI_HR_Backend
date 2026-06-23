
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator



from model.Payroll.bank_transfer import (
    DataRetentionDays,
    PaymentCategory,
    PaymentFileStatus,
    PaymentType,
    ReconciliationStatus,
    TransferStatus,
)




class PaymentFileCreate(BaseModel):
    file_name: str = Field(..., max_length=255)
    batch_reference: str = Field(..., max_length=100)
    reference_number: Optional[str] = Field(None, max_length=100)

    payroll_run_id: Optional[int] = None

    bank_name: str = Field(..., max_length=255)
    bank_code: Optional[str] = Field(None, max_length=50)

    payment_type: PaymentType = PaymentType.NEFT
    payment_category: PaymentCategory = PaymentCategory.SALARY
    total_amount: Decimal = Field(..., ge=0)
    total_employees: int = Field(..., ge=0)

    value_date: Optional[datetime] = None
    remarks: Optional[str] = None


class PaymentFileUpdate(BaseModel):
    status: Optional[PaymentFileStatus] = None
    failed_count: Optional[int] = None
    success_count: Optional[int] = None
    pending_count: Optional[int] = None
    processed_date: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    remarks: Optional[str] = None


class PaymentFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    batch_reference: str
    reference_number: Optional[str]
    payroll_run_id: Optional[int]
    bank_name: str
    bank_code: Optional[str]
    payment_type: PaymentType
    payment_category: PaymentCategory
    total_amount: Decimal
    total_employees: int
    status: PaymentFileStatus
    failed_count: int
    success_count: int
    pending_count: int
    generated_date: datetime
    processed_date: Optional[datetime]
    value_date: Optional[datetime]
    generated_by: Optional[int]
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]



class PaymentFileEntryCreate(BaseModel):
    payment_file_id: int
    employee_id: int
    employee_code: str = Field(..., max_length=100)
    employee_name: str = Field(..., max_length=255)
    department: Optional[str] = None
    designation: Optional[str] = None
    bank_name: str = Field(..., max_length=255)
    bank_account: str = Field(..., max_length=100)
    ifsc_code: str = Field(..., max_length=20)
    gross_salary: Optional[Decimal] = None
    deductions: Decimal = Field(default=Decimal("0"))
    net_pay: Decimal = Field(..., ge=0)


class PaymentFileEntryUpdate(BaseModel):
    status: Optional[TransferStatus] = None
    utr_number: Optional[str] = Field(None, max_length=100)
    failure_reason: Optional[str] = None
    retry_count: Optional[int] = None
    transfer_date: Optional[datetime] = None


class PaymentFileEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_file_id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department: Optional[str]
    designation: Optional[str]
    bank_name: str
    bank_account: str
    ifsc_code: str
    gross_salary: Optional[Decimal]
    deductions: Optional[Decimal]
    net_pay: Decimal
    status: TransferStatus
    utr_number: Optional[str]
    failure_reason: Optional[str]
    retry_count: int
    transfer_date: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class BankTransferCreate(BaseModel):
    payroll_run_id: Optional[int] = None
    payment_file_id: Optional[int] = None
    employee_id: int
    employee_code: Optional[str] = Field(None, max_length=100)
    employee_name: str = Field(..., max_length=255)
    bank_name: str = Field(..., max_length=255)
    bank_code: Optional[str] = Field(None, max_length=50)
    bank_account: str = Field(..., max_length=100)
    ifsc_code: str = Field(..., max_length=20)
    payment_type: PaymentType = PaymentType.NEFT
    transfer_amount: Decimal = Field(..., gt=0)
    transfer_date: datetime
    value_date: Optional[datetime] = None
    remarks: Optional[str] = None
    initiated_by: Optional[int] = None


class BankTransferUpdate(BaseModel):
    status: Optional[TransferStatus] = None
    utr_number: Optional[str] = Field(None, max_length=100)
    failure_reason: Optional[str] = None
    transfer_date: Optional[datetime] = None
    value_date: Optional[datetime] = None
    transfer_amount: Optional[Decimal] = Field(None, gt=0)
    remarks: Optional[str] = None
    completed_at: Optional[datetime] = None


class TransferStatusPayload(BaseModel):
 

    utr_number: Optional[str] = Field(None, max_length=100)
    failure_reason: Optional[str] = None
    remarks: Optional[str] = None


class BankTransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payroll_run_id: Optional[int]
    payment_file_id: Optional[int]
    employee_id: int
    employee_code: Optional[str]
    employee_name: str
    bank_name: str
    bank_code: Optional[str]
    bank_account: str
    ifsc_code: str
    payment_type: PaymentType
    transfer_amount: Decimal
    transfer_date: datetime
    value_date: Optional[datetime]
    status: TransferStatus
    utr_number: Optional[str]
    failure_reason: Optional[str]
    retry_count: int
    last_retry_at: Optional[datetime]
    remarks: Optional[str]
    initiated_by: Optional[int]
    initiated_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]



class PendingPaymentCreate(BaseModel):
    bank_transfer_id: Optional[int] = None
    payment_file_id: Optional[int] = None
    employee_id: int
    employee_code: Optional[str] = None
    employee_name: str
    bank_name: str
    bank_account: str
    payment_type: PaymentType = PaymentType.NEFT
    amount: Decimal = Field(..., gt=0)
    failure_reason: Optional[str] = None
    error_code: Optional[str] = None
    max_retries: int = 3
    days_pending: int = 0


class PendingPaymentResolve(BaseModel):
    resolution_note: Optional[str] = None
    resolved_by: Optional[int] = None


class PendingPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bank_transfer_id: Optional[int]
    payment_file_id: Optional[int]
    employee_id: int
    employee_code: Optional[str]
    employee_name: str
    bank_name: str
    bank_account: str
    payment_type: PaymentType
    amount: Decimal
    failure_reason: Optional[str]
    error_code: Optional[str]
    retry_count: int
    max_retries: int
    last_retry_at: Optional[datetime]
    days_pending: int
    is_resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[int]
    resolution_note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class PaymentSettingsUpsert(BaseModel):
    auto_file_encryption: bool = True
    payment_notifications: bool = True
    auto_reconciliation: bool = False
    auto_backup: bool = True
    data_retention_period: DataRetentionDays = DataRetentionDays.DAYS_90
    default_payment_type: PaymentType = PaymentType.NEFT
    updated_by: Optional[int] = None


class PaymentSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auto_file_encryption: bool
    payment_notifications: bool
    auto_reconciliation: bool
    auto_backup: bool
    data_retention_period: DataRetentionDays
    default_payment_type: PaymentType
    updated_by: Optional[int]
    updated_at: Optional[datetime]
    created_at: datetime



class BankReconciliationCreate(BaseModel):
    payment_file_id: Optional[int] = None
    payroll_run_id: Optional[int] = None
    bank_name: Optional[str] = None
    total_amount: Decimal = Field(default=Decimal("0"), ge=0)
    statement_file_name: Optional[str] = None
    statement_date: Optional[datetime] = None
    run_by: Optional[int] = None
    notes: Optional[str] = None


class BankReconciliationVerify(BaseModel):
    verified_by: int
    notes: Optional[str] = None


class BankReconciliationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_file_id: Optional[int]
    payroll_run_id: Optional[int]
    bank_name: Optional[str]
    total_amount: Decimal
    matched_count: int
    unmatched_count: int
    pending_count: int
    success_rate: Optional[Decimal]
    is_verified: bool
    verified_at: Optional[datetime]
    verified_by: Optional[int]
    statement_file_name: Optional[str]
    statement_date: Optional[datetime]
    run_at: datetime
    run_by: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]




class BankReconciliationEntryCreate(BaseModel):
    reconciliation_id: int
    bank_transfer_id: Optional[int] = None
    transaction_id: str = Field(..., max_length=100)
    reference_number: Optional[str] = Field(None, max_length=100)
    employee_id: Optional[int] = None
    employee_code: Optional[str] = None
    employee_name: str
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    expected_amount: Optional[Decimal] = None
    actual_amount: Decimal
    status: ReconciliationStatus = ReconciliationStatus.PENDING
    mismatch_reason: Optional[str] = None
    statement_date: Optional[datetime] = None


class BankReconciliationEntryUpdate(BaseModel):
    status: Optional[ReconciliationStatus] = None
    mismatch_reason: Optional[str] = None
    actual_amount: Optional[Decimal] = None


class BankReconciliationEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reconciliation_id: int
    bank_transfer_id: Optional[int]
    transaction_id: str
    reference_number: Optional[str]
    employee_id: Optional[int]
    employee_code: Optional[str]
    employee_name: str
    bank_name: Optional[str]
    bank_account: Optional[str]
    expected_amount: Optional[Decimal]
    actual_amount: Decimal
    status: ReconciliationStatus
    mismatch_reason: Optional[str]
    statement_date: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]



class MonthlyTrendItem(BaseModel):
    month: str                 
    amount: Decimal
    transactions: int
    success_count: int


class BankDistributionItem(BaseModel):
    bank_name: str
    amount: Decimal
    percentage: Optional[float] = None


class PaymentTypeDistributionItem(BaseModel):
    payment_type: PaymentType
    count: int
    percentage: Optional[float] = None


class TransactionStatusSummary(BaseModel):
    processed: int
    failed: int
    pending: int
    generated: int


class PaymentAnalyticsResponse(BaseModel):
    total_amount: Decimal
    success_rate: float            
    total_transactions: int
    avg_processing_time_hrs: float
    monthly_trends: List[MonthlyTrendItem]
    bank_distribution: List[BankDistributionItem]
    payment_type_distribution: List[PaymentTypeDistributionItem]
    transaction_status: TransactionStatusSummary


class DashboardSummaryResponse(BaseModel):
    total_processed: Decimal
    successful_count: int
    pending_count: int
    failed_count: int


class GeneratePaymentFileRequest(BaseModel):


    payroll_run_id: int
    bank_names: Optional[List[str]] = None          
    payment_type: Optional[PaymentType] = None       
    value_date: Optional[datetime] = None
    remarks: Optional[str] = None


class BulkStatusUpdateRequest(BaseModel):


    entry_ids: List[int] = Field(..., min_length=1)
    status: TransferStatus
    utr_number: Optional[str] = None
    failure_reason: Optional[str] = None
    remarks: Optional[str] = None


class ExportRequest(BaseModel):


    format: str = Field(default="csv", pattern="^(csv|pdf)$")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    bank_name: Optional[str] = None
    status: Optional[PaymentFileStatus] = None
    payment_method: Optional[PaymentType] = None