

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from schema.Company_Settings.data_privacy import (
    DataPrivacyCreate,
    DataPrivacyUpdate,
    DataPrivacyResponse,
)
from services.Company_Settings.data_privacy_service import (
    upsert_data_privacy,
    get_data_privacy,
)

router = APIRouter(
    prefix="/company-settings/data-privacy",
    tags=["Company Settings – Data Privacy"],
)


@router.get("/", response_model=DataPrivacyResponse)
def read_data_privacy(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    
    return get_data_privacy(db, current_user.tenant_id)


@router.post("/", response_model=DataPrivacyResponse)
def save_data_privacy(
    data:         DataPrivacyCreate,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    
    return upsert_data_privacy(db, current_user.tenant_id, data, current_user.id)


@router.patch("/", response_model=DataPrivacyResponse)
def patch_data_privacy(
    data:         DataPrivacyUpdate,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
   
    return upsert_data_privacy(db, current_user.tenant_id, data, current_user.id)
