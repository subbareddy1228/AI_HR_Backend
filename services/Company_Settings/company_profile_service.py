

from __future__ import annotations
import os
import shutil
import time
import logging
from typing import Optional

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from model.Company_Settings.company_profile import CompanyProfile
from schema.Company_Settings.company_profile import (
    CompanyProfileCreate,
    CompanyProfileUpdate,
)

logger = logging.getLogger(__name__)

UPLOAD_DIR          = "uploads/company_logos"
ALLOWED_EXTENSIONS  = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

os.makedirs(UPLOAD_DIR, exist_ok=True)



def _validate_and_save_logo(file: UploadFile) -> tuple[str, str, int]:

    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported logo format. Allowed: {ALLOWED_EXTENSIONS}",
        )

    contents = file.file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Logo file exceeds 5 MB limit",
        )

    filename = f"{int(time.time() * 1000)}_{file.filename}"
    path     = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(contents)

    logger.info("Logo saved → %s (%d bytes)", path, len(contents))
    return path, file.filename, len(contents)


def _delete_logo_file(path: Optional[str]) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError as exc:
            logger.warning("Could not delete old logo %s: %s", path, exc)



def create_company_profile(
    db:        Session,
    tenant_id: int,
    data:      CompanyProfileCreate,
    logo:      Optional[UploadFile] = None,
    actor_id:  Optional[int]        = None,
) -> CompanyProfile:
    """Create a new company profile (one per tenant)."""
    existing = _get_profile(db, tenant_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company profile already exists. Use PUT to update.",
        )

    logo_path = logo_name = logo_size = None
    if logo and logo.filename:
        logo_path, logo_name, logo_size = _validate_and_save_logo(logo)

    profile = CompanyProfile(
        tenant_id          = tenant_id,
        logo_path          = logo_path,
        logo_original_name = logo_name,
        logo_size_bytes    = logo_size,
        updated_by         = actor_id,
        **data.model_dump(exclude_none=True),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_company_profile(db: Session, tenant_id: int) -> Optional[CompanyProfile]:
    return _get_profile(db, tenant_id)


def update_company_profile(
    db:        Session,
    tenant_id: int,
    data:      CompanyProfileUpdate,
    logo:      Optional[UploadFile] = None,
    actor_id:  Optional[int]        = None,
) -> CompanyProfile:
    profile = _get_profile_or_404(db, tenant_id)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    if logo and logo.filename:
        _delete_logo_file(profile.logo_path)
        profile.logo_path, profile.logo_original_name, profile.logo_size_bytes = (
            _validate_and_save_logo(logo)
        )

    profile.updated_by = actor_id
    db.commit()
    db.refresh(profile)
    return profile


def delete_company_profile(
    db: Session, tenant_id: int, actor_id: Optional[int] = None
) -> None:
    """Soft-delete the company profile."""
    from datetime import datetime

    profile = _get_profile_or_404(db, tenant_id)
    profile.is_deleted  = True
    profile.deleted_at  = datetime.utcnow()
    profile.updated_by  = actor_id
    db.commit()



def _get_profile(db: Session, tenant_id: int) -> Optional[CompanyProfile]:
    return (
        db.query(CompanyProfile)
        .filter(
            CompanyProfile.tenant_id == tenant_id,
            CompanyProfile.is_deleted.is_(False),
        )
        .first()
    )


def _get_profile_or_404(db: Session, tenant_id: int) -> CompanyProfile:
    profile = _get_profile(db, tenant_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return profile
