

from __future__ import annotations
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from model.Company_Settings.financial_year import FinancialYear
from schema.Company_Settings.financial_year import FinancialYearCreate


MONTH_MAP = {
    "January": 1, "February": 2, "March": 3,
    "April":   4, "May":      5, "June":   6,
    "July":    7, "August":   8, "September": 9,
    "October": 10, "November": 11, "December": 12,
}


def _compute_labels(start_month: int) -> tuple[str, str, str]:
 
    now   = datetime.utcnow()
    year  = now.year
    month = now.month

    if month >= start_month:
        current  = f"{year}-{year + 1}"
        previous = f"{year - 1}-{year}"
        nxt      = f"{year + 1}-{year + 2}"
    else:
        current  = f"{year - 1}-{year}"
        previous = f"{year - 2}-{year - 1}"
        nxt      = f"{year}-{year + 1}"

    return current, previous, nxt


def create_or_update_financial_year(
    db:        Session,
    tenant_id: int,
    data:      FinancialYearCreate,
    actor_id:  Optional[int] = None,
) -> FinancialYear:
    start_num = MONTH_MAP[data.start_month]
    current, previous, nxt = _compute_labels(start_num)


    (
        db.query(FinancialYear)
        .filter(FinancialYear.tenant_id == tenant_id)
        .update({"is_active": False}, synchronize_session="fetch")
    )

    fy = FinancialYear(
        tenant_id        = tenant_id,
        current_year     = current,
        previous_year    = previous,
        next_year        = nxt,
        is_active        = True,
        updated_by       = actor_id,
        **data.model_dump(),
    )
    db.add(fy)
    db.commit()
    db.refresh(fy)
    return fy


def get_active_financial_year(db: Session, tenant_id: int) -> FinancialYear:
    fy = (
        db.query(FinancialYear)
        .filter(
            FinancialYear.tenant_id == tenant_id,
            FinancialYear.is_active.is_(True),
        )
        .first()
    )
    if not fy:
        raise HTTPException(status_code=404, detail="No active financial year configured")
    return fy


def reset_to_default(
    db: Session, tenant_id: int, actor_id: Optional[int] = None
) -> FinancialYear:

    from schema.Company_Settings.financial_year import FinancialYearCreate
    default = FinancialYearCreate(
        start_month        = "April",
        start_day          = 1,
        end_month          = "March",
        end_day            = 31,
        period_type        = "Fiscal Year",
        tax_year_alignment = "Calendar Year",
    )
    return create_or_update_financial_year(db, tenant_id, default, actor_id)
