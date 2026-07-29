from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from schema.Company_Settings.company_profile import (
    CompanyProfileCreate,
    CompanyProfileUpdate,
    CompanyProfileResponse,
)
from services.Company_Settings.company_profile_service import (
    create_company_profile,
    get_company_profile,
    update_company_profile,
    delete_company_profile,
)

router = APIRouter(
    prefix="/company-settings/profile",
    tags=["Company Settings – Profile"],
)



@router.get("/", response_model=CompanyProfileResponse)
def read_company_profile(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    """Fetch the company profile for the authenticated user's tenant."""
    profile = get_company_profile(db, current_user.tenant_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return profile



@router.post("/", response_model=CompanyProfileResponse, status_code=status.HTTP_201_CREATED)
def add_company_profile(
    company_name:           str            = Form(...),
    company_type:           Optional[str]  = Form(None),
    company_website:        Optional[str]  = Form(None),
    email:                  Optional[str]  = Form(None),
    phone:                  Optional[str]  = Form(None),
    address:                Optional[str]  = Form(None),
    about_company:          Optional[str]  = Form(None),
    registration_number:    Optional[str]  = Form(None),
    tax_id:                 Optional[str]  = Form(None),
    vat_gst_number:         Optional[str]  = Form(None),
    industry:               Optional[str]  = Form(None),
    legal_entity_name:      Optional[str]  = Form(None),
    year_founded:           Optional[int]  = Form(None),
    registration_date:      Optional[str]  = Form(None),
    registration_authority: Optional[str]  = Form(None),
    incorporation_number:   Optional[str]  = Form(None),
    logo:                   Optional[UploadFile] = File(None),
    current_user: User    = Depends(require_roles(["admin", "company"])),
    db:           Session = Depends(get_db),
):
    data = CompanyProfileCreate(
        company_name           = company_name,
        company_type           = company_type,
        company_website        = company_website,
        email                  = email,
        phone                  = phone,
        address                = address,
        about_company          = about_company,
        registration_number    = registration_number,
        tax_id                 = tax_id,
        vat_gst_number         = vat_gst_number,
        industry               = industry,
        legal_entity_name      = legal_entity_name,
        year_founded           = year_founded,
        registration_date      = registration_date,
        registration_authority = registration_authority,
        incorporation_number   = incorporation_number,
    )
    return create_company_profile(db, current_user.tenant_id, data, logo, current_user.id)



@router.put("/", response_model=CompanyProfileResponse)
def edit_company_profile(
    company_name:           Optional[str]  = Form(None),
    company_type:           Optional[str]  = Form(None),
    company_website:        Optional[str]  = Form(None),
    email:                  Optional[str]  = Form(None),
    phone:                  Optional[str]  = Form(None),
    address:                Optional[str]  = Form(None),
    about_company:          Optional[str]  = Form(None),
    registration_number:    Optional[str]  = Form(None),
    tax_id:                 Optional[str]  = Form(None),
    vat_gst_number:         Optional[str]  = Form(None),
    industry:               Optional[str]  = Form(None),
    legal_entity_name:      Optional[str]  = Form(None),
    year_founded:           Optional[int]  = Form(None),
    registration_date:      Optional[str]  = Form(None),
    registration_authority: Optional[str]  = Form(None),
    incorporation_number:   Optional[str]  = Form(None),
    logo:                   Optional[UploadFile] = File(None),
    current_user: User    = Depends(require_roles(["admin", "company"])),
    db:           Session = Depends(get_db),
):
    data = CompanyProfileUpdate(
        company_name           = company_name,
        company_type           = company_type,
        company_website        = company_website,
        email                  = email,
        phone                  = phone,
        address                = address,
        about_company          = about_company,
        registration_number    = registration_number,
        tax_id                 = tax_id,
        vat_gst_number         = vat_gst_number,
        industry               = industry,
        legal_entity_name      = legal_entity_name,
        year_founded           = year_founded,
        registration_date      = registration_date,
        registration_authority = registration_authority,
        incorporation_number   = incorporation_number,
    )
    return update_company_profile(db, current_user.tenant_id, data, logo, current_user.id)



@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def remove_company_profile(
    current_user: User    = Depends(require_roles(["admin", "company"])),
    db:           Session = Depends(get_db),
):
    delete_company_profile(db, current_user.tenant_id, current_user.id)