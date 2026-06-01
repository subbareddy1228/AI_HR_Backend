from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List 
import os
import shutil
import uuid

from schema import company
from core.database import get_db
import model
import crud_ops

router = APIRouter()

UPLOAD_FOLDER = "uploads/logos"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


#  CREATE
@router.post("/", response_model=company.CompanyResponse)
def create_company(
    company_name: str = Form(...),
    phone_number: str = Form(...),
    phone_number2: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    rating: Optional[float] = Form(None),
    fax: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    owner: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    deals: Optional[str] = Form(None),
    industry: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    currency: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    about: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    zipcode: Optional[str] = Form(None),
    facebook: Optional[str] = Form(None),
    twitter: Optional[str] = Form(None),
    linkedin: Optional[str] = Form(None),
    skype: Optional[str] = Form(None),
    whatsapp: Optional[str] = Form(None),
    instagram: Optional[str] = Form(None),
    visibility: Optional[str] = Form("private"),
    status: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    logo_filename = None

    if logo:
        file_extension = os.path.splitext(logo.filename)[1] if logo.filename else '.png'
        unique_filename = f"company_{uuid.uuid4().hex[:8]}{file_extension}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(logo.file, f)
        # Store relative path
        logo_filename = file_path.replace("\\", "/")

    new_company = model.Company(
        company_name=company_name,
        phone_number=phone_number,
        phone_number2=phone_number2,
        email=email,
        location=location,
        rating=rating,
        fax=fax,
        website=website,
        owner=owner,
        tags=tags,
        deals=deals,
        industry=industry,
        source=source,
        currency=currency,
        language=language,
        about=about,
        contact=contact,
        address=address,
        country=country,
        state=state,
        city=city,
        zipcode=zipcode,
        facebook=facebook,
        twitter=twitter,
        linkedin=linkedin,
        skype=skype,
        whatsapp=whatsapp,
        instagram=instagram,
        visibility=visibility,
        status=status,
        logo=logo_filename,
    )

    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    return convert_company_output(new_company)


# UTIL: Convert DB Model → Frontend JSON 
def convert_company_output(db_company):
    """Convert DB fields into frontend-friendly structure."""
    if not db_company:
        return None

    company_dict = db_company.__dict__.copy()

    # Normalize logo path
    if db_company.logo:
        # Normalize path separators and ensure it starts with /
        normalized_path = db_company.logo.replace("\\", "/")
        if not normalized_path.startswith("/"):
            company_dict["logo"] = f"/{normalized_path}"
        else:
            company_dict["logo"] = normalized_path
    else:
        company_dict["logo"] = None

    company_dict.pop("_sa_instance_state", None)
    return company_dict


#  READ ALL
@router.get("/", response_model=List[company.CompanyResponse])
def read_companies(db: Session = Depends(get_db)):
    db_companies = db.query(model.Company).all()
    return [convert_company_output(c) for c in db_companies]


#  READ ONE
@router.get("/{company_id}", response_model=company.CompanyResponse)
def read_company(company_id: int, db: Session = Depends(get_db)):
    company_obj = db.query(model.Company).filter(model.Company.id == company_id).first()
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")
    return convert_company_output(company_obj)


#  UPDATE
@router.put("/{company_id}", response_model=company.CompanyResponse)
def update_company(
    company_id: int,
    company_name: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    phone_number2: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    rating: Optional[float] = Form(None),
    fax: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    owner: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    deals: Optional[str] = Form(None),
    industry: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    currency: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    about: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    zipcode: Optional[str] = Form(None),
    facebook: Optional[str] = Form(None),
    twitter: Optional[str] = Form(None),
    linkedin: Optional[str] = Form(None),
    skype: Optional[str] = Form(None),
    whatsapp: Optional[str] = Form(None),
    instagram: Optional[str] = Form(None),
    visibility: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    db_company = db.query(model.Company).filter(model.Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    # LOGO
    if logo:
        file_extension = os.path.splitext(logo.filename)[1] if logo.filename else '.png'
        unique_filename = f"company_{company_id}_{uuid.uuid4().hex[:8]}{file_extension}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(logo.file, f)
        # Store relative path
        db_company.logo = file_path.replace("\\", "/")

    # FIELDS 
    updates = {
        "company_name": company_name,
        "phone_number": phone_number,
        "phone_number2": phone_number2,
        "email": email,
        "location": location,
        "rating": rating,
        "fax": fax,
        "website": website,
        "owner": owner,
        "tags": tags,
        "deals": deals,
        "industry": industry,
        "source": source,
        "currency": currency,
        "language": language,
        "about": about,
        "contact": contact,
        "address": address,
        "country": country,
        "state": state,
        "city": city,
        "zipcode": zipcode,
        "facebook": facebook,
        "twitter": twitter,
        "linkedin": linkedin,
        "skype": skype,
        "whatsapp": whatsapp,
        "instagram": instagram,
        "visibility": visibility,
        "status": status
    }

    for field, value in updates.items():
        if value is not None:
            setattr(db_company, field, value)

    db.commit()
    db.refresh(db_company)
    return convert_company_output(db_company)


#  UPDATE LOGO  
@router.put("/{company_id}/logo")
def update_company_logo(
    company_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    db_company = db.query(model.Company).filter(model.Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    file_extension = os.path.splitext(file.filename)[1] if file.filename else '.png'
    unique_filename = f"company_{company_id}_{uuid.uuid4().hex[:8]}{file_extension}"
    logo_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    with open(logo_path, "wb") as f:
        f.write(file.file.read())

    # Store relative path
    relative_path = logo_path.replace("\\", "/")
    db_company.logo = relative_path
    db.commit()
    db.refresh(db_company)

    # Return normalized path for frontend
    normalized_path = relative_path
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"

    return {"message": "Logo updated successfully", "logo": normalized_path}


#  DELETE  
@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    db_company = db.query(model.Company).filter(model.Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(db_company)
    db.commit()

    return {"message": "Company deleted successfully"}
