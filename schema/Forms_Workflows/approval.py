from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date


class ApprovalRequestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    reference_type: str                          # leave/expense/transfer/promotion/exit/other
    reference_id: Optional[int] = None
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    requested_by: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_id: Optional[int] = None
    priority: str = "Medium"                     # Low/Medium/High/Critical
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sla_due_date: Optional[datetime] = None


class ApprovalRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_id: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    comments: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sla_due_date: Optional[datetime] = None


class ApprovalRequestResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    reference_type: str
    reference_id: Optional[int] = None
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    requested_by: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_id: Optional[int] = None
    status: str
    priority: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sla_due_date: Optional[datetime] = None
    sla_breached: bool
    action_by: Optional[str] = None
    action_taken_at: Optional[datetime] = None
    comments: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalActionSchema(BaseModel):
    action_by: str
    comments: Optional[str] = None


class ApprovalDashboardStats(BaseModel):
    total_requests: int
    pending: int
    approved: int
    rejected: int
    last_approved_date: Optional[datetime] = None
    rejection_rate: Optional[float] = None