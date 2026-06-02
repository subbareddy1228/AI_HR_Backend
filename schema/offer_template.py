from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class OfferTemplateBase(BaseModel):
    name: str
    position: Optional[str] = None
    department: Optional[str] = None
    template_content: str
    salary_range_min: Optional[float] = None
    salary_range_max: Optional[float] = None
    benefits: List[str] = []
    validity_days: int = 30

class OfferTemplateCreate(OfferTemplateBase):
    created_by: Optional[int] = None

class OfferTemplateUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    template_content: Optional[str] = None
    salary_range_min: Optional[float] = None
    salary_range_max: Optional[float] = None
    benefits: Optional[List[str]] = None
    validity_days: Optional[int] = None

class OfferTemplateOut(OfferTemplateBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

