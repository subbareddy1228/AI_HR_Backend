

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from schema.Company_Settings.financial_year import (
    FinancialYearCreate,
    FinancialYearResponse,
)
from services.Company_Settings.financial_year_service import (
    create_or_update_financial_year,
    get_active_financial_year,
    reset_to_default,
)

router = APIRouter(
    prefix="/company-settings/financial-year",
    tags=["Company Settings – Financial Year"],
)


@router.get("/current", response_model=FinancialYearResponse)
def fetch_current_fy(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    return get_active_financial_year(db, current_user.tenant_id)


@router.post("/", response_model=FinancialYearResponse)
def save_financial_year(
    data:         FinancialYearCreate,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    return create_or_update_financial_year(db, current_user.tenant_id, data, current_user.id)


@router.post("/reset-default", response_model=FinancialYearResponse)
def reset_financial_year(
    current_user: User    = Depends(require_roles(["admin"])),
    db:           Session = Depends(get_db),
):

    return reset_to_default(db, current_user.tenant_id, current_user.id)
