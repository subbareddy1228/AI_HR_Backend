from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime


# ── Workflow schemas ───────────────────────────────────────────────────────────

class WorkflowBase(BaseModel):
    workflow_name: str
    workflow_type: str
    steps: Optional[Any] = None
    is_active: bool = True


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    workflow_name: Optional[str] = None
    workflow_type: Optional[str] = None
    steps: Optional[Any] = None
    is_active: Optional[bool] = None


class WorkflowResponse(WorkflowBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── WorkflowInstance schemas ───────────────────────────────────────────────────

class WorkflowInstanceBase(BaseModel):
    workflow_id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    current_step: int = 1
    status: str = "Pending"
    initiated_by: Optional[str] = None


class WorkflowInstanceCreate(WorkflowInstanceBase):
    pass


class WorkflowInstanceUpdate(BaseModel):
    current_step: Optional[int] = None
    status: Optional[str] = None
    completed_at: Optional[datetime] = None


class WorkflowInstanceResponse(WorkflowInstanceBase):
    id: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
