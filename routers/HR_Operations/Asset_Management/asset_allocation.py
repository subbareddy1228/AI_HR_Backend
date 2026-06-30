
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from core.session import get_db
from schema.HR_Operations.Asset_Management.asset_allocation import (
    AssetAllocationCreate,
    AssetAllocationResponse,
    AssetAllocationUpdate,
)
from services.asset_allocation_service import (
    approve_allocation,
    create_allocation,
    get_allocation,
    list_allocations,
    transfer_allocation,
    update_allocation,
)

router = APIRouter(prefix="/asset-allocations", tags=["Asset Allocations"])


@router.post(
    "/",
    response_model=AssetAllocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new asset allocation",
)
def new_allocation(payload: AssetAllocationCreate, db: Session = Depends(get_db)):

    return create_allocation(db, payload)


@router.get(
    "/",
    response_model=List[AssetAllocationResponse],
    summary="List all allocations (Allocations tab)",
)
def all_allocations(
    skip:              int           = Query(default=0, ge=0),
    limit:             int           = Query(default=50, ge=1, le=200),
    search:            Optional[str] = None,
    allocation_status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return list_allocations(db, skip, limit, search, allocation_status=allocation_status)


@router.get(
    "/{allocation_id}",
    response_model=AssetAllocationResponse,
    summary="Get allocation by ID",
)
def get_one_allocation(allocation_id: UUID, db: Session = Depends(get_db)):
    return get_allocation(db, allocation_id)


@router.patch(
    "/{allocation_id}",
    response_model=AssetAllocationResponse,
    summary="Update allocation (e.g., insurance flag, status)",
)
def edit_allocation(
    allocation_id: UUID,
    payload: AssetAllocationUpdate,
    db: Session = Depends(get_db),
):
    return update_allocation(db, allocation_id, payload)


@router.post(
    "/{allocation_id}/approve",
    response_model=AssetAllocationResponse,
    summary="Approve an allocation — stamps Approved By and Approved At",
)
def approve(
    allocation_id: UUID,
    approved_by:   str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    return approve_allocation(db, allocation_id, approved_by)


@router.post(
    "/{allocation_id}/transfer",
    response_model=AssetAllocationResponse,
    summary="Transfer allocated asset to a different employee",
)
def transfer(
    allocation_id:    UUID,
    new_employee_id:  str           = Body(...),
    new_employee_name: str          = Body(...),
    new_department:   str           = Body(...),
    approved_by:      Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
):
    return transfer_allocation(
        db, allocation_id, new_employee_id, new_employee_name, new_department, approved_by
    )
