from pydantic import BaseModel
from datetime import datetime
from typing import Optional





class ActivityOpen(BaseModel):

    activity_type: str             
    name: Optional[str] = None         
    description: Optional[str] = None
    activity_metadata: Optional[str] = None
    productive: Optional[str] = None


class ActivityClose(BaseModel):

    activity_id: int


class ActivityUpdate(BaseModel):
   
    description: Optional[str] = None
    productive: Optional[str] = None


class ActivityResponse(BaseModel):

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
        from_attributes = True  




class AppOpen(BaseModel):
  
    app_name: str
    category: str
    priority: str
    path: str
    cpu_usage: float
    memory_usage: float
    threads: int


class AppClose(BaseModel):

    app_name: str


class AppSessionResponse(BaseModel):
 
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
        from_attributes = True  
