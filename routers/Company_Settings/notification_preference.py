from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from schema.Company_Settings.notification_preference import (
    NotificationPreferenceCreate,
    NotificationPreferenceResponse,
)
from services.Company_Settings.notification_service import (
    upsert_notification_preferences,
    get_notification_preferences,
)

router = APIRouter(
    prefix="/company-settings/notifications",
    tags=["Company Settings – Notifications"],
)


@router.get("/", response_model=NotificationPreferenceResponse)
def read_notification_preferences(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
  
    return get_notification_preferences(db, current_user.tenant_id)


@router.post("/", response_model=NotificationPreferenceResponse)
def save_notification_preferences(
    data:         NotificationPreferenceCreate,
    current_user: User    = Depends(require_roles(["admin", "company"])),
    db:           Session = Depends(get_db),
):

    return upsert_notification_preferences(db, current_user.tenant_id, data, current_user.id)