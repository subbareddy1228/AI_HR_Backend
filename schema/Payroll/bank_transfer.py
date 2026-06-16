from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime


# ══════════════════════════════════════════════════════════════════════════════
#  Settings
# ══════════════════════════════════════════════════════════════════════════════

class BankTransferSettingsUpdate(BaseModel):
    auto_file_encryption   : Optional[bool] = None
    payment_notifications  : Optional[bool] = None
    auto_reconciliation    : Optional[bool] = None
    auto_backup            : Optional[bool] = None
    data_retention_days    : Optional[int]  = Field(None, ge=1, le=3650)
    default_payment_type   : Optional[str]  = None   # NEFT | RTGS | IMPS


class BankTransferSettingsResponse(BaseModel):
    id                     : int
    auto_file_encryption   : bool
    payment_notifications  : bool
    auto_reconciliation    : bool
    auto_backup            : bool
    data_retention_days    : int
    default_payment_type   : str
    created_at             : datetime
    updated_at             : datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════════
#  Payment File
# ══════════════════════════════════════════════════════════════════════════════

class PaymentFileCreate(BaseModel):
    file_name          : str   = Field(..., min_length=1, max_length=255)
    bank_name          : str   = Field(..., max_length=100)
    payment_type       : str   = Field(..., description="NEFT | RTGS | IMPS")
    payment_sub_type   : Optional[str]  = Field(None, max_length=100)
    total_amount       : float = Field(..., gt=0)
    employee_count     : int   = Field(..., gt=0)
    file_date          : date
    payroll_id         : Optional[int] = None

    @validator("payment_type")
    def validate_payment_type(cls, v: str) -> str:
        allowed = ("NEFT", "RTGS", "IMPS")
        if v.upper() not in allowed:
            raise ValueError(f"payment_type must be one of {allowed}")
        return v.upper()


class PaymentFileUpdate(BaseModel):
    file_name          : Optional[str]   = None
    bank_name          : Optional[str]   = None
    payment_type       : Optional[str]   = None
    payment_sub_type   : Optional[str]   = None
    total_amount       : Optional[float] = Field(None, gt=0)
    employee_count     : Optional[int]   = Field(None, gt=0)
    failed_count       : Optional[int]   = Field(None, ge=0)
    status             : Optional[str]   = None
    file_date          : Optional[date]  = None
    payroll_id         : Optional[int]   = None


class PaymentFileResponse(BaseModel):
    id                 : int
    file_name          : str
    reference_number   : str
    batch_id           : str
    bank_name          : str
    payment_type       : str
    payment_sub_type   : Optional[str]
    total_amount       : float
    employee_count     : int
    failed_count       : int
    status             : str
    file_date          : date
    processed_at       : Optional[datetime]
    payroll_id         : Optional[int]
    created_at         : datetime
    updated_at         : datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════════
#  Payment Transaction
# ══════════════════════════════════════════════════════════════════════════════

class PaymentTransactionCreate(BaseModel):
    payment_file_id    : int
    employee_id        : int
    employee_level_id  : Optional[str]  = Field(None, max_length=20)
    bank_name          : str            = Field(..., max_length=100)
    account_number     : str            = Field(..., max_length=50)
    amount             : float          = Field(..., gt=0)


class PaymentTransactionUpdate(BaseModel):
    status             : Optional[str]   = None
    failure_reason     : Optional[str]   = None
    retry_count        : Optional[int]   = Field(None, ge=0)
    days_pending       : Optional[int]   = Field(None, ge=0)
    processed_at       : Optional[datetime] = None


class PaymentTransactionResponse(BaseModel):
    id                 : int
    transaction_number : str
    payment_file_id    : int
    employee_id        : int
    employee_level_id  : Optional[str]
    bank_name          : str
    account_number     : str
    amount             : float
    status             : str
    failure_reason     : Optional[str]
    retry_count        : int
    days_pending       : int
    processed_at       : Optional[datetime]
    created_at         : datetime
    updated_at         : datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════════
#  Bank Reconciliation
# ══════════════════════════════════════════════════════════════════════════════

class BankReconciliationResponse(BaseModel):
    id                     : int
    payment_file_id        : int
    transaction_number     : str
    reference_number       : Optional[str]
    employee_id            : Optional[int]
    bank_account           : Optional[str]
    amount                 : float
    reconciliation_status  : str
    reconciled_at          : Optional[datetime]
    created_at             : datetime
    updated_at             : datetime

    class Config:
        from_attributes = True


class ReconciliationSummary(BaseModel):
    total_amount   : float
    matched        : int
    unmatched      : int
    pending        : int
    success_rate   : float
    details        : List[BankReconciliationResponse] = []


# ══════════════════════════════════════════════════════════════════════════════
#  Dashboard (4 cards on UI)
# ══════════════════════════════════════════════════════════════════════════════

class BankTransferDashboard(BaseModel):
    total_processed    : float   # ₹2.85Cr — this month
    successful         : int     # 158 transactions
    pending            : int     # 3 — require action
    failed             : int     # 7 — need retry


# ══════════════════════════════════════════════════════════════════════════════
#  Payment Analytics modal
# ══════════════════════════════════════════════════════════════════════════════

class MonthlyTrendItem(BaseModel):
    month          : str    # "Oct 2024"
    amount         : float  # ₹2.85Cr
    transactions   : int    # 158
    success_rate   : float  # 98.1


class PaymentAnalytics(BaseModel):
    total_amount   : float
    success_rate   : float
    transactions   : int
    avg_time_hours : float
    monthly_trends : List[MonthlyTrendItem] = []