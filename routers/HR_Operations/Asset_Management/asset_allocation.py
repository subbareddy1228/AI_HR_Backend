# app/api/v1/asset_allocation.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from core.session import get_db
from schema.HR_Operations.Asset_Management.asset_allocation import (
    AssetAllocationCreate,
    AssetAllocationResponse,
)
from services.asset_allocation_service import allocate_asset
from model.HR_Operations.Asset_Management.asset_allocation import AssetAllocation

router = APIRouter(prefix="/asset-allocations", tags=["Asset Allocation"])


# ✅ CREATE Allocation
@router.post("/", response_model=AssetAllocationResponse)
def create_allocation(
    payload: AssetAllocationCreate,
    db: Session = Depends(get_db),
):
    return allocate_asset(db, payload)


# ✅ LIST ALL Allocations
@router.get("/", response_model=List[AssetAllocationResponse])
def list_allocations(db: Session = Depends(get_db)):
    allocations = (
        db.query(AssetAllocation)
        .order_by(AssetAllocation.allocated_at.desc())
        .all()
    )
    return allocations


# ✅ GET Allocation By ID
@router.get("/{allocation_id}", response_model=AssetAllocationResponse)
def get_allocation(allocation_id: UUID, db: Session = Depends(get_db)):
    allocation = (
        db.query(AssetAllocation)
        .filter(AssetAllocation.id == allocation_id)
        .first()
    )

    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")

    return allocation
