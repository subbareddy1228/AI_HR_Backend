from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime, time
from enum import Enum as PyEnum

from pydantic import BaseModel
from datetime import date
from enum import Enum as PyEnum

class StatusEnum(str, PyEnum):
    active = "active"
    inactive = "inactive"

class PipelineBase(BaseModel):
    pipeline_Name: str
    total_deal_value: float
    deals: int
    stages: str
    created_date: date
    status: StatusEnum

class PipelineCreate(PipelineBase):
    pass

class PipelineUpdate(BaseModel):
    pipeline_Name: Optional[str] = None
    total_deal_value: Optional[float] = None
    deals: Optional[int] = None
    stages: Optional[str] = None
    created_date: Optional[date] = None
    status: Optional[StatusEnum] = None

class PipelineResponse(PipelineBase):
    id: int

    class Config:
        from_attributes = True 
