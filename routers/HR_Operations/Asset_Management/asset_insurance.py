"""
Asset Insurance Router
Covers: Insurance tab — list policies, add, update, file claim,
expiring policies alert, auto-expire sync.
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from core.session import get_db
from schema.HR_Operations.Asset_Management.asset_insurance import (
    AssetInsuranceCreate,
    AssetInsuranceResponse,
    AssetInsuranceUpdate,
)
from services.asset_insurance_service import (
    create_insurance,
    file_claim,
    get_insurance,
    list_expiring_policies,
    list_insurances,
    sync_expired_policies,
    update_insurance,
)

router = APIRouter(prefix="/asset-insurances", tags=["Asset Insurance"])


@router.post(
    "/",
    response_model=AssetInsuranceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new insurance policy",
)
def add_insurance(payload: AssetInsuranceCreate, db: Session = Depends(get_db)):
    return create_insurance(db, payload)


@router.get(
    "/",
    response_model=List[AssetInsuranceResponse],
    summary="List all insurance policies (Insurance tab)",
)
def all_insurances(
    skip:       int           = Query(default=0, ge=0),
    limit:      int           = Query(default=50, ge=1, le=200),
    search:     Optional[str] = None,
    ins_status: Optional[str] = Query(default=None, alias="status"),
    asset_id:   Optional[int] = None,
    db: Session = Depends(get_db),
):
    return list_insurances(db, skip, limit, search, ins_status, asset_id)


@router.get(
    "/expiring",
    response_model=List[AssetInsuranceResponse],
    summary="Get policies expiring within N days (default 30)",
)
def expiring_policies(
    days_ahead: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return list_expiring_policies(db, days_ahead)


@router.post(
    "/sync-expired",
    summary="Sync expired policies — auto-mark past end_date policies as Expired",
    response_model=dict,
)
def sync_expired(db: Session = Depends(get_db)):
    """
    Should be called by a scheduler (cron / Celery beat) daily.
    Returns count of newly expired policies.
    """
    count = sync_expired_policies(db)
    return {"expired_count": count}


@router.get(
    "/{insurance_id}",
    response_model=AssetInsuranceResponse,
    summary="Get an insurance policy by ID",
)
def get_one_insurance(insurance_id: int, db: Session = Depends(get_db)):
    return get_insurance(db, insurance_id)


@router.patch(
    "/{insurance_id}",
    response_model=AssetInsuranceResponse,
    summary="Update an insurance policy",
)
def edit_insurance(
    insurance_id: int,
    payload: AssetInsuranceUpdate,
    db: Session = Depends(get_db),
):
    return update_insurance(db, insurance_id, payload)


@router.post(
    "/{insurance_id}/file-claim",
    response_model=AssetInsuranceResponse,
    summary="File an insurance claim — increments claims count and amount",
)
def claim(
    insurance_id: int,
    claim_amount: Decimal = Body(...),
    claim_notes:  str     = Body(...),
    db: Session = Depends(get_db),
):
    return file_claim(db, insurance_id, claim_amount, claim_notes)
