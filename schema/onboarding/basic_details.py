from pydantic import BaseModel
from datetime import date
from typing import Optional


class BasicDetailsCreate(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    gender: str
    date_of_birth: date


class BasicDetailsResponse(BasicDetailsCreate):
    id: int

    class Config:
        from_attributes = True
