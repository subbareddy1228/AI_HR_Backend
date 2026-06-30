
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.session import get_db
from schema.HR_Operations.Asset_Management.asset_maintenance import (
    AssetMaintenanceCreate,
    AssetMaintenanceResponse,
    AssetMaintenanceUpdate,
)
from services.asset_maintenance_service import (
    create_maintenance,
    get_maintenance,
    list_maintenances,
    list_overdue_maintenance,
    list_upcoming_maintenance,
    update_maintenance,
)

router = APIRouter(prefix="/asset-maintenances", tags=["Asset Maintenance"])


@router.post(
    "/",
    response_model=AssetMaintenanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a maintenance record",
)
def add_maintenance(payload: AssetMaintenanceCreate, db: Session = Depends(get_db)):

    return create_maintenance(db, payload)


@router.get(
    "/",
    response_model=List[AssetMaintenanceResponse],
    summary="List maintenance history (Maintenance tab)",
)
def all_maintenances(
    skip:             int           = Query(default=0, ge=0),
    limit:            int           = Query(default=50, ge=1, le=200),
    search:           Optional[str] = None,
    maint_status:     Optional[str] = Query(default=None, alias="status"),
    maintenance_type: Optional[str] = None,
    asset_id:         Optional[int] = None,
    db: Session = Depends(get_db),
):
    return list_maintenances(db, skip, limit, search, maint_status, maintenance_type, asset_id)


@router.get(
    "/upcoming",
    response_model=List[AssetMaintenanceResponse],
    summary="Get upcoming maintenance due within N days (default 30)",
)
def upcoming_maintenance(
    days_ahead: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return list_upcoming_maintenance(db, days_ahead)


@router.get(
    "/overdue",
    response_model=List[AssetMaintenanceResponse],
    summary="Get overdue maintenance records",
)
def overdue_maintenance(db: Session = Depends(get_db)):
    return list_overdue_maintenance(db)


@router.get(
    "/{maintenance_id}",
    response_model=AssetMaintenanceResponse,
    summary="Get a maintenance record by ID",
)
def get_one_maintenance(maintenance_id: UUID, db: Session = Depends(get_db)):
    return get_maintenance(db, maintenance_id)


@router.patch(
    "/{maintenance_id}",
    response_model=AssetMaintenanceResponse,
    summary="Update a maintenance record",
)
def edit_maintenance(
    maintenance_id: UUID,
    payload: AssetMaintenanceUpdate,
    db: Session = Depends(get_db),
):

    return update_maintenance(db, maintenance_id, payload)
