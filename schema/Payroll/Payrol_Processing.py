
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from model.Payroll.Payroll_Processing import (
    CalculationMethod,
    ComponentType,
    CycleType,
    LockAction,
    PayPeriod,
    PayrollStatus,
)


class PayrollConfigCreate(BaseModel):
    # Cycle Settings
    cycle_type:       CycleType = CycleType.MONTHLY
    pay_period:       PayPeriod = PayPeriod.STANDARD_MONTH
    period_start_day: Optional[int] = Field(None, ge=1, le=31)
    period_end_day:   Optional[int] = Field(None, ge=1, le=31)

    # Schedule
    processing_day: int = Field(25, ge=1, le=31,
                                description="Day of month payroll is processed")
    payment_day:    int = Field(30, ge=1, le=31,
                                description="Day of month salaries are credited")


    enable_off_cycle_payroll:         bool = True
    enable_advance_payroll_scheduling: bool = False

    @model_validator(mode="after")
    def validate_custom_period(self) -> "PayrollConfigCreate":
        if self.pay_period == PayPeriod.CUSTOM_DATE_RANGE:
            if not self.period_start_day or not self.period_end_day:
                raise ValueError(
                    "period_start_day and period_end_day are required "
                    "when pay_period is custom_date_range."
                )
        return self


class PayrollConfigUpdate(BaseModel):
    cycle_type:       Optional[CycleType] = None
    pay_period:       Optional[PayPeriod] = None
    period_start_day: Optional[int] = Field(None, ge=1, le=31)
    period_end_day:   Optional[int] = Field(None, ge=1, le=31)
    processing_day:   Optional[int] = Field(None, ge=1, le=31)
    payment_day:      Optional[int] = Field(None, ge=1, le=31)
    enable_off_cycle_payroll:         Optional[bool] = None
    enable_advance_payroll_scheduling: Optional[bool] = None
    updated_by:       Optional[int]  = None


class PayrollConfigResponse(BaseModel):
    id:             int
    cycle_type:     CycleType
    pay_period:     PayPeriod
    period_start_day: Optional[int]
    period_end_day:   Optional[int]
    processing_day: int
    payment_day:    int
    enable_off_cycle_payroll:         bool
    enable_advance_payroll_scheduling: bool
    payroll_status: PayrollStatus
    locked_by:      Optional[int]
    locked_at:      Optional[datetime]
    lock_reason:    Optional[str]
    created_at:     datetime
    updated_at:     Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class LockPayrollRequest(BaseModel):
    reason:      Optional[str] = Field(None, max_length=500)
    actioned_by: Optional[int] = Field(None, description="Employee ID performing the action")


class PayrollLockResponse(BaseModel):
    payroll_status:  PayrollStatus
    locked_by:       Optional[int]
    locked_at:       Optional[datetime]
    lock_reason:     Optional[str]
    message:         str

    model_config = ConfigDict(from_attributes=True)


class PayrollLockLogResponse(BaseModel):
    id:              int
    action:          LockAction
    reason:          Optional[str]
    actioned_by:     Optional[int]
    actioned_at:     datetime
    previous_status: str
    new_status:      str

    model_config = ConfigDict(from_attributes=True)


class CommissionConfigCreate(BaseModel):
    enable_commission_calculation: bool    = False
    commission_rate_percent:       Optional[float]   = Field(None, ge=0, le=100)
    bonus_threshold:               Optional[Decimal] = Field(None, ge=0)
    updated_by:                    Optional[int]     = None

    @model_validator(mode="after")
    def validate_rate_required(self) -> "CommissionConfigCreate":
        if self.enable_commission_calculation:
            if self.commission_rate_percent is None:
                raise ValueError(
                    "commission_rate_percent is required when commission calculation is enabled."
                )
        return self


class CommissionConfigUpdate(BaseModel):
    enable_commission_calculation: Optional[bool]    = None
    commission_rate_percent:       Optional[float]   = Field(None, ge=0, le=100)
    bonus_threshold:               Optional[Decimal] = Field(None, ge=0)
    updated_by:                    Optional[int]     = None


class CommissionConfigResponse(BaseModel):
    id:                            int
    enable_commission_calculation: bool
    commission_rate_percent:       Optional[float]
    bonus_threshold:               Optional[Decimal]
    created_at:                    datetime
    updated_at:                    Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class StatutorySettingsCreate(BaseModel):
    enable_tax_calculation:  bool = True
    enable_epf_contribution: bool = True
    enable_esi_contribution:  bool = True
    enable_tds_deduction:     bool = True
    updated_by:               Optional[int] = None


class StatutorySettingsUpdate(BaseModel):
    enable_tax_calculation:  Optional[bool] = None
    enable_epf_contribution: Optional[bool] = None
    enable_esi_contribution:  Optional[bool] = None
    enable_tds_deduction:     Optional[bool] = None
    updated_by:               Optional[int] = None


class StatutorySettingsResponse(BaseModel):
    id:                      int
    enable_tax_calculation:  bool
    enable_epf_contribution: bool
    enable_esi_contribution:  bool
    enable_tds_deduction:     bool
    created_at:              datetime
    updated_at:              Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PayrollComponentCreate(BaseModel):
    component_name:     str             = Field(..., min_length=2, max_length=255)
    component_type:     ComponentType   = ComponentType.EARNINGS
    calculation_method: CalculationMethod = CalculationMethod.PERCENTAGE
    value:              float           = Field(..., ge=0,
                                               description="Percent (0-100) or flat amount")
    is_taxable:         bool            = False
    display_order:      int             = Field(0, ge=0)
    created_by:         Optional[int]   = None

    @field_validator("component_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def validate_percent_cap(self) -> "PayrollComponentCreate":
        if self.calculation_method == CalculationMethod.PERCENTAGE and self.value > 100:
            raise ValueError("Percent value must be ≤ 100.")
        return self


class PayrollComponentUpdate(BaseModel):
    component_name:     Optional[str]               = Field(None, min_length=2, max_length=255)
    component_type:     Optional[ComponentType]     = None
    calculation_method: Optional[CalculationMethod] = None
    value:              Optional[float]             = Field(None, ge=0)
    is_taxable:         Optional[bool]              = None
    display_order:      Optional[int]               = Field(None, ge=0)
    is_active:          Optional[bool]              = None
    updated_by:         Optional[int]               = None


class PayrollComponentResponse(BaseModel):
    id:                 int
    component_name:     str
    component_type:     ComponentType
    calculation_method: CalculationMethod
    value:              float
    is_taxable:         bool
    display_order:      int
    is_active:          bool
    created_at:         datetime
    updated_at:         Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ComponentsTableResponse(BaseModel):

    earnings:   list[PayrollComponentResponse] = []
    deductions: list[PayrollComponentResponse] = []
    total:      int = 0


class PayrollProcessingPageResponse(BaseModel):

    config:     Optional[PayrollConfigResponse]     = None
    commission: Optional[CommissionConfigResponse]  = None
    statutory:  Optional[StatutorySettingsResponse] = None
    components: ComponentsTableResponse             = ComponentsTableResponse()

    model_config = ConfigDict(from_attributes=True)