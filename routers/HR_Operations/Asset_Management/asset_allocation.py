# app/api/v1/asset_allocation.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
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
def list_allocations(
    status_filter: Optional[str] = Query(None, alias="status", description="ACTIVE | RETURNED"),
    department: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AssetAllocation)

    if status_filter:
        query = query.filter(AssetAllocation.status == status_filter.upper())
    if department:
        query = query.filter(AssetAllocation.department.ilike(f"%{department}%"))
    if employee_id:
        query = query.filter(AssetAllocation.employee_id == employee_id)

    return query.order_by(AssetAllocation.allocated_at.desc()).all()


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