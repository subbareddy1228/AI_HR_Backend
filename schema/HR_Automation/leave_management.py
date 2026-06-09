"""
schemas/leave_management.py
Pydantic v2 schemas for all 7 tabs — exact field names from component.
"""

from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from model.HR_Automation.leave_management import (
    AccrualTypeEnum, ApplicationStatusEnum, AdjustmentTypeEnum,
    CompOffSourceEnum, CompOffPolicyEnum, CompOffStatusEnum,
    CampaignStatusEnum, CampaignPeriodEnum,
)


# ══════════════════════════════════════════════════════════
# TAB 1 — LEAVE TYPES
# ══════════════════════════════════════════════════════════

class CarryForwardCfg(BaseModel):
    enabled:       bool = False
    maxDays:       int  = Field(0, ge=0)
    expiryMonths:  int  = Field(0, ge=0)


class EncashmentCfg(BaseModel):
    enabled:  bool  = False
    maxDays:  int   = Field(0, ge=0)
    rate:     float = Field(0.0, ge=0)


class ProrateConfig(BaseModel):
    enabled: bool = True
    method:  str  = "proportional"


class ApproverConfig(BaseModel):
    level:    int
    role:     str
    required: bool = True


class ApprovalWorkflowCfg(BaseModel):
    levels:    int                  = 1
    approvers: List[ApproverConfig] = [ApproverConfig(level=1, role="Manager", required=True)]


class LeaveTypeCreateIn(BaseModel):
    name:                str             = Field(..., max_length=100)
    code:                str             = Field(..., max_length=10)
    description:         str             = ""
    isPaid:              bool            = True
    accrualType:         AccrualTypeEnum = AccrualTypeEnum.monthly
    accrualAmount:       float           = Field(1.0, ge=0.25)
    maxAccrual:          float           = Field(12.0, ge=0)
    carryForward:        CarryForwardCfg     = CarryForwardCfg()
    encashment:          EncashmentCfg       = EncashmentCfg()
    allowHalfDay:        bool            = True
    allowNegative:       bool            = False
    probationApplicable: bool            = False
    sandwichLeave:       bool            = True
    allowBackdated:      bool            = False
    allowShortLeave:     bool            = False
    isOptional:          bool            = False
    usageLimit:          Optional[int]   = None
    proration:           ProrateConfig   = ProrateConfig()
    approvalWorkflow:    ApprovalWorkflowCfg = ApprovalWorkflowCfg()

    @field_validator("code")
    @classmethod
    def upper_code(cls, v): return v.strip().upper()


class LeaveTypeUpdateIn(BaseModel):
    name:                Optional[str]              = None
    description:         Optional[str]              = None
    isPaid:              Optional[bool]             = None
    accrualType:         Optional[AccrualTypeEnum]  = None
    accrualAmount:       Optional[float]            = None
    maxAccrual:          Optional[float]            = None
    carryForward:        Optional[CarryForwardCfg]  = None
    encashment:          Optional[EncashmentCfg]    = None
    allowHalfDay:        Optional[bool]             = None
    allowNegative:       Optional[bool]             = None
    probationApplicable: Optional[bool]             = None
    sandwichLeave:       Optional[bool]             = None
    allowBackdated:      Optional[bool]             = None
    allowShortLeave:     Optional[bool]             = None
    isOptional:          Optional[bool]             = None
    usageLimit:          Optional[int]              = None
    isActive:            Optional[bool]             = None
    proration:           Optional[ProrateConfig]    = None
    approvalWorkflow:    Optional[ApprovalWorkflowCfg] = None


class LeaveTypeOut(BaseModel):
    id:                  int
    name:                str
    code:                str
    description:         str
    isPaid:              bool
    isActive:            bool
    accrualType:         AccrualTypeEnum
    accrualAmount:       float
    maxAccrual:          float
    carryForward:        CarryForwardCfg
    encashment:          EncashmentCfg
    allowHalfDay:        bool
    allowNegative:       bool
    probationApplicable: bool
    sandwichLeave:       bool
    allowBackdated:      bool
    allowShortLeave:     bool
    isOptional:          bool
    usageLimit:          Optional[int]
    proration:           ProrateConfig
    approvalWorkflow:    ApprovalWorkflowCfg
    # Display strings
    accrualDisplay:       str = ""
    carryForwardDisplay:  str = ""
    encashmentDisplay:    str = ""
    halfDayDisplay:       str = ""
    paidDisplay:          str = ""
    statusDisplay:        str = ""
    created_at:           datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# TAB 2 — LEAVE BALANCE
# ══════════════════════════════════════════════════════════

class LeaveBalanceOut(BaseModel):
    id:               int
    employee_id:      str
    employeeName:     str = ""
    leave_type_id:    int
    leaveTypeName:    str = ""
    leaveTypeCode:    str = ""
    year:             int
    openingBalance:   float
    accrued:          float
    carryForward:     float
    used:             float
    encashed:         float
    balance:          float
    projectedBalance: float = 0.0
    lastAccrualDate:  Optional[datetime]

    model_config = {"from_attributes": True}


class AdjustBalanceIn(BaseModel):
    employeeId:       str
    leaveTypeId:      int
    openingBalance:   float = 0.0
    adjustmentType:   AdjustmentTypeEnum
    adjustmentAmount: float = Field(..., ge=0)
    reason:           str
    effectiveDate:    date


# ══════════════════════════════════════════════════════════
# TAB 3 — APPLICATIONS
# ══════════════════════════════════════════════════════════

class LeaveApplicationIn(BaseModel):
    employeeId:    str
    leaveTypeId:   Optional[int]  = None
    startDate:     date
    endDate:       Optional[date] = None
    halfDay:       bool           = False
    halfDayType:   Optional[str]  = None     # first | second
    reason:        str            = ""
    isBulk:        bool           = False
    bulkEmployees: List[str]      = []

    @model_validator(mode="after")
    def validate_dates(self):
        if self.endDate and self.endDate < self.startDate:
            raise ValueError("endDate must be >= startDate")
        if self.halfDay and not self.halfDayType:
            raise ValueError("halfDayType required when halfDay=True")
        return self


class LeaveApplicationOut(BaseModel):
    id:              int
    employee_id:     str
    employeeName:    str = ""
    leave_type_id:   Optional[int]
    leaveTypeName:   str
    isCompOff:       bool
    startDate:       date
    endDate:         Optional[date]
    days:            float
    halfDay:         bool
    halfDayType:     Optional[str]
    reason:          str
    attachmentPath:  Optional[str]
    status:          ApplicationStatusEnum
    isAutoApproved:  bool
    isBulk:          bool
    appliedAt:       datetime
    appliedBy:       str
    currentBalance:  float
    approvedAt:      Optional[datetime]
    rejectionReason: Optional[str]
    withdrawnAt:     Optional[datetime]
    approvalWorkflow:List[dict] = []

    model_config = {"from_attributes": True}


class ApproveRejectIn(BaseModel):
    approved:        bool
    rejectionReason: Optional[str] = None


class OverlapCheckOut(BaseModel):
    employeeId:  str
    hasOverlap:  bool
    overlapping: List[LeaveApplicationOut] = []


# ══════════════════════════════════════════════════════════
# TAB 4 — CALENDAR
# ══════════════════════════════════════════════════════════

class CalendarDayOut(BaseModel):
    day:         int
    date:        date
    leaves:      List[dict]
    hasOverlap:  bool


class CalendarOut(BaseModel):
    year:        int
    month:       int
    monthLabel:  str
    days:        List[CalendarDayOut]
    deptStats:   List[dict]


# ══════════════════════════════════════════════════════════
# TAB 5 — COMP-OFF
# ══════════════════════════════════════════════════════════

class CompOffCreateIn(BaseModel):
    employeeId:  str
    earnedDate:  date
    hours:       float  = Field(..., gt=0)
    expiryDate:  Optional[date] = None
    source:      CompOffSourceEnum  = CompOffSourceEnum.holiday
    policyType:  CompOffPolicyEnum  = CompOffPolicyEnum.compOff
    description: str = ""


class CompOffOut(BaseModel):
    id:          int
    employee_id: str
    employeeName:str = ""
    earnedDate:  date
    hours:       float
    days:        float
    expiryDate:  Optional[date]
    source:      CompOffSourceEnum
    policyType:  CompOffPolicyEnum
    description: str
    status:      CompOffStatusEnum
    applied:     bool
    isExpired:   bool = False
    created_at:  datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# TAB 6 — PLANNING
# ══════════════════════════════════════════════════════════

class CoverageOut(BaseModel):
    department:        str
    totalEmployees:    int
    employeesOnLeave:  int
    coverage:          str   # "100.0" as string — matches frontend


class CampaignCreateIn(BaseModel):
    name:             str  = Field(..., max_length=200)
    period:           CampaignPeriodEnum = CampaignPeriodEnum.quarterly
    startDate:        date
    endDate:          date
    targetDepartment: str  = "All"
    message:          str  = ""
    status:           CampaignStatusEnum = CampaignStatusEnum.active

    @model_validator(mode="after")
    def check_dates(self):
        if self.endDate < self.startDate:
            raise ValueError("endDate must be >= startDate")
        return self


class CampaignOut(BaseModel):
    id:               int
    name:             str
    period:           CampaignPeriodEnum
    startDate:        date
    endDate:          date
    targetDepartment: str
    message:          str
    status:           CampaignStatusEnum
    created_at:       datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# TAB 7 — DELEGATION
# ══════════════════════════════════════════════════════════

class DelegationCreateIn(BaseModel):
    fromApprover: str
    toApprover:   str
    startDate:    date
    endDate:      date
    reason:       str

    @model_validator(mode="after")
    def check_dates(self):
        if self.endDate < self.startDate:
            raise ValueError("endDate must be >= startDate")
        return self


class DelegationOut(BaseModel):
    id:                  int
    fromApprover:        str
    toApprover:          str
    startDate:           date
    endDate:             date
    reason:              str
    isActive:            bool
    isCurrentlyActive:   bool = False
    created_at:          datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# GENERIC
# ══════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    message: str


class AccrualResultOut(BaseModel):
    processed: int
    skipped:   int
    message:   str


class LapseResultOut(BaseModel):
    lapsed:  int
    message: str
