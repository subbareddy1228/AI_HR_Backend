

from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator, model_validator



class CompanyProfileBase(BaseModel):
    company_name:           str
    company_type:           Optional[str]   = None  
    company_website:        Optional[str]   = None
    email:                  Optional[EmailStr] = None
    phone:                  Optional[str]   = None
    address:                Optional[str]   = None
    about_company:          Optional[str]   = None

    registration_number:    Optional[str]   = None
    tax_id:                 Optional[str]   = None
    vat_gst_number:         Optional[str]   = None
    industry:               Optional[str]   = None
    legal_entity_name:      Optional[str]   = None
    year_founded:           Optional[int]   = None
    registration_date:      Optional[date]  = None
    registration_authority: Optional[str]   = None
    incorporation_number:   Optional[str]   = None


class CompanyProfileCreate(CompanyProfileBase):
    company_name: str

    @field_validator("year_founded")
    @classmethod
    def validate_year(cls, v):
        if v and (v < 1800 or v > datetime.utcnow().year):
            raise ValueError("year_founded must be between 1800 and current year")
        return v


class CompanyProfileUpdate(CompanyProfileBase):
    company_name: Optional[str] = None  


class CompanyProfileResponse(CompanyProfileBase):
    id:                 int
    tenant_id:          int
    logo_path:          Optional[str]   = None
    logo_original_name: Optional[str]   = None
    logo_size_bytes:    Optional[int]   = None
    created_at:         datetime
    updated_at:         datetime

    model_config = {"from_attributes": True}
