from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class AlertPriority(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"
    success = "success"

class AlertStatus(str, Enum):
    active = "active"
    dismissed = "dismissed"
    resolved = "resolved"

class AlertCreate(BaseModel):
    employee_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    priority: AlertPriority = AlertPriority.info
    occurred_at: Optional[datetime] = None

class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    title: Optional[str] = None
    description: Optional[str] = None

class AlertRead(BaseModel):
    id: int
    employee_id: Optional[int]
    title: str
    description: Optional[str]
    priority: AlertPriority
    status: AlertStatus
    occurred_at: datetime
    created_at: datetime
    employee_name: Optional[str] = None

    class Config:
        from_attributes = True
