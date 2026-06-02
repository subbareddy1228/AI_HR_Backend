# app/api/v1/asset_maintenance.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from core.session import get_db
from schema.HR_Operations.Asset_Management.asset_maintenance import (
    AssetMaintenanceCreate,
    AssetMaintenanceResponse,
)
from services.asset_maintenance_service import create_maintenance
from model.HR_Operations.Asset_Management.asset_maintenance import AssetMaintenance

router = APIRouter(prefix="/asset-maintenances", tags=["Asset Maintenance"])


# ✅ CREATE Maintenance
@router.post("/", response_model=AssetMaintenanceResponse)
def add_maintenance(
    payload: AssetMaintenanceCreate,
    db: Session = Depends(get_db),
):
    return create_maintenance(db, payload)


# ✅ LIST ALL Maintenances
@router.get("/", response_model=List[AssetMaintenanceResponse])
def list_maintenances(db: Session = Depends(get_db)):
    maintenances = (
        db.query(AssetMaintenance)
        .order_by(AssetMaintenance.created_at.desc())
        .all()
    )
    return maintenances


# ✅ GET Maintenance By ID
@router.get("/{maintenance_id}", response_model=AssetMaintenanceResponse)
def get_maintenance(maintenance_id: UUID, db: Session = Depends(get_db)):
    maintenance = (
        db.query(AssetMaintenance)
        .filter(AssetMaintenance.id == maintenance_id)
        .first()
    )

    if not maintenance:
        raise HTTPException(status_code=404, detail="Maintenance not found")

    return maintenance
