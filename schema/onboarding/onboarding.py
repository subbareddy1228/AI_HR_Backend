from datetime import date
from pydantic import BaseModel, EmailStr

class OnboardingCreate(BaseModel):
    full_name: str
    email: EmailStr
    gender: str
    joining_date: date
    confirmation_date: date

class OnboardingRead(OnboardingCreate):
    id: int
    status: str

    class Config:
        from_attributes = True
