# app/api/v1/asset_return.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from core.session import get_db
from schema.HR_Operations.Asset_Management.asset_return import (
    AssetReturnCreate,
    AssetReturnResponse,
)
from services.asset_return_service import process_return
from model.HR_Operations.Asset_Management.asset_return import AssetReturn

router = APIRouter(prefix="/asset-returns", tags=["Asset Returns"])


# ✅ CREATE Return
@router.post("/", response_model=AssetReturnResponse)
def create_return(
    payload: AssetReturnCreate,
    db: Session = Depends(get_db),
):
    return process_return(db, payload)


# ✅ LIST ALL Returns
@router.get("/", response_model=List[AssetReturnResponse])
def list_returns(db: Session = Depends(get_db)):
    returns = (
        db.query(AssetReturn)
        .order_by(AssetReturn.returned_at.desc())
        .all()
    )
    return returns


# ✅ GET Return By ID
@router.get("/{return_id}", response_model=AssetReturnResponse)
def get_return(return_id: UUID, db: Session = Depends(get_db)):
    asset_return = (
        db.query(AssetReturn)
        .filter(AssetReturn.id == return_id)
        .first()
    )

    if not asset_return:
        raise HTTPException(status_code=404, detail="Return record not found")

    return asset_return
