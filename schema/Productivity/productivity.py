from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ProductivityOut(BaseModel):
    id: int
    employee_id: int

    department_id: Optional[int] = None
    team_id: Optional[int] = None

    date: date
    period: str

    score: Optional[float] = None
    average_score: float
    tasks_completed: int
    hours_logged: float

    created_at: datetime

    class Config:
        from_attributes = True  





class SummaryMetrics(BaseModel):
    overall_score: float
    average_hours: float
    tasks_completed: int