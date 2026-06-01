# app/services/asset_return_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException

from model.HR_Operations.Asset_Management.asset import Asset
from model.HR_Operations.Asset_Management.asset_allocation import AssetAllocation
from model.HR_Operations.Asset_Management.asset_return import AssetReturn


def process_return(db: Session, data):

    allocation = (
        db.query(AssetAllocation)
        .filter(AssetAllocation.id == data.allocation_id)
        .first()
    )

    if not allocation:
        raise HTTPException(404, "Allocation not found")

    asset = allocation.asset

    if asset.status != "ALLOCATED":
        raise HTTPException(400, "Asset already returned or invalid state")

    asset.status = "AVAILABLE"

    asset_return = AssetReturn(**data.model_dump())

    db.add(asset_return)
    db.commit()
    db.refresh(asset_return)

    return asset_return
