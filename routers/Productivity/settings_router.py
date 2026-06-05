# app/routers/settings_router.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from schema.Productivity.setting import SettingCreate, SettingRead
from services.Productivity.setting_service import get_all_settings, create_or_update_setting

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/", response_model=List[SettingRead])
def list_settings(db: Session = Depends(get_db)):
    return get_all_settings(db)

@router.post("/", response_model=SettingRead, status_code=status.HTTP_201_CREATED)
def upsert_setting(payload: SettingCreate, db: Session = Depends(get_db)):
    return create_or_update_setting(db, payload)
