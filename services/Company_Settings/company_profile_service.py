from sqlalchemy.orm import Session
from model.Company_Settings.company_profile import CompanyProfile


def create_company_profile(db: Session, data, logo_path=None):
    profile = CompanyProfile(**data.dict(), logo_path=logo_path)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_company_profile(db: Session):
    # ⚠️ IMPORTANT: Your UI shows ONE company profile.
    # So fetch latest record only.
    return db.query(CompanyProfile).order_by(CompanyProfile.id.desc()).first()


def update_company_profile(db: Session, profile, data: dict, logo_path=None):
    for key, value in data.items():
        setattr(profile, key, value)

    if logo_path:
        profile.logo_path = logo_path

    db.commit()
    db.refresh(profile)
    return profile


def delete_company_profile(db: Session, profile):
    db.delete(profile)
    db.commit()
