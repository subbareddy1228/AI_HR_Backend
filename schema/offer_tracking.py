from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List
from model.models import OfferStatus

class OfferTrackingBase(BaseModel):
    candidate_id: int
    job_id: Optional[int] = None
    template_id: Optional[int] = None
    candidate_name: str
    candidate_email: str
    position: str
    department: Optional[str] = None
    salary_offered: Optional[float] = None
    benefits: List[str] = []
    offer_content: str
    expiry_date: Optional[date] = None
    notes: Optional[str] = None

class OfferTrackingCreate(OfferTrackingBase):
    created_by: Optional[int] = None

class OfferTrackingUpdate(BaseModel):
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    salary_offered: Optional[float] = None
    benefits: Optional[List[str]] = None
    offer_content: Optional[str] = None
    status: Optional[OfferStatus] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None

class OfferTrackingOut(OfferTrackingBase):
    id: int
    status: OfferStatus
    sent_date: Optional[datetime] = None
    response_date: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OfferStatusUpdate(BaseModel):
    status: OfferStatus

