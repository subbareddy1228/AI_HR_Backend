# schema/Forms_Workflows/request.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, List
from datetime import datetime


# ── Request Template ──────────────────────────────────────────────────────────
class RequestTemplateResponse(BaseModel):
    id:               int
    title:            str
    description:      Optional[str]  = None
    request_type:     str
    category:         str
    sla:              Optional[str]  = None
    priority:         str
    is_quick_action:  bool
    auto_description: bool
    form_schema:      Optional[Any]  = None
    workflow:         Optional[str]  = None
    is_active:        bool

    model_config = ConfigDict(from_attributes=True)


# ── HR Request Create ─────────────────────────────────────────────────────────
class HRRequestCreate(BaseModel):
    title:           str
    description:     Optional[str]  = None
    request_type:    str
    category:        str
    location:        Optional[str]  = None
    workflow:        Optional[str]  = None
    employee_id:     Optional[int]  = None
    employee_name:   Optional[str]  = None
    employee_email:  Optional[str]  = None
    department:      Optional[str]  = None
    submitted_by:    Optional[str]  = None
    assigned_to:     Optional[str]  = None
    priority:        str            = "Medium"
    sla:             Optional[str]  = None
    sla_due_date:    Optional[datetime] = None
    is_quick_action: bool           = False
    auto_fill_data:  Optional[Any]  = None
    form_data:       Optional[Any]  = None
    attachments:     Optional[Any]  = None


class HRRequestUpdate(BaseModel):
    title:          Optional[str]      = None
    description:    Optional[str]      = None
    request_type:   Optional[str]      = None
    category:       Optional[str]      = None
    location:       Optional[str]      = None
    workflow:       Optional[str]      = None
    assigned_to:    Optional[str]      = None
    priority:       Optional[str]      = None
    status:         Optional[str]      = None
    sla:            Optional[str]      = None
    sla_due_date:   Optional[datetime] = None
    response:       Optional[str]      = None
    comments:       Optional[str]      = None
    form_data:      Optional[Any]      = None


class HRRequestResponse(BaseModel):
    id:              int
    request_id:      str
    title:           str
    description:     Optional[str]      = None
    request_type:    str
    category:        str
    location:        Optional[str]      = None
    workflow:        Optional[str]      = None
    employee_id:     Optional[int]      = None
    employee_name:   Optional[str]      = None
    employee_email:  Optional[str]      = None
    department:      Optional[str]      = None
    submitted_by:    Optional[str]      = None
    assigned_to:     Optional[str]      = None
    assigned_to_id:  Optional[int]      = None
    status:          str
    filter_status:   Optional[str]      = None
    priority:        str
    sla:             Optional[str]      = None
    sla_due_date:    Optional[datetime] = None
    sla_breached:    bool
    is_quick_action: bool
    auto_fill_data:  Optional[Any]      = None
    form_data:       Optional[Any]      = None
    attachments:     Optional[Any]      = None
    action_by:       Optional[str]      = None
    action_taken_at: Optional[datetime] = None
    response:        Optional[str]      = None
    comments:        Optional[str]      = None
    submitted_date:  datetime
    created_at:      datetime
    updated_at:      Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Action Schemas ────────────────────────────────────────────────────────────
class RequestActionSchema(BaseModel):
    action_by: str
    comments:  Optional[str] = None
    response:  Optional[str] = None


# ── Dashboard Stats ───────────────────────────────────────────────────────────
class RequestDashboardStats(BaseModel):
    total_requests: int
    in_progress:    int
    approved:       int
    completed:      int
    open:           int
    rejected:       int