from pydantic import BaseModel
from typing import Optional


class CompanyBase(BaseModel):
    company_name: Optional[str]
    phone_number: Optional[str]
    phone_number2: Optional[str]
    email: Optional[str]
    location: Optional[str]
    rating: Optional[float]
    fax: Optional[str]
    website: Optional[str]
    owner: Optional[str]
    tags: Optional[str]
    deals: Optional[str]
    industry: Optional[str]
    source: Optional[str]
    currency: Optional[str]
    language: Optional[str]
    about: Optional[str]
    contact: Optional[str]
    address: Optional[str]
    country: Optional[str]
    state: Optional[str]
    city: Optional[str]
    zipcode: Optional[str]
    facebook: Optional[str]
    twitter: Optional[str]
    linkedin: Optional[str]
    skype: Optional[str]
    whatsapp: Optional[str]
    instagram: Optional[str]
    visibility: Optional[str]
    status: Optional[str]
    logo: Optional[str]


class CompanyCreate(CompanyBase):
    company_name: str
    phone_number: str


class CompanyUpdate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: int

    class Config:
        orm_mode = True
