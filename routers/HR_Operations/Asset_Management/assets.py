from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from typing import Optional

from core.database import get_db
from model.HR_Operations.Asset_Management.asset import Asset
from schema.HR_Operations.Asset_Management.asset import (
    AssetCreate,
    AssetUpdate,
    AssetResponse,
)

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(Asset).where(Asset.serial_number == payload.serial_number)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Serial number already exists"
        )

    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/", response_model=list[AssetResponse])
def list_assets(
    search: Optional[str] = Query(None, description="Search by asset name, serial number, make, or model"),
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status", description="AVAILABLE | ALLOCATED | UNDER_MAINTENANCE | RETIRED"),
    department: Optional[str] = Query(None),
    condition: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(Asset)

    if search:
        like = f"%{search}%"
        query = query.where(
            or_(
                Asset.asset_name.ilike(like),
                Asset.serial_number.ilike(like),
                Asset.make.ilike(like),
                Asset.model.ilike(like),
            )
        )
    if category:
        query = query.where(Asset.category == category)
    if status_filter:
        query = query.where(Asset.status == status_filter.upper())
    if department:
        query = query.where(Asset.department.ilike(f"%{department}%"))
    if condition:
        query = query.where(Asset.condition == condition)

    result = db.execute(query.order_by(Asset.id.desc()))
    return result.scalars().all()


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.execute(
        select(Asset).where(Asset.id == asset_id)
    ).scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return asset


@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
):
    asset = db.execute(
        select(Asset).where(Asset.id == asset_id)
    ).scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, key, value)

    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.execute(
        select(Asset).where(Asset.id == asset_id)
    ).scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    db.delete(asset)
    db.commit()