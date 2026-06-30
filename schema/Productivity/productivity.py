from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime





class ProductivityOut(BaseModel):
    id: int
    employee_id: int
    department_id: Optional[int] = None
    team_id: Optional[int] = None
    score: Optional[float] = None
    date: Optional[datetime] = None   
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True





class SummaryMetrics(BaseModel):
    overall_score: float
    average_hours: float = 0.0
    tasks_completed: int = 0