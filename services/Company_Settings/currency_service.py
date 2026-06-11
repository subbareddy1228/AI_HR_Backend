

from __future__ import annotations
from typing import List, Optional
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from model.Company_Settings.currency import CurrencySetting, ExchangeRate
from schema.Company_Settings.currency import (
    CurrencySettingCreate,
    ExchangeRateCreate,
    ExchangeRateUpdate,
)

logger = logging.getLogger(__name__)

def upsert_currency_settings(
    db:        Session,
    tenant_id: int,
    data:      CurrencySettingCreate,
    actor_id:  Optional[int] = None,
) -> CurrencySetting:
   
    setting = (
        db.query(CurrencySetting)
        .filter(CurrencySetting.tenant_id == tenant_id)
        .first()
    )
    if setting:
        for field, value in data.model_dump().items():
            setattr(setting, field, value)
        setting.updated_by = actor_id
    else:
        setting = CurrencySetting(
            tenant_id  = tenant_id,
            updated_by = actor_id,
            **data.model_dump(),
        )
        db.add(setting)

    db.commit()
    db.refresh(setting)
    return setting


def get_currency_settings(db: Session, tenant_id: int) -> Optional[CurrencySetting]:
    return (
        db.query(CurrencySetting)
        .filter(CurrencySetting.tenant_id == tenant_id)
        .first()
    )



def get_exchange_rates(db: Session, tenant_id: int) -> List[ExchangeRate]:
    return (
        db.query(ExchangeRate)
        .filter(ExchangeRate.tenant_id == tenant_id)
        .order_by(ExchangeRate.from_currency)
        .all()
    )


def add_exchange_rate(
    db:        Session,
    tenant_id: int,
    data:      ExchangeRateCreate,
    actor_id:  Optional[int] = None,
) -> ExchangeRate:
  
    existing = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.tenant_id    == tenant_id,
            ExchangeRate.from_currency == data.from_currency,
            ExchangeRate.to_currency   == data.to_currency,
            ExchangeRate.status        == "active",
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Active exchange rate {data.from_currency}→{data.to_currency} already exists",
        )

    rate = ExchangeRate(
        tenant_id  = tenant_id,
        updated_by = actor_id,
        **data.model_dump(),
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


def update_exchange_rate(
    db:        Session,
    tenant_id: int,
    rate_id:   int,
    data:      ExchangeRateUpdate,
    actor_id:  Optional[int] = None,
) -> ExchangeRate:
    rate = _get_rate_or_404(db, tenant_id, rate_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(rate, field, value)
    rate.updated_by = actor_id
    db.commit()
    db.refresh(rate)
    return rate


def delete_exchange_rate(
    db: Session, tenant_id: int, rate_id: int, actor_id: Optional[int] = None
) -> None:
    rate = _get_rate_or_404(db, tenant_id, rate_id)
    rate.status     = "inactive"
    rate.updated_by = actor_id
    db.commit()



def _get_rate_or_404(db: Session, tenant_id: int, rate_id: int) -> ExchangeRate:
    rate = (
        db.query(ExchangeRate)
        .filter(ExchangeRate.id == rate_id, ExchangeRate.tenant_id == tenant_id)
        .first()
    )
    if not rate:
        raise HTTPException(status_code=404, detail="Exchange rate not found")
    return rate
