"""
Asset Return Service
Handles: process return (closes allocation, frees asset),
certificate issuance, penalty management, and dispute resolution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from model.HR_Operations.Asset_Management.asset import Asset
from model.HR_Operations.Asset_Management.asset_allocation import AssetAllocation
from model.HR_Operations.Asset_Management.asset_return import AssetReturn
from schema.HR_Operations.Asset_Management.asset_return import (
    AssetReturnCreate,
    AssetReturnUpdate,
)


def process_return(db: Session, payload: AssetReturnCreate) -> AssetReturn:
    # 1. Validate allocation exists and is active
    alloc = (
        db.query(AssetAllocation)
        .filter(AssetAllocation.id == payload.allocation_id)
        .first()
    )
    if not alloc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found.")
    if alloc.status != "Active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot return asset — allocation status is '{alloc.status}'.",
        )

    # 2. Prevent duplicate return for same allocation
    existing = (
        db.query(AssetReturn)
        .filter(AssetReturn.allocation_id == payload.allocation_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A return record already exists for this allocation.",
        )

    # 3. Persist return record
    asset_return = AssetReturn(**payload.model_dump())
    db.add(asset_return)

    # 4. Close allocation
    alloc.status = "Returned"

    # 5. Transition asset status
    asset = db.query(Asset).filter(Asset.id == alloc.asset_id).first()
    if asset:
        if payload.condition_at_return in ("Damaged", "Missing Parts", "Beyond Repair"):
            asset.status    = "UNDER_MAINTENANCE"
            asset.condition = payload.condition_at_return if payload.condition_at_return != "Damaged" else "Poor"
        else:
            asset.status = "AVAILABLE"

    db.commit()
    db.refresh(asset_return)
    return asset_return


def get_return(db: Session, return_id: UUID) -> AssetReturn:
    ret = db.query(AssetReturn).filter(AssetReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return record not found.")
    return ret


def list_returns(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    ret_status: Optional[str] = None,
) -> List[AssetReturn]:
    q = db.query(AssetReturn)
    if ret_status:
        q = q.filter(AssetReturn.status == ret_status)
    return q.order_by(AssetReturn.returned_at.desc()).offset(skip).limit(limit).all()


def update_return(
    db: Session, return_id: UUID, payload: AssetReturnUpdate
) -> AssetReturn:
    ret  = get_return(db, return_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(ret, field, value)
    db.commit()
    db.refresh(ret)
    return ret


def issue_certificate(
    db: Session, return_id: UUID, issued_by: str
) -> AssetReturn:
    """Issue clearance certificate for a processed return."""
    ret = get_return(db, return_id)
    if ret.status not in ("Processed",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate can only be issued for a Processed return.",
        )
    if ret.certificate_issued:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate has already been issued.",
        )
    ret.certificate_issued    = True
    ret.certificate_issued_at = datetime.now(timezone.utc)
    ret.certificate_issued_by = issued_by
    db.commit()
    db.refresh(ret)
    return ret


def resolve_dispute(db: Session, return_id: UUID, resolution_notes: str) -> AssetReturn:
    """Resolve a disputed return, marking it as Processed."""
    ret = get_return(db, return_id)
    if ret.status != "Disputed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only Disputed returns can be resolved.",
        )
    ret.status       = "Processed"
    ret.damage_details = (ret.damage_details or "") + f"\n[RESOLVED] {resolution_notes}"
    db.commit()
    db.refresh(ret)
    return ret
