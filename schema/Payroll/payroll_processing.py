from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
#  Payroll Config
# ══════════════════════════════════════════════════════════════════════════════

class PayrollConfigUpdate(BaseModel):
    """All fields optional — UI sends only what changed."""
    # Payroll Cycle Settings
    cycle_type                : Optional[str]   = Field(None, max_length=50)
    pay_period                : Optional[str]   = Field(None, max_length=100)

    # Payroll Schedule
    processing_day            : Optional[int]   = Field(None, ge=1, le=28)
    payment_day               : Optional[int]   = Field(None, ge=1, le=31)
    enable_off_cycle_payroll  : Optional[bool]  = None
    enable_advance_scheduling : Optional[bool]  = None

    # Sales / Commission
    enable_commission         : Optional[bool]  = None
    commission_rate           : Optional[float] = Field(None, ge=0, le=100)
    bonus_threshold           : Optional[float] = Field(None, ge=0)

    # Statutory Compliance
    enable_tax_calculation    : Optional[bool]  = None
    enable_epf_contribution   : Optional[bool]  = None
    enable_esi_contribution   : Optional[bool]  = None
    enable_tds_deduction      : Optional[bool]  = None


class PayrollConfigResponse(BaseModel):
    id                        : int
    payroll_status            : str
    cycle_type                : str
    pay_period                : str
    processing_day            : int
    payment_day               : int
    enable_off_cycle_payroll  : bool
    enable_advance_scheduling : bool
    enable_commission         : bool
    commission_rate           : float
    bonus_threshold           : float
    enable_tax_calculation    : bool
    enable_epf_contribution   : bool
    enable_esi_contribution   : bool
    enable_tds_deduction      : bool
    created_at                : datetime
    updated_at                : datetime

    class Config:
        from_attributes = True


# ── Lock / Unlock ─────────────────────────────────────────────────────────────

class PayrollLockRequest(BaseModel):
    reason : Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
#  Salary Component
# ══════════════════════════════════════════════════════════════════════════════

class SalaryComponentCreate(BaseModel):
    component_name   : str   = Field(..., min_length=1, max_length=200)
    component_type   : str   = Field(..., description="earnings | deductions")
    calculation_type : str   = Field(..., description="percentage | fixed")
    value            : float = Field(..., gt=0)
    is_taxable       : bool  = False
    is_active        : bool  = True
    description      : Optional[str] = None
    display_order    : int   = Field(0, ge=0)

    @validator("component_type")
    def validate_component_type(cls, v: str) -> str:
        allowed = ("earnings", "deductions")
        if v.lower() not in allowed:
            raise ValueError(f"component_type must be one of {allowed}")
        return v.lower()

    @validator("calculation_type")
    def validate_calculation_type(cls, v: str) -> str:
        allowed = ("percentage", "fixed")
        if v.lower() not in allowed:
            raise ValueError(f"calculation_type must be one of {allowed}")
        return v.lower()

    @validator("value")
    def validate_percentage_range(cls, v: float, values) -> float:
        if values.get("calculation_type") == "percentage" and v > 100:
            raise ValueError("Percentage value cannot exceed 100")
        return v


class SalaryComponentUpdate(BaseModel):
    component_name   : Optional[str]   = Field(None, min_length=1, max_length=200)
    component_type   : Optional[str]   = None
    calculation_type : Optional[str]   = None
    value            : Optional[float] = Field(None, gt=0)
    is_taxable       : Optional[bool]  = None
    is_active        : Optional[bool]  = None
    description      : Optional[str]   = None
    display_order    : Optional[int]   = Field(None, ge=0)


class SalaryComponentResponse(BaseModel):
    id               : int
    component_name   : str
    component_type   : str
    calculation_type : str
    value            : float
    is_taxable       : bool
    is_active        : bool
    description      : Optional[str]
    display_order    : int
    created_at       : datetime
    updated_at       : datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════════
#  Combined config export (Export Config button on UI)
# ══════════════════════════════════════════════════════════════════════════════

class PayrollFullConfigResponse(BaseModel):
    config              : PayrollConfigResponse
    salary_components   : List[SalaryComponentResponse]