from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from model.HR_Operations.Asset_Management.asset import Asset
from model.HR_Operations.Asset_Management.asset_maintenance import AssetMaintenance
from schema.HR_Operations.Asset_Management.asset_maintenance import (
    AssetMaintenanceCreate,
    AssetMaintenanceUpdate,
)


def create_maintenance(db: Session, payload: AssetMaintenanceCreate) -> AssetMaintenance:
    asset = db.query(Asset).filter(Asset.id == payload.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    if asset.status == "RETIRED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot schedule maintenance for a retired asset.",
        )

    maintenance = AssetMaintenance(**payload.model_dump())
    db.add(maintenance)

    # Transition asset → UNDER_MAINTENANCE for active/scheduled work
    if payload.status in ("Scheduled", "In Progress"):
        if asset.status == "AVAILABLE":
            asset.status = "UNDER_MAINTENANCE"

    db.commit()
    db.refresh(maintenance)
    return maintenance


def get_maintenance(db: Session, maintenance_id: UUID) -> AssetMaintenance:
    m = db.query(AssetMaintenance).filter(AssetMaintenance.id == maintenance_id).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found.")
    return m


def list_maintenances(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    maint_status: Optional[str] = None,
    maintenance_type: Optional[str] = None,
    asset_id: Optional[int] = None,
) -> List[AssetMaintenance]:
    q = db.query(AssetMaintenance)
    if asset_id:
        q = q.filter(AssetMaintenance.asset_id == asset_id)
    if maint_status:
        q = q.filter(AssetMaintenance.status == maint_status)
    if maintenance_type:
        q = q.filter(AssetMaintenance.maintenance_type == maintenance_type)
    if search:
        pattern = f"%{search}%"
        q = q.filter(AssetMaintenance.performed_by.ilike(pattern) | AssetMaintenance.description.ilike(pattern))
    return q.order_by(AssetMaintenance.maintenance_date.desc()).offset(skip).limit(limit).all()


def update_maintenance(
    db: Session, maintenance_id: UUID, payload: AssetMaintenanceUpdate
) -> AssetMaintenance:
    m    = get_maintenance(db, maintenance_id)
    data = payload.model_dump(exclude_unset=True)

    
    if data.get("status") == "Completed":
        asset = db.query(Asset).filter(Asset.id == m.asset_id).first()
        if asset and asset.status == "UNDER_MAINTENANCE":
            asset.status = "AVAILABLE"

    for field, value in data.items():
        setattr(m, field, value)
    db.commit()
    db.refresh(m)
    return m


def list_upcoming_maintenance(
    db: Session,
    days_ahead: int = 30,
) -> List[AssetMaintenance]:
    
    today = date.today()
    return (
        db.query(AssetMaintenance)
        .filter(
            AssetMaintenance.next_due_date >= today,
            AssetMaintenance.next_due_date <= today + timedelta(days=days_ahead),
            AssetMaintenance.status != "Cancelled",
        )
        .order_by(AssetMaintenance.next_due_date)
        .all()
    )


def list_overdue_maintenance(db: Session) -> List[AssetMaintenance]:
    
    today = date.today()
    return (
        db.query(AssetMaintenance)
        .filter(
            AssetMaintenance.next_due_date < today,
            AssetMaintenance.status.in_(["Scheduled", "In Progress"]),
        )
        .order_by(AssetMaintenance.next_due_date)
        .all()
    )
