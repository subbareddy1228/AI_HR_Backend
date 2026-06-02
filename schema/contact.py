from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class ContactBase(BaseModel):
    name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[str] = None 
    phone_number: Optional[str] = None
    phone_number2: Optional[str] = None
    fax: Optional[str] = None
    deals: Optional[str] = None
    dob: Optional[date] = None
    ratings: Optional[str] = None
    owner: Optional[str] = None
    industry: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    tags: Optional[List[str]] = []    
    source: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    instagram: Optional[str] = None
    skype: Optional[str] = None
    website: Optional[str] = None
    access_level: Optional[str] = None
    department: Optional[str] = None
    allow_email_access: Optional[bool] = False
    allow_phone_access: Optional[bool] = False
    allow_data_export: Optional[bool] = False
    profile_photo: Optional[str] = None
    
    model_config = {"from_attributes": True}


class ContactCreate(ContactBase):
    name: str
    job_title: str
    phone_number: str
    company_name: str


class ContactUpdate(ContactBase):
    pass


class ContactResponse(ContactBase):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True