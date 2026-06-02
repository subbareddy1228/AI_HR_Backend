# app/services/asset_insurance_service.py

from fastapi import HTTPException
from sqlalchemy.orm import Session

from model.HR_Operations.Asset_Management.asset import Asset
from model.HR_Operations.Asset_Management.asset_insurance import AssetInsurance


def create_insurance(db: Session, data):

    asset = db.query(Asset).filter(Asset.id == data.asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset not found")

    if data.end_date <= data.start_date:
        raise HTTPException(400, "End date must be after start date")

    exists = db.query(AssetInsurance).filter(
        AssetInsurance.policy_number == data.policy_number
    ).first()

    if exists:
        raise HTTPException(409, "Policy already exists")

    insurance = AssetInsurance(**data.model_dump())

    db.add(insurance)
    db.commit()
    db.refresh(insurance)

    return insurance
