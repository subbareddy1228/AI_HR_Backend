from pydantic import BaseModel
from datetime import datetime
from typing import Optional
  
class AssessmentBase(BaseModel):
    name: str
    type: str
    skill: Optional[str] = None
    difficulty: Optional[str] = None
    role: Optional[str] = None
    question_count: Optional[int] = 0

class AssessmentCreate(AssessmentBase):
    created_by: Optional[int] = None

class AssessmentUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    skill: Optional[str] = None
    difficulty: Optional[str] = None
    role: Optional[str] = None
    question_count: Optional[int] = None
    created_by: Optional[int] = None

class AssessmentOut(AssessmentBase):
    id: int
    last_updated: datetime
    created_by: Optional[int] = None

    class Config:
        
        from_attributes = True
