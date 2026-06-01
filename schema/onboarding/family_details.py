from pydantic import BaseModel
from datetime import date
from typing import Optional

class FamilyDetailsCreate(BaseModel):
    marital_status: str
    father_name: Optional[str]
    father_phone: Optional[str]
    father_dob: Optional[date]
    mother_name: Optional[str]
    mother_phone: Optional[str]
    mother_dob: Optional[date]

class FamilyDetailsResponse(FamilyDetailsCreate):
    id: int

    class Config:
        from_attributes = True
