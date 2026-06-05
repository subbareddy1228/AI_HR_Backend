from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ACTIVITY SCHEMAS


class ActivityOpen(BaseModel):
    """
    Used when starting an activity (like app_session open)
    """
    activity_type: str                 # app / website / idle
    name: Optional[str] = None         # app name or website
    description: Optional[str] = None
    activity_metadata: Optional[str] = None
    productive: Optional[str] = None


class ActivityClose(BaseModel):
    """
    Used when closing an activity
    """
    activity_id: int


class ActivityUpdate(BaseModel):
    """
    Used for manual updates (rare, controlled)
    """
    description: Optional[str] = None
    productive: Optional[str] = None


class ActivityResponse(BaseModel):
    """
    What API returns
    """
    id: int
    employee_id: int
    department_id: Optional[int]
    team_id: Optional[int]

    activity_type: str
    name: Optional[str]
    description: Optional[str]
    activity_metadata: Optional[str]

    start_at: Optional[datetime]
    end_at: Optional[datetime]
    duration_seconds: Optional[int]
    productive: Optional[str]

    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True  #  Pydantic v2 (orm_mode is DEAD)


# APP SESSION SCHEMAS

class AppOpen(BaseModel):
    """
    Start / open an app session
    """
    app_name: str
    category: str
    priority: str
    path: str
    cpu_usage: float
    memory_usage: float
    threads: int


class AppClose(BaseModel):
    """
    Close app session
    """
    app_name: str


class AppSessionResponse(BaseModel):
    """
    API response for app session
    """
    id: int
    app_name: str
    category: str
    priority: str
    path: str
    cpu_usage: float
    memory_usage: float
    threads: int

    opened_at: datetime
    closed_at: Optional[datetime]
    duration_seconds: Optional[int]

    class Config:
        from_attributes = True  #  FIXED (no orm_mode)
