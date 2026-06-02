from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# ── ApprovalRequest schemas ────────────────────────────────────────────────────

class ApprovalRequestBase(BaseModel):
    reference_type: str
    reference_id: int
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    request_summary: str
    requested_by: Optional[str] = None
    assigned_to: Optional[str] = None
    status: str = "Pending"


class ApprovalRequestCreate(ApprovalRequestBase):
    pass


class ApprovalRequestUpdate(BaseModel):
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    comments: Optional[str] = None
    action_by: Optional[str] = None


class ApprovalRequestResponse(ApprovalRequestBase):
    id: int
    action_taken_at: Optional[datetime] = None
    action_by: Optional[str] = None
    comments: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Action schema (approve / reject body) ─────────────────────────────────────

class ApprovalActionSchema(BaseModel):
    action_by: str
    comments: Optional[str] = None
