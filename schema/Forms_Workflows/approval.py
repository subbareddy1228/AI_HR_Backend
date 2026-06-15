from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalRequestBase(BaseModel):
    reference_type:  str
    reference_id:    Optional[int] = None
    employee_id:     int
    employee_name:   str
    request_summary: Optional[str] = None
    requested_by:    str
    assigned_to:     Optional[str] = None
    status:          Optional[str] = "Pending"


# ─────────────────────────────────────────────────────────────────────────────
# Create  →  POST /approvals/
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalRequestCreate(ApprovalRequestBase):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Update  →  PATCH (future use - reassign / edit)
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalRequestUpdate(BaseModel):
    assigned_to: Optional[str] = None
    status:      Optional[str] = None
    comments:    Optional[str] = None
    action_by:   Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Response  →  GET endpoints
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalRequestResponse(ApprovalRequestBase):
    id:              int
    action_taken_at: Optional[datetime] = None
    action_by:       Optional[str]      = None
    comments:        Optional[str]      = None
    created_at:      datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# Action  →  body for /approve and /reject
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalActionSchema(BaseModel):
    action_by: str
    comments:  Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard summary  →  GET /approvals/summary
# Powers the 4 stat-cards: Total Requests | Pending | Approved | Rejected
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalDashboardSummary(BaseModel):
    total_requests: int
    pending:        int
    approved:       int
    rejected:       int