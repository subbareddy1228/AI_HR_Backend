from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class HRRequestBase(BaseModel):
    employee_id: Optional[int] = None
    request_type: str
    subject: str
    description: str
    priority: str = "Medium"
    assigned_to: Optional[str] = None


class HRRequestCreate(HRRequestBase):
    pass


class HRRequestUpdate(BaseModel):
    request_type: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    response: Optional[str] = None


class HRRequestResponse(HRRequestBase):
    id: int
    status: str
    response: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
