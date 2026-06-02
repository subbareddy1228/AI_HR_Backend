from pydantic import BaseModel
from datetime import date
from typing import Optional

class PolicyBase(BaseModel):
    title: str
    category: str
    version: str
    effective_date: date
    description: Optional[str] = None

class PolicyCreate(PolicyBase):
    pass

class PolicyUpdate(BaseModel):   # ✅ FIXED
    title: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    effective_date: Optional[date] = None
    description: Optional[str] = None
    status: Optional[str] = None

class PolicyResponse(PolicyBase):
    id: int
    status: str
    document_path: Optional[str]

    class Config:
        from_attributes = True
