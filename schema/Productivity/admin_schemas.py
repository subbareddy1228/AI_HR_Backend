# app/schemas/admin_schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProductiveEntityCreate(BaseModel):
    name: str
    entity_type: str  # "app" or "website"
    productive: Optional[bool] = True

class ProductiveEntityResponse(ProductiveEntityCreate):
    id: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class ReportRequest(BaseModel):
    scope: Optional[str] = "org"  # "org", "team", "department", "employee"
    team_id: Optional[int] = None
    department_id: Optional[int] = None
    employee_id: Optional[int] = None
    period_start: Optional[str] = None  # ISO date strings
    period_end: Optional[str] = None

class ReportLogResponse(BaseModel):
    id: int
    report_type: str
    file_path: str
    generated_by: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class OrgSummary(BaseModel):
    average_productivity_score: float
    total_tasks_completed: int
    average_hours_logged: float
