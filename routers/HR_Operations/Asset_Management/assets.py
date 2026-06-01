from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

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
def list_assets(db: Session = Depends(get_db)):
    result = db.execute(select(Asset))
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
