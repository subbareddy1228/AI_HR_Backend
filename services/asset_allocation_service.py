# app/services/asset_allocation_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from model.HR_Operations.Asset_Management.asset import Asset
from model.HR_Operations.Asset_Management.asset_allocation import AssetAllocation


def allocate_asset(db: Session, data):

    try:
        # 🔒 Lock asset row to avoid race condition (two users allocating same asset)
        asset = (
            db.query(Asset)
            .filter(Asset.id == data.asset_id)
            .with_for_update()
            .first()
        )

        # ❌ Asset not found
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # ❌ Asset already allocated
        if asset.status != "AVAILABLE":
            raise HTTPException(status_code=400, detail="Asset not available")

        # ✅ Create allocation record
        allocation = AssetAllocation(
            asset_id=data.asset_id,
            employee_id=data.employee_id,
            employee_name=data.employee_name,
            department=data.department,
            allocation_type=data.allocation_type,
            allocation_reason=data.allocation_reason,
        )

        # ✅ Update lifecycle state
        asset.status = "ALLOCATED"

        db.add(allocation)
        db.add(asset)

        db.commit()
        db.refresh(allocation)

        return allocation

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error while allocating asset"
        )
