

from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from schema.Company_Settings.currency import (
    CurrencySettingCreate,
    CurrencySettingResponse,
    ExchangeRateCreate,
    ExchangeRateUpdate,
    ExchangeRateResponse,
)
from services.Company_Settings.currency_service import (
    upsert_currency_settings,
    get_currency_settings,
    get_exchange_rates,
    add_exchange_rate,
    update_exchange_rate,
    delete_exchange_rate,
)

router = APIRouter(
    prefix="/company-settings/currency",
    tags=["Company Settings – Currency"],
)



@router.get("/settings", response_model=CurrencySettingResponse)
def read_currency_settings(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    from fastapi import HTTPException
    setting = get_currency_settings(db, current_user.tenant_id)
    if not setting:
        raise HTTPException(status_code=404, detail="Currency settings not configured")
    return setting


@router.post("/settings", response_model=CurrencySettingResponse)
def save_currency_settings(
    data:         CurrencySettingCreate,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    return upsert_currency_settings(db, current_user.tenant_id, data, current_user.id)



@router.get("/rates", response_model=List[ExchangeRateResponse])
def list_exchange_rates(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    return get_exchange_rates(db, current_user.tenant_id)


@router.post("/rates", response_model=ExchangeRateResponse, status_code=status.HTTP_201_CREATED)
def create_exchange_rate(
    data:         ExchangeRateCreate,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    return add_exchange_rate(db, current_user.tenant_id, data, current_user.id)


@router.put("/rates/{rate_id}", response_model=ExchangeRateResponse)
def edit_exchange_rate(
    rate_id:      int,
    data:         ExchangeRateUpdate,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    return update_exchange_rate(db, current_user.tenant_id, rate_id, data, current_user.id)


@router.delete("/rates/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_exchange_rate(
    rate_id:      int,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    delete_exchange_rate(db, current_user.tenant_id, rate_id, current_user.id)
