from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class TimeLogBase(BaseModel):
    employee: str
    project:  str
    task:     str
    hours:    float
    log_date: str       # ISO date string e.g. "2025-06-04"


class TimeLogCreate(TimeLogBase):
    pass


class TimeLogUpdate(BaseModel):
    project:  Optional[str]   = None
    task:     Optional[str]   = None
    hours:    Optional[float] = None
    log_date: Optional[str]   = None


class TimeLogResponse(TimeLogBase):
    id:         int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
