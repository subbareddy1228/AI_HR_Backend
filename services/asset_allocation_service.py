"""
Asset Allocation Service
Handles: create allocation, approve, list, update, and guard asset status transitions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from model.HR_Operations.Asset_Management.asset import Asset
from model.HR_Operations.Asset_Management.asset_allocation import AssetAllocation
from schema.HR_Operations.Asset_Management.asset_allocation import (
    AssetAllocationCreate,
    AssetAllocationUpdate,
)


def create_allocation(db: Session, payload: AssetAllocationCreate) -> AssetAllocation:
    # 1. Asset must exist and be AVAILABLE
    asset = db.query(Asset).filter(Asset.id == payload.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    if asset.status != "AVAILABLE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset is not available for allocation (current status: {asset.status}).",
        )

    # 2. No duplicate active allocation for same asset
    existing = (
        db.query(AssetAllocation)
        .filter(
            AssetAllocation.asset_id == payload.asset_id,
            AssetAllocation.status == "Active",
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Asset already has an active allocation.",
        )

    allocation = AssetAllocation(**payload.model_dump())
    db.add(allocation)

    # 3. Transition asset → ALLOCATED
    asset.status = "ALLOCATED"
    db.commit()
    db.refresh(allocation)
    return allocation


def get_allocation(db: Session, allocation_id: UUID) -> AssetAllocation:
    alloc = db.query(AssetAllocation).filter(AssetAllocation.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found.")
    return alloc


def list_allocations(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    asset_status: Optional[str] = None,
    allocation_status: Optional[str] = None,
) -> List[AssetAllocation]:
    q = db.query(AssetAllocation)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            AssetAllocation.employee_name.ilike(pattern)
            | AssetAllocation.employee_id.ilike(pattern)
            | AssetAllocation.department.ilike(pattern)
        )
    if allocation_status:
        q = q.filter(AssetAllocation.status == allocation_status)
    return q.order_by(AssetAllocation.allocated_at.desc()).offset(skip).limit(limit).all()


def update_allocation(
    db: Session, allocation_id: UUID, payload: AssetAllocationUpdate
) -> AssetAllocation:
    alloc = get_allocation(db, allocation_id)
    data  = payload.model_dump(exclude_unset=True)

    # Auto-stamp approved_at when approved_by is set for the first time
    if "approved_by" in data and data["approved_by"] and not alloc.approved_at:
        data.setdefault("approved_at", datetime.now(timezone.utc))

    for field, value in data.items():
        setattr(alloc, field, value)
    db.commit()
    db.refresh(alloc)
    return alloc


def approve_allocation(db: Session, allocation_id: UUID, approved_by: str) -> AssetAllocation:
    """Shortcut endpoint: mark an allocation as approved by a named approver."""
    alloc = get_allocation(db, allocation_id)
    if alloc.approved_by:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Allocation has already been approved.",
        )
    alloc.approved_by = approved_by
    alloc.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alloc)
    return alloc


def transfer_allocation(
    db: Session,
    allocation_id: UUID,
    new_employee_id: str,
    new_employee_name: str,
    new_department: str,
    approved_by: Optional[str] = None,
) -> AssetAllocation:
    """Transfer an allocated asset to a different employee without returning it."""
    alloc = get_allocation(db, allocation_id)
    if alloc.status != "Active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only active allocations can be transferred.",
        )
    alloc.employee_id   = new_employee_id
    alloc.employee_name = new_employee_name
    alloc.department    = new_department
    alloc.approved_by   = approved_by
    alloc.approved_at   = datetime.now(timezone.utc) if approved_by else None
    db.commit()
    db.refresh(alloc)
    return alloc
