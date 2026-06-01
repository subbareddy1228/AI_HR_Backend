from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional

class ExamStartRequest(BaseModel):
    student_id: int
    email: str = None  # Optional: for looking up by email

class QuestionOption(BaseModel):
    A: str
    B: str
    C: str
    D: str

class QuestionOut(BaseModel):
    id: int
    question: str
    options: QuestionOption

class SubmitExam(BaseModel):
    student_id: int
    answers: Dict[int, str]

class ExamResult(BaseModel):
    email: Optional[EmailStr] = None
    score: int
    status: str
