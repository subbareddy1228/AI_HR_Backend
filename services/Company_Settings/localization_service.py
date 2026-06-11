

from __future__ import annotations
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from model.Company_Settings.localization import LocalizationPreference
from schema.Company_Settings.localization import LocalizationCreate, LocalizationUpdate


def upsert_localization(
    db:        Session,
    tenant_id: int,
    data:      LocalizationCreate,
    actor_id:  Optional[int] = None,
) -> LocalizationPreference:
   
    pref = _get_pref(db, tenant_id)
    if pref:
        for field, value in data.model_dump().items():
            setattr(pref, field, value)
        pref.updated_by = actor_id
    else:
        pref = LocalizationPreference(
            tenant_id  = tenant_id,
            updated_by = actor_id,
            **data.model_dump(),
        )
        db.add(pref)

    db.commit()
    db.refresh(pref)
    return pref


def get_localization(db: Session, tenant_id: int) -> LocalizationPreference:
    pref = _get_pref(db, tenant_id)
    if not pref:
        raise HTTPException(status_code=404, detail="Localization preferences not configured")
    return pref



def _get_pref(db: Session, tenant_id: int) -> Optional[LocalizationPreference]:
    return (
        db.query(LocalizationPreference)
        .filter(
            LocalizationPreference.tenant_id == tenant_id,
            LocalizationPreference.is_active.is_(True),
        )
        .first()
    )
