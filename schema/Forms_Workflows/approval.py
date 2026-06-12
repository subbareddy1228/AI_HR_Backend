
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApprovalHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id            : int
    from_status   : Optional[str] = None
    to_status     : str
    changed_by    : Optional[str] = None
    changed_by_id : Optional[int] = None
    note          : Optional[str] = None
    changed_at    : datetime


class ApprovalCommentCreate(BaseModel):
    body        : str = Field(..., min_length=1, max_length=4000)
    is_internal : bool = False
    author_name : Optional[str] = None


class ApprovalCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id          : int
    approval_id : int
    author_id   : Optional[int] = None
    author_name : Optional[str] = None
    body        : str
    is_internal : bool
    created_at  : datetime
    updated_at  : datetime


class SLASummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sla_status       : str
    sla_due_date     : Optional[datetime] = None
    sla_days_allowed : Optional[int] = None
    days_overdue     : Optional[int] = None


class ApprovalsDashboardCreate(BaseModel):


    reference_type : str = Field(..., max_length=100)
    period_start   : Optional[str] = Field(None, description="e.g. Mar 15, 2024")
    period_end     : Optional[str] = Field(None, description="e.g. Mar 19, 2024")
    tags           : Optional[str] = Field(None, description="Comma-separated tag string")

    request_mgmt_id : Optional[int] = None


    employee_id    : Optional[int]  = None
    employee_name  : Optional[str]  = Field(None, max_length=255)
    employee_email : Optional[str]  = Field(None, max_length=255)
    employee_code  : Optional[str]  = Field(None, max_length=50)
    department     : Optional[str]  = Field(None, max_length=100)
    designation    : Optional[str]  = Field(None, max_length=100)
    location       : Optional[str]  = Field(None, max_length=100)

    subject        : str = Field(..., max_length=500)
    description    : Optional[str] = None

    assigned_to    : Optional[str] = Field(None, max_length=255)
    assigned_to_id : Optional[int] = None

    priority       : str = Field(default="Medium")

 
    sla_days_allowed : Optional[int] = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        allowed = {"Low", "Medium", "High", "Urgent"}
        if v not in allowed:
            raise ValueError(f"priority must be one of {allowed}")
        return v


class ApprovalsDashboardUpdate(BaseModel):
    subject        : Optional[str]  = Field(None, max_length=500)
    description    : Optional[str]  = None
    priority       : Optional[str]  = None
    assigned_to    : Optional[str]  = Field(None, max_length=255)
    assigned_to_id : Optional[int]  = None
    tags           : Optional[str]  = None
    period_start   : Optional[str]  = None
    period_end     : Optional[str]  = None
    sla_days_allowed : Optional[int] = None



class ApprovePayload(BaseModel):

    actioned_by    : str = Field(..., max_length=255)
    actioned_by_id : Optional[int] = None
    comments       : Optional[str] = None


class RejectPayload(BaseModel):

    actioned_by    : str = Field(..., max_length=255)
    actioned_by_id : Optional[int] = None
    comments       : str = Field(..., min_length=1, description="Reason for rejection is required")


class EscalatePayload(BaseModel):

    escalated_to    : str = Field(..., max_length=255)
    escalated_to_id : Optional[int] = None
    reason          : str = Field(..., min_length=1)
    actioned_by     : str = Field(..., max_length=255)


class ReassignPayload(BaseModel):

    new_assignee_name : str = Field(..., max_length=255)
    new_assignee_id   : Optional[int] = None
    reason            : Optional[str] = None
    actioned_by       : str = Field(..., max_length=255)


class WithdrawPayload(BaseModel):

    reason      : Optional[str] = None
    withdrawn_by: str = Field(..., max_length=255)


class OnHoldPayload(BaseModel):

    reason      : str = Field(..., min_length=1)
    actioned_by : str = Field(..., max_length=255)



class ApprovalsDashboardListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id             : int
    approval_code  : str
    reference_type : str
    period_start   : Optional[str] = None
    period_end     : Optional[str] = None
    tags           : Optional[str] = None

    employee_id    : Optional[int]  = None
    employee_name  : Optional[str]  = None
    employee_email : Optional[str]  = None
    department     : Optional[str]  = None
    designation    : Optional[str]  = None

    subject        : str
    status         : str
    priority       : str

    assigned_to    : Optional[str]  = None
    actioned_by    : Optional[str]  = None
    actioned_at    : Optional[datetime] = None

    sla_status       : str
    sla_due_date     : Optional[datetime] = None
    sla_days_allowed : Optional[int] = None

    submitted_at   : datetime
    created_at     : datetime
    updated_at     : datetime


class ApprovalsDashboardDetail(ApprovalsDashboardListItem):


    description    : Optional[str]  = None
    request_mgmt_id: Optional[int]  = None
    employee_code  : Optional[str]  = None
    location       : Optional[str]  = None

    assigned_to_id  : Optional[int]  = None
    actioned_by_id  : Optional[int]  = None
    action_comments : Optional[str]  = None

    is_escalated        : bool = False
    escalated_to        : Optional[str]  = None
    escalated_to_id     : Optional[int]  = None
    escalated_at        : Optional[datetime] = None
    escalation_reason   : Optional[str]  = None
    auto_escalated      : bool = False

    workflow_instance_id: Optional[int] = None

    history  : List[ApprovalHistoryOut]      = []
    comments : List[ApprovalCommentOut]      = []


class ApprovalsDashboardPage(BaseModel):
    total   : int
    page    : int
    size    : int
    items   : List[ApprovalsDashboardListItem]


class ApprovalStatusCount(BaseModel):
    status : str
    count  : int


class ApprovalsDashboardStats(BaseModel):

    total_requests    : int = 0
    total_pending     : int = 0
    total_approved    : int = 0
    total_rejected    : int = 0
    total_escalated   : int = 0
    total_on_hold     : int = 0
    total_withdrawn   : int = 0


    last_approved_at  : Optional[datetime] = None

    rejection_rate_pct: Optional[float]    = None


    sla_on_track      : int = 0
    sla_at_risk       : int = 0
    sla_breached      : int = 0

    by_status         : List[ApprovalStatusCount] = []
    by_reference_type : List[ApprovalStatusCount] = []

class ApprovalDelegationCreate(BaseModel):
    delegator_id   : int
    delegator_name : Optional[str] = None
    delegate_id    : int
    delegate_name  : Optional[str] = None
    valid_from     : datetime
    valid_until    : datetime
    reason         : Optional[str] = None

    @field_validator("valid_until")
    @classmethod
    def until_after_from(cls, v: datetime, info) -> datetime:
        from_val = info.data.get("valid_from")
        if from_val and v <= from_val:
            raise ValueError("valid_until must be after valid_from")
        return v


class ApprovalDelegationUpdate(BaseModel):
    valid_until : Optional[datetime] = None
    is_active   : Optional[bool]     = None
    reason      : Optional[str]      = None


class ApprovalDelegationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id             : int
    delegator_id   : int
    delegator_name : Optional[str] = None
    delegate_id    : int
    delegate_name  : Optional[str] = None
    valid_from     : datetime
    valid_until    : datetime
    is_active      : bool
    reason         : Optional[str] = None
    created_at     : datetime
    updated_at     : datetime


class ApprovalsDashboardFilters(BaseModel):

    status         : Optional[str]      = None   
    reference_type : Optional[str]      = None  
    priority       : Optional[str]      = None   
    employee_id    : Optional[int]      = None
    employee_name  : Optional[str]      = None
    assigned_to_id : Optional[int]      = None
    sla_status     : Optional[str]      = None  
    date_from      : Optional[datetime] = None
    date_to        : Optional[datetime] = None
    search         : Optional[str]      = None   
  
    view_mode      : str = Field(default="Employee")  
  
    page           : int = Field(default=1,  ge=1)
    size           : int = Field(default=20, ge=1, le=200)

    @field_validator("view_mode")
    @classmethod
    def validate_view_mode(cls, v: str) -> str:
        allowed = {"Employee", "Manager"}
        if v not in allowed:
            raise ValueError(f"view_mode must be one of {allowed}")
        return v

class SwitchContextRequest(BaseModel):

    target_employee_id : int
    target_name        : str
