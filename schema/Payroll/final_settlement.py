from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime


# ══════════════════════════════════════════════════════════════════════════════
#  Settlement Addition
# ══════════════════════════════════════════════════════════════════════════════

class SettlementAdditionCreate(BaseModel):
    component_name : str   = Field(..., min_length=1, max_length=200)
    description    : Optional[str]  = None
    amount         : float = Field(..., ge=0)
    is_taxable     : bool  = False


class SettlementAdditionUpdate(BaseModel):
    component_name : Optional[str]   = Field(None, min_length=1, max_length=200)
    description    : Optional[str]   = None
    amount         : Optional[float] = Field(None, ge=0)
    is_taxable     : Optional[bool]  = None


class SettlementAdditionResponse(BaseModel):
    id             : int
    settlement_id  : int
    component_name : str
    description    : Optional[str]
    amount         : float
    is_taxable     : bool
    created_at     : datetime
    updated_at     : datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════════
#  Settlement Deduction
# ══════════════════════════════════════════════════════════════════════════════

class SettlementDeductionCreate(BaseModel):
    component_name : str   = Field(..., min_length=1, max_length=200)
    description    : Optional[str]  = None
    amount         : float = Field(..., ge=0)
    is_taxable     : bool  = False


class SettlementDeductionUpdate(BaseModel):
    component_name : Optional[str]   = Field(None, min_length=1, max_length=200)
    description    : Optional[str]   = None
    amount         : Optional[float] = Field(None, ge=0)
    is_taxable     : Optional[bool]  = None


class SettlementDeductionResponse(BaseModel):
    id             : int
    settlement_id  : int
    component_name : str
    description    : Optional[str]
    amount         : float
    is_taxable     : bool
    created_at     : datetime
    updated_at     : datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════════
#  Final Settlement — Create / Update
# ══════════════════════════════════════════════════════════════════════════════

class FinalSettlementCreate(BaseModel):
    employee_id                  : int
    date_of_joining              : date
    last_working_day             : date
    notice_period_initiated_date : Optional[date] = None
    document_collection_date     : Optional[date] = None
    settlement_calculation_date  : Optional[date] = None
    current_settlement           : float = Field(0.0, ge=0)
    remarks                      : Optional[str] = None
    payroll_id                   : Optional[int] = None

    @validator("last_working_day")
    def lwt_after_doj(cls, v, values):
        doj = values.get("date_of_joining")
        if doj and v <= doj:
            raise ValueError("Last working day must be after date of joining.")
        return v


class FinalSettlementUpdate(BaseModel):
    date_of_joining              : Optional[date]  = None
    last_working_day             : Optional[date]  = None
    notice_period_initiated_date : Optional[date]  = None
    document_collection_date     : Optional[date]  = None
    settlement_calculation_date  : Optional[date]  = None
    payment_processing_date      : Optional[date]  = None
    current_settlement           : Optional[float] = Field(None, ge=0)
    remarks                      : Optional[str]   = None
    payment_mode                 : Optional[str]   = None
    payment_reference            : Optional[str]   = None
    payroll_id                   : Optional[int]   = None


# ── Approval / Rejection ──────────────────────────────────────────────────────

class SettlementApproveRequest(BaseModel):
    approved_by : Optional[str] = None
    remarks     : Optional[str] = None


class SettlementRejectRequest(BaseModel):
    rejected_by      : Optional[str] = None
    rejection_reason : str = Field(..., min_length=5)


# ── Payment ───────────────────────────────────────────────────────────────────

class SettlementPayRequest(BaseModel):
    payment_mode      : str = Field(..., min_length=1)
    payment_reference : Optional[str] = None
    remarks           : Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
#  Response schemas
# ══════════════════════════════════════════════════════════════════════════════

class FinalSettlementResponse(BaseModel):
    id                           : int
    settlement_number            : str
    employee_id                  : int
    date_of_joining              : date
    last_working_day             : date
    notice_period_initiated_date : Optional[date]
    document_collection_date     : Optional[date]
    settlement_calculation_date  : Optional[date]
    payment_processing_date      : Optional[date]
    current_settlement           : float
    total_additions              : float
    total_deductions             : float
    net_settlement               : float
    status                       : str
    approved_by                  : Optional[str]
    approved_at                  : Optional[datetime]
    rejected_by                  : Optional[str]
    rejected_at                  : Optional[datetime]
    rejection_reason             : Optional[str]
    remarks                      : Optional[str]
    payment_mode                 : Optional[str]
    payment_reference            : Optional[str]
    paid_at                      : Optional[datetime]
    payroll_id                   : Optional[int]
    created_at                   : datetime
    updated_at                   : datetime

    class Config:
        from_attributes = True


class FinalSettlementDetailResponse(FinalSettlementResponse):
    """Full detail with all addition and deduction line items."""
    additions  : List[SettlementAdditionResponse]  = []
    deductions : List[SettlementDeductionResponse] = []


# ══════════════════════════════════════════════════════════════════════════════
#  Dashboard summary (4 cards on the UI)
# ══════════════════════════════════════════════════════════════════════════════

class FinalSettlementDashboard(BaseModel):
    current_settlement : float
    total_additions    : float
    total_deductions   : float
    approval_status    : str


# ══════════════════════════════════════════════════════════════════════════════
#  Report response
# ══════════════════════════════════════════════════════════════════════════════

class FinalSettlementReport(BaseModel):
    settlement_number            : str
    employee_id                  : int
    date_of_joining              : date
    last_working_day             : date
    current_settlement           : float
    total_additions              : float
    total_deductions             : float
    net_settlement               : float
    status                       : str
    notice_period_initiated_date : Optional[date]
    document_collection_date     : Optional[date]
    settlement_calculation_date  : Optional[date]
    payment_processing_date      : Optional[date]
    additions                    : List[SettlementAdditionResponse]  = []
    deductions                   : List[SettlementDeductionResponse] = []

    class Config:
        from_attributes = True