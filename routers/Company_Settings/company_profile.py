from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
import os, shutil, time

from core.dependencies import get_db
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

router = APIRouter(prefix="/company-profile", tags=["Company Profile"])

UPLOAD_DIR = "uploads/company_logos"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------- FILE SAVE ----------------
def save_logo(file: UploadFile):
    filename = f"{int(time.time())}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return path


# =========================================================
# CREATE COMPANY PROFILE
# =========================================================
@router.post("/", response_model=CompanyProfileResponse)
def add_company_profile(
    company_name: str = Form(...),
    company_type: str = Form(...),
    company_website: str | None = Form(None),
    email: str = Form(...),
    registration_number: str = Form(...),
    tax_id: str = Form(...),
    vat_gst_number: str | None = Form(None),
    industry: str | None = Form(None),
    year_founded: int | None = Form(None),
    legal_entity_name: str | None = Form(None),
    registration_date: str | None = Form(None),
    registration_authority: str | None = Form(None),
    incorporation_number: str | None = Form(None),
    phone: str | None = Form(None),
    address: str | None = Form(None),
    about_company: str | None = Form(None),
    logo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):

    data = CompanyProfileCreate(
        company_name=company_name,
        company_type=company_type,
        company_website=company_website,
        email=email,
        registration_number=registration_number,
        tax_id=tax_id,
        vat_gst_number=vat_gst_number,
        industry=industry,
        year_founded=year_founded,
        legal_entity_name=legal_entity_name,
        registration_date=registration_date,
        registration_authority=registration_authority,
        incorporation_number=incorporation_number,
        phone=phone,
        address=address,
        about_company=about_company,
    )

    logo_path = save_logo(logo) if logo else None
    return create_company_profile(db, data, logo_path)


# =========================================================
# GET COMPANY PROFILE
# =========================================================
@router.get("/", response_model=CompanyProfileResponse)
def read_company_profile(db: Session = Depends(get_db)):
    profile = get_company_profile(db)
    if not profile:
        raise HTTPException(404, "Company profile not found")
    return profile


# =========================================================
# UPDATE COMPANY PROFILE
# =========================================================
@router.put("/{company_id}", response_model=CompanyProfileResponse)
def edit_company_profile(
    company_id: int,
    company_name: str = Form(...),
    company_type: str = Form(...),
    company_website: str | None = Form(None),
    email: str = Form(...),
    registration_number: str = Form(...),
    tax_id: str = Form(...),
    vat_gst_number: str | None = Form(None),
    industry: str | None = Form(None),
    year_founded: int | None = Form(None),
    legal_entity_name: str | None = Form(None),
    registration_date: str | None = Form(None),
    registration_authority: str | None = Form(None),
    incorporation_number: str | None = Form(None),
    phone: str | None = Form(None),
    address: str | None = Form(None),
    about_company: str | None = Form(None),
    logo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):

    profile = get_company_profile(db)
    if not profile:
        raise HTTPException(404, "Company profile not found")

    data = CompanyProfileUpdate(
        company_name=company_name,
        company_type=company_type,
        company_website=company_website,
        email=email,
        registration_number=registration_number,
        tax_id=tax_id,
        vat_gst_number=vat_gst_number,
        industry=industry,
        year_founded=year_founded,
        legal_entity_name=legal_entity_name,
        registration_date=registration_date,
        registration_authority=registration_authority,
        incorporation_number=incorporation_number,
        phone=phone,
        address=address,
        about_company=about_company,
    )

    logo_path = save_logo(logo) if logo else None

    return update_company_profile(
        db,
        profile,
        data.dict(exclude_unset=True),
        logo_path,
    )


# =========================================================
# DELETE COMPANY PROFILE
# =========================================================
@router.delete("/{company_id}")
def remove_company_profile(company_id: int, db: Session = Depends(get_db)):
    profile = get_company_profile(db)
    if not profile:
        raise HTTPException(404, "Company profile not found")

    delete_company_profile(db, profile)
    return {"message": "Deleted"}
