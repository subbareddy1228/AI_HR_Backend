from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

class JobRead(BaseModel):
    id: int
    title: str
    department: str
    employment_type: str
    location: Optional[str]
    is_remote: bool
    description: str
    responsibilities: Optional[str]
    requirements: Optional[str]
    salary_min: Optional[float]
    salary_max: Optional[float]
    currency: str
    benefits: List[str]
    skills: List[str]
    expiry_date: Optional[date]
    reference_id: Optional[str]
    jd_file: Optional[str]
    status: str
    recruiter_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
