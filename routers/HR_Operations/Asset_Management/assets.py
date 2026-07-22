
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.session import get_db
from schema.HR_Operations.Asset_Management.asset import (
    AssetCreate,
    AssetDashboardStats,
    AssetReportRow,
    AssetResponse,
    AssetUpdate,
    DepreciationScheduleItem,
)
from services.asset_service import (
    create_asset,
    delete_asset,
    get_asset,
    get_asset_report,
    get_dashboard_stats,
    get_depreciation_schedule,
    list_assets,
    update_asset,
)

router = APIRouter(prefix="/assets", tags=["Asset Management"])


@router.get(
    "/dashboard/stats",
    response_model=AssetDashboardStats,
    summary="Get Asset Management dashboard statistics",
)
def asset_dashboard_stats(db: Session = Depends(get_db)):

    return get_dashboard_stats(db)


@router.post(
    "/",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new asset",
)
def add_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    return create_asset(db, payload)


@router.get(
    "/",
    response_model=List[AssetResponse],
    summary="List / search assets (Asset Master tab)",
)
def list_asset_master(
    skip:       int            = Query(default=0, ge=0),
    limit:      int            = Query(default=50, ge=1, le=200),
    search:     Optional[str]  = Query(default=None, description="Search by name, serial, make, model"),
    category:   Optional[str]  = None,
    status:     Optional[str]  = None,
    department: Optional[str]  = None,
    db: Session = Depends(get_db),
):
    return list_assets(db, skip, limit, search, category, status, department)


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Get a single asset by ID",
)
def get_asset_detail(asset_id: int, db: Session = Depends(get_db)):
    return get_asset(db, asset_id)


@router.patch(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Update asset details",
)
def edit_asset(asset_id: int, payload: AssetUpdate, db: Session = Depends(get_db)):
    return update_asset(db, asset_id, payload)


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an asset (only if not currently allocated)",
)
def remove_asset(asset_id: int, db: Session = Depends(get_db)):
    delete_asset(db, asset_id)


@router.get(
    "/depreciation/schedule",
    response_model=List[DepreciationScheduleItem],
    summary="Get depreciation schedule for all active assets (Depreciation tab)",
)
def depreciation_schedule(
    skip:   int           = Query(default=0, ge=0),
    limit:  int           = Query(default=50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):

    return get_depreciation_schedule(db, skip, limit, search)


@router.get(
    "/reports/full",
    response_model=List[AssetReportRow],
    summary="Full asset report with current value and holder (Reports tab)",
)
def asset_report(
    category:   Optional[str] = None,
    status:     Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return get_asset_report(db, category, status, department)
