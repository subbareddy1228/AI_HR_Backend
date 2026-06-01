from pydantic import BaseModel
from typing import Optional, Dict

class CandidateCreate(BaseModel):
    name: str
    email: str

class OTPVerify(BaseModel):
    email: str
    otp: str

class SubmitExam(BaseModel):
    student_id: int
    answers: Dict[str, str]

class CandidateResponse(BaseModel):
    id: int
    name: str
    email: str
    verified: bool
    score: Optional[int] = 0
    status: Optional[str] = "Pending"
    answers: Optional[Dict[str, str]] = None

    class Config:
        orm_mode = True
