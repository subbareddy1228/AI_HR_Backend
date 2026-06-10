from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class HRHelpdeskCreate(BaseModel):
    employee_id: int
    category: str          
    subject: str
    description: str
    priority: Optional[str] = "MEDIUM"


class HRHelpdeskUpdate(BaseModel):
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    resolution: Optional[str] = None


class HRHelpdeskResponse(BaseModel):
    id: int
    employee_id: int
    category: str
    subject: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[int]
    resolution: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
