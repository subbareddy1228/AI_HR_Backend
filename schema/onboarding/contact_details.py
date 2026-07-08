from pydantic import BaseModel
from typing import Optional


class ContactDetailsCreate(BaseModel):
    mobile: str
    email: str
    home_phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    mobile_verified: bool = False


class ContactDetailsResponse(ContactDetailsCreate):
    id: int

    class Config:
        from_attributes = True
