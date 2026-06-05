from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class TaskBase(BaseModel):
    title:      str
    assignee:   Optional[str] = None
    department: Optional[str] = None
    priority:   str = "Medium"
    status:     str = "To Do"
    due_date:   Optional[str] = None
    tags:       Optional[str] = None    # comma-separated string


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title:      Optional[str] = None
    assignee:   Optional[str] = None
    department: Optional[str] = None
    priority:   Optional[str] = None
    status:     Optional[str] = None
    due_date:   Optional[str] = None
    tags:       Optional[str] = None


class TaskResponse(TaskBase):
    id:         int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
