from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class RegularizationStatusEnum(str, Enum):
    pending = "Pending"
    approved = "Approved"
    rejected = "Rejected"


class ReportFormat(str, Enum):
    pdf = "PDF"
    csv = "CSV"
    excel = "Excel"




class RegularizationRequestBase(BaseModel):
    employee_id: int
    request_type: str
    request_date: date
    original_check_in: Optional[str] = None
    original_check_out: Optional[str] = None
    requested_check_in: Optional[str] = None
    requested_check_out: Optional[str] = None
    reason: str


class RegularizationRequestCreate(RegularizationRequestBase):
    pass


class RegularizationRequestUpdate(BaseModel):
    request_type: Optional[str] = None
    request_date: Optional[date] = None
    original_check_in: Optional[str] = None
    original_check_out: Optional[str] = None
    requested_check_in: Optional[str] = None
    requested_check_out: Optional[str] = None
    reason: Optional[str] = None


class RegularizationReviewAction(BaseModel):
    status: RegularizationStatusEnum  # Approved | Rejected
    review_comments: Optional[str] = None
    reviewed_by: Optional[int] = None


class RegularizationRequestResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    department: Optional[str] = None
    request_type: str
    request_date: date
    original_check_in: Optional[str] = None
    original_check_out: Optional[str] = None
    requested_check_in: Optional[str] = None
    requested_check_out: Optional[str] = None
    reason: str
    status: RegularizationStatusEnum
    submitted_at: datetime
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_comments: Optional[str] = None
    is_bulk: bool = False

    model_config = ConfigDict(from_attributes=True)


class PaginatedRegularizationRequests(BaseModel):
    total: int
    items: List[RegularizationRequestResponse]




class AutoRejectRuleBase(BaseModel):
    request_type: str
    days_threshold: int = 7
    is_enabled: bool = True


class AutoRejectRuleCreate(AutoRejectRuleBase):
    pass


class AutoRejectRuleUpdate(BaseModel):
    days_threshold: Optional[int] = None
    is_enabled: Optional[bool] = None


class AutoRejectRuleResponse(AutoRejectRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




class RegularizationStatistics(BaseModel):
    total_requests: int
    pending: int
    approved: int
    rejected: int




class BulkRegularizationCreate(BaseModel):
    employee_ids: List[int] = Field(..., min_length=1)
    request_type: str
    request_date: date
    requested_check_in: Optional[str] = None
    requested_check_out: Optional[str] = None
    reason: str
    auto_approve: bool = False


class BulkRegularizationResult(BaseModel):
    batch_id: str
    created_count: int
    auto_approved: bool
    request_ids: List[int]