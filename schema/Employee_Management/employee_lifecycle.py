from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class LifecycleEventCreate(BaseModel):
    employee_id: int
    event_type: str
    event_date: date
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    remarks: Optional[str] = None


class LifecycleEventUpdate(BaseModel):
    event_type: Optional[str] = None
    event_date: Optional[date] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    remarks: Optional[str] = None


class LifecycleEventResponse(BaseModel):
    id: int
    employee_id: int
    event_type: str
    event_date: Optional[date] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)