from pydantic import BaseModel
from typing import Optional, List

# Define structured question model
class Question(BaseModel):
    q: str
    a: Optional[str] = None

class AIInterviewTemplateBase(BaseModel):
    name: str
    interview_type: str
    questions: Optional[List[Question]] = None
    time_limit: Optional[int] = None
    difficulty: Optional[str] = None

class AIInterviewTemplateCreate(AIInterviewTemplateBase):
    questions: Optional[List[Question]] = None  

class AIInterviewTemplateUpdate(BaseModel):
    name: Optional[str] = None
    interview_type: Optional[str] = None
    questions: Optional[List[Question]] = None
    time_limit: Optional[int] = None
    difficulty: Optional[str] = None
    created_by: Optional[int] = None

class AIInterviewTemplateOut(AIInterviewTemplateBase):
    id: int
    created_by: int

    class Config:
        from_attributes = True  
