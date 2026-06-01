# app/services/asset_maintenance_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException

from model.HR_Operations.Asset_Management.asset import Asset
from model.HR_Operations.Asset_Management.asset_maintenance import AssetMaintenance


def create_maintenance(db: Session, data):

    asset = db.query(Asset).filter(Asset.id == data.asset_id).first()

    if not asset:
        raise HTTPException(404, "Asset not found")

    if asset.status == "RETIRED":
        raise HTTPException(400, "Cannot maintain retired asset")

    maintenance = AssetMaintenance(**data.model_dump())

    db.add(maintenance)
    db.commit()
    db.refresh(maintenance)

    return maintenance
