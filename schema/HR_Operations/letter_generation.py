from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional


class LetterGenerationCreate(BaseModel):
    employee_id: int
    letter_type: str        
    letter_date: date
    subject: str
    body: str
    generated_by: Optional[int] = None


class LetterGenerationUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None


class LetterGenerationResponse(BaseModel):
    id: int
    employee_id: int
    letter_type: str
    letter_date: date
    subject: str
    body: str
    generated_by: Optional[int]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
