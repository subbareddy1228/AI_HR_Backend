from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime



class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: int
    team_id: Optional[int] = None
    assigned_to: Optional[int] = None
    due_date: Optional[date] = None






class TaskCreate(TaskBase):
    pass






class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    assigned_to: Optional[int] = None






class Task(BaseModel):
    id: int
    title: str
    description: Optional[str]
    project_id: int
    team_id: Optional[int]
    assigned_to: Optional[int]

    status: str
    due_date: Optional[date]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True  
