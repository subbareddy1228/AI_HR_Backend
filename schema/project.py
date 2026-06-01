from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

class ProjectBase(BaseModel):
    client_id: int
    name: str = Field(..., max_length=150)
    start_date: date
    end_date: date
    description: Optional[str] = Field(None, max_length=500)
    active: Optional[bool] = True


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class ProjectOut(ProjectBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
