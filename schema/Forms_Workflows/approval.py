# schema/Forms_Workflows/approval.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date


class ApprovalRequestCreate(BaseModel):
    title:           str
    description:     Optional[str]      = None
    reference_type:  str                          # leave/expense/transfer/promotion/exit/other
    reference_id:    Optional[int]      = None
    employee_id:     Optional[int]      = None
    employee_name:   Optional[str]      = None    # shown as badge "John Smith"
    employee_email:  Optional[str]      = None
    assigned_to:     Optional[str]      = None
    assigned_to_id:  Optional[int]      = None
    approver_role:   Optional[str]      = None    # "Approver" badge
    priority:        str                = "Medium"
    start_date:      Optional[date]     = None
    end_date:        Optional[date]     = None
    sla_due_date:    Optional[datetime] = None


class ApprovalRequestUpdate(BaseModel):
    title:           Optional[str]      = None
    description:     Optional[str]      = None
    assigned_to:     Optional[str]      = None
    assigned_to_id:  Optional[int]      = None
    approver_role:   Optional[str]      = None
    priority:        Optional[str]      = None
    status:          Optional[str]      = None
    comments:        Optional[str]      = None
    start_date:      Optional[date]     = None
    end_date:        Optional[date]     = None
    sla_due_date:    Optional[datetime] = None


class ApprovalRequestResponse(BaseModel):
    id:              int
    title:           str
    description:     Optional[str]      = None
    reference_type:  str
    reference_id:    Optional[int]      = None
    employee_id:     Optional[int]      = None
    employee_name:   Optional[str]      = None
    employee_email:  Optional[str]      = None
    assigned_to:     Optional[str]      = None
    assigned_to_id:  Optional[int]      = None
    approver_role:   Optional[str]      = None
    status:          str
    priority:        str
    start_date:      Optional[date]     = None
    end_date:        Optional[date]     = None
    sla_due_date:    Optional[datetime] = None
    sla_breached:    bool
    action_by:       Optional[str]      = None
    action_taken_at: Optional[datetime] = None
    comments:        Optional[str]      = None
    created_at:      datetime
    updated_at:      Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalActionSchema(BaseModel):
    action_by: str
    comments:  Optional[str] = None


# Powers the 4 stat cards in both views
# Employee View: Total=3, Pending=1, Approved=1 (Last: Feb 28 2024), Rejected=1 (1 of 3 = 33%)
# Manager View: Total=0, Pending=0, Approved=0, Rejected=0
class ApprovalDashboardStats(BaseModel):
    total_requests:     int
    pending:            int
    approved:           int
    rejected:           int
    last_approved_date: Optional[datetime] = None   # "Last: Feb 28, 2024"
    rejection_rate:     Optional[float]    = None   # "1 of 3 (33%)"