

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from model.HR_Operations.notice_period import (
    ApprovalStatus,
    CounterOfferStatus,
    NoticeStatus,
    ResignationReason,
    ResignationWorkflowStep,
)


class _TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime



class NoticePeriodCreate(BaseModel):
    employee_id:          int
    resignation_date:     date
    resignation_reason:   Optional[ResignationReason] = None
    resignation_letter:   Optional[str]               = None
    notice_start_date:    date
    notice_period_days:   int = Field(..., gt=0, description="Contractual notice period in days")
    monthly_salary:       Optional[Decimal]           = Field(None, gt=0)
    remarks:              Optional[str]               = None
    created_by:           Optional[int]               = None

    @model_validator(mode="after")
    def set_notice_end_date(self) -> "NoticePeriodCreate":
 
        return self


class NoticePeriodUpdate(BaseModel):
    resignation_reason:   Optional[ResignationReason] = None
    resignation_letter:   Optional[str]               = None
    actual_lwd:           Optional[date]               = None
    serving_days:         Optional[int]                = Field(None, ge=0)
    days_remaining:       Optional[int]                = Field(None, ge=0)
    manager_acknowledged: Optional[bool]               = None
    hr_reviewed:          Optional[bool]               = None
    monthly_salary:       Optional[Decimal]            = Field(None, gt=0)
    buyout_amount:        Optional[Decimal]            = Field(None, ge=0)
    status:               Optional[NoticeStatus]       = None
    remarks:              Optional[str]                = None


class NoticePeriodSummary(BaseModel):

    id:                   int
    employee_id:          int
    employee_name:        Optional[str]  = None
    department:           Optional[str]  = None
    resignation_date:     date
    notice_start_date:    date
    notice_end_date:      date
    notice_period_days:   int
    days_remaining:       Optional[int]
    status:               NoticeStatus
    manager_acknowledged: bool
    hr_reviewed:          bool

    model_config = ConfigDict(from_attributes=True)


class NoticePeriodResponse(NoticePeriodSummary, _TimestampMixin):

    resignation_reason:   Optional[ResignationReason]
    resignation_letter:   Optional[str]
    actual_lwd:           Optional[date]
    serving_days:         Optional[int]
    monthly_salary:       Optional[Decimal]
    buyout_amount:        Optional[Decimal]
    remarks:              Optional[str]
    created_by:           Optional[int]

    model_config = ConfigDict(from_attributes=True)


class BuyoutRequestCreate(BaseModel):
    employee_id:     int
    notice_period_id: int
    requested_date:  date
    days_to_buyout:  int   = Field(..., gt=0)
    monthly_salary:  Decimal = Field(..., gt=0)
    requested_lwd:   date
    remarks:         Optional[str] = None

    @model_validator(mode="after")
    def compute_buyout_amount(self) -> "BuyoutRequestCreate":

        return self


class BuyoutApprovalUpdate(BaseModel):

    approver_role:    str  = Field(..., pattern="^(MANAGER|HR|FINANCE)$")
    approval_status:  ApprovalStatus
    rejection_reason: Optional[str] = None
    remarks:          Optional[str] = None


class BuyoutRequestResponse(_TimestampMixin):
    id:               int
    notice_period_id: int
    employee_id:      int
    requested_date:   date
    days_to_buyout:   int
    monthly_salary:   Decimal
    buyout_amount:    Decimal
    requested_lwd:    date
    manager_status:   ApprovalStatus
    hr_status:        ApprovalStatus
    finance_status:   ApprovalStatus
    approval_status:  ApprovalStatus
    approved_by:      Optional[int]
    approved_at:      Optional[datetime]
    rejection_reason: Optional[str]
    remarks:          Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WaiverRequestCreate(BaseModel):
    employee_id:      int
    notice_period_id: int
    requested_date:   date
    waiver_days:      int  = Field(..., gt=0)
    reason:           str  = Field(..., min_length=10)
    document_urls:    Optional[List[str]] = None
    remarks:          Optional[str]       = None

    @field_validator("document_urls", mode="before")
    @classmethod
    def serialise_docs(cls, v: Any) -> Optional[str]:

        if isinstance(v, list):
            return json.dumps(v)
        return v


class WaiverApprovalUpdate(BaseModel):
    approver_role:    str = Field(..., pattern="^(MANAGER|HR|DIRECTOR)$")
    approval_status:  ApprovalStatus
    rejection_reason: Optional[str] = None
    remarks:          Optional[str] = None


class WaiverRequestResponse(_TimestampMixin):
    id:               int
    notice_period_id: int
    employee_id:      int
    requested_date:   date
    waiver_days:      int
    reason:           str
    document_urls:    Optional[List[str]] = None
    manager_status:   ApprovalStatus
    hr_status:        ApprovalStatus
    director_status:  ApprovalStatus
    approval_status:  ApprovalStatus
    approved_by:      Optional[int]
    approved_at:      Optional[datetime]
    rejection_reason: Optional[str]
    remarks:          Optional[str]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("document_urls", mode="before")
    @classmethod
    def parse_docs(cls, v: Any) -> Optional[List[str]]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


class CounterOfferCreate(BaseModel):
    employee_id:           int
    notice_period_id:      int
    current_salary:        Decimal = Field(..., gt=0)
    offered_salary:        Decimal = Field(..., gt=0)
    additional_benefits:   Optional[str]  = None
    role_change:           Optional[str]  = None
    retention_probability: Optional[int]  = Field(None, ge=0, le=100)
    offer_date:            date
    expiry_date:           Optional[date] = None
    created_by:            Optional[int]  = None


class CounterOfferResponseUpdate(BaseModel):

    status:            CounterOfferStatus
    employee_response: Optional[str] = None


class CounterOfferResponse(_TimestampMixin):
    id:                    int
    notice_period_id:      int
    employee_id:           int
    current_salary:        Decimal
    offered_salary:        Decimal
    hike_percentage:       Optional[Decimal]
    additional_benefits:   Optional[str]
    role_change:           Optional[str]
    retention_probability: Optional[int]
    offer_date:            date
    expiry_date:           Optional[date]
    status:                CounterOfferStatus
    employee_response:     Optional[str]
    responded_at:          Optional[datetime]
    created_by:            Optional[int]

    model_config = ConfigDict(from_attributes=True)


class ExtensionRequestCreate(BaseModel):
    employee_id:      int
    notice_period_id: int
    requested_by:     str  = Field(..., pattern="^(EMPLOYEE|COMPANY)$")
    requested_date:   date
    extension_days:   int  = Field(..., gt=0)
    reason:           str  = Field(..., min_length=10)
    remarks:          Optional[str] = None


class ExtensionApprovalUpdate(BaseModel):
    approval_status:  ApprovalStatus
    rejection_reason: Optional[str] = None
    remarks:          Optional[str] = None
    approved_by:      Optional[int] = None


class ExtensionRequestResponse(_TimestampMixin):
    id:               int
    notice_period_id: int
    employee_id:      int
    requested_by:     str
    requested_date:   date
    extension_days:   int
    new_end_date:     date
    reason:           str
    approval_status:  ApprovalStatus
    approved_by:      Optional[int]
    approved_at:      Optional[datetime]
    rejection_reason: Optional[str]
    remarks:          Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WorkflowStepCreate(BaseModel):
    notice_period_id: int
    employee_id:      int
    step:             ResignationWorkflowStep
    performed_by:     Optional[int] = None
    comments:         Optional[str] = None


class WorkflowStepResponse(BaseModel):
    id:               int
    notice_period_id: int
    employee_id:      int
    step:             ResignationWorkflowStep
    step_date:        datetime
    performed_by:     Optional[int]
    comments:         Optional[str]
    is_current_step:  bool
    created_at:       datetime

    model_config = ConfigDict(from_attributes=True)



class LWDCalculatorRequest(BaseModel):
    resignation_date:  date
    notice_period_days: int = Field(..., gt=0)

class LWDCalculatorResponse(BaseModel):
    resignation_date:  date
    notice_period_days: int
    last_working_date: date
    calendar_days:     int


class BuyoutCalculatorRequest(BaseModel):
    monthly_salary: Decimal = Field(..., gt=0)
    days_to_buyout: int     = Field(..., gt=0)

class BuyoutCalculatorResponse(BaseModel):
    monthly_salary:   Decimal
    days_to_buyout:   int
    per_day_salary:   Decimal
    buyout_amount:    Decimal


class WaiverCalculatorRequest(BaseModel):
    current_notice_period_days: int   = Field(..., gt=0)
    waiver_days_requested:      int   = Field(..., gt=0)
    actual_service_days:        int   = Field(..., gt=0)

class WaiverCalculatorResponse(BaseModel):
    original_notice_days: int
    waiver_days_requested: int
    actual_service_days:  int
    effective_notice_days: int
    shortfall_days:        int
    is_eligible_for_waiver: bool


class ShortfallCalculatorRequest(BaseModel):
    required_notice_days: int = Field(..., gt=0)
    actual_service_days:  int = Field(..., ge=0)
    monthly_salary:       Decimal = Field(..., gt=0)

class ShortfallCalculatorResponse(BaseModel):
    required_notice_days: int
    actual_service_days:  int
    shortfall_days:       int
    shortfall_amount:     Decimal

class DashboardStats(BaseModel):
    active_cases:          int
    pending_approvals:     int
    retention_successes:   int
    cases_this_week:       int
    ai_time_saved_hours:   int       
    prediction_accuracy:   float     


class CountdownTrackerItem(BaseModel):
    notice_period_id: int
    employee_id:      int
    employee_name:    str
    employee_code:    Optional[str]
    department:       Optional[str]
    days_left:        int
    notice_start_date: date
    notice_end_date:  date
    status:           NoticeStatus
    pending_actions:  List[str]      

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    stats:            DashboardStats
    countdown_tracker: List[CountdownTrackerItem]