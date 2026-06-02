from pydantic import BaseModel
from datetime import date
from typing import Optional

class CompanyProfileBase(BaseModel):
    company_name: str
    company_type: Optional[str]
    company_website: Optional[str]
    email: Optional[str]

    registration_number: Optional[str]
    tax_id: Optional[str]
    vat_gst_number: Optional[str]

    industry: Optional[str]
    legal_entity_name: Optional[str]

    year_founded: Optional[int]
    registration_date: Optional[date]
    registration_authority: Optional[str]

    incorporation_number: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    about_company: Optional[str]


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileUpdate(CompanyProfileBase):
    pass


class CompanyProfileResponse(CompanyProfileBase):
    id: int
    logo_path: Optional[str]

    class Config:
        from_attributes = True
