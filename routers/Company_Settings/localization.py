

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from schema.Company_Settings.localization import (
    LocalizationCreate,
    LocalizationResponse,
)
from services.Company_Settings.localization_service import (
    upsert_localization,
    get_localization,
)

router = APIRouter(
    prefix="/company-settings/localization",
    tags=["Company Settings – Localization"],
)


@router.get("/", response_model=LocalizationResponse)
def read_localization(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    return get_localization(db, current_user.tenant_id)


@router.post("/", response_model=LocalizationResponse)
def save_localization(
    data:         LocalizationCreate,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    
    return upsert_localization(db, current_user.tenant_id, data, current_user.id)
