from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class EmployeeProductivityBase(BaseModel):
    employee_name:   str
    department:      Optional[str] = None
    role:            Optional[str] = None
    score:           int = 0
    tasks_assigned:  int = 0
    tasks_completed: int = 0
    avg_hours:       float = 0
    streak_days:     int = 0
    trend:           Optional[str] = None
    status:          str = "good"
    period:          Optional[str] = None


class EmployeeProductivityCreate(EmployeeProductivityBase):
    pass


class EmployeeProductivityUpdate(BaseModel):
    score:           Optional[int]   = None
    tasks_assigned:  Optional[int]   = None
    tasks_completed: Optional[int]   = None
    avg_hours:       Optional[float] = None
    streak_days:     Optional[int]   = None
    trend:           Optional[str]   = None
    status:          Optional[str]   = None
    period:          Optional[str]   = None


class EmployeeProductivityResponse(EmployeeProductivityBase):
    id:         int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
