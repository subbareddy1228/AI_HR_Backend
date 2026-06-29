
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
    allocation.status = "RETURNED"

    # simple penalty rule: flat charge if items are missing or damage is reported,
    # proportional to the asset's purchase price so high-value assets cost more to damage
    penalty_amount = 0
    if data.missing_items or data.condition_at_return.upper() in ("DAMAGED", "LOST"):
        penalty_amount = round(float(asset.purchase_price) * 0.10, 2)  # 10% of purchase price
    elif data.damage_details:
        penalty_amount = round(float(asset.purchase_price) * 0.05, 2)  # 5% for minor damage

    asset_return = AssetReturn(**data.model_dump(), penalty_amount=penalty_amount)

    db.add(asset_return)
    db.commit()
    db.refresh(asset_return)

    return asset_return