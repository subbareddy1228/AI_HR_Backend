# app/services/setting_service.py
from sqlalchemy import select
from sqlalchemy.orm import Session
from model.Productivity.setting import NotificationSetting
from schema.Productivity.setting import SettingCreate


def get_all_settings(db: Session):
    result = db.execute(select(NotificationSetting))
    return result.scalars().all()


def get_setting_by_name(db: Session, name: str):
    result = db.execute(select(NotificationSetting).where(NotificationSetting.name == name))
    return result.scalars().first()


def create_or_update_setting(db: Session, payload: SettingCreate):
    existing = get_setting_by_name(db, payload.name)
    if existing:
        existing.enabled = payload.enabled
        existing.channel = payload.channel
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_setting = NotificationSetting(
            name=payload.name,
            enabled=payload.enabled,
            channel=payload.channel
        )
        db.add(new_setting)
        db.commit()
        db.refresh(new_setting)
        return new_setting
