
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from core.session import get_db
from schema.HR_Operations.Asset_Management.asset_return import (
    AssetReturnCreate,
    AssetReturnResponse,
    AssetReturnUpdate,
)
from services.asset_return_service import (
    get_return,
    issue_certificate,
    list_returns,
    process_return,
    resolve_dispute,
    update_return,
)

router = APIRouter(prefix="/asset-returns", tags=["Asset Returns"])


@router.post(
    "/",
    response_model=AssetReturnResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Process an asset return",
)
def new_return(payload: AssetReturnCreate, db: Session = Depends(get_db)):

    return process_return(db, payload)


@router.get(
    "/",
    response_model=List[AssetReturnResponse],
    summary="List all asset returns (Returns tab)",
)
def all_returns(
    skip:       int           = Query(default=0, ge=0),
    limit:      int           = Query(default=50, ge=1, le=200),
    ret_status: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    return list_returns(db, skip, limit, ret_status=ret_status)


@router.get(
    "/{return_id}",
    response_model=AssetReturnResponse,
    summary="Get a return record by ID",
)
def get_one_return(return_id: UUID, db: Session = Depends(get_db)):
    return get_return(db, return_id)


@router.patch(
    "/{return_id}",
    response_model=AssetReturnResponse,
    summary="Update a return record (penalty, status)",
)
def edit_return(return_id: UUID, payload: AssetReturnUpdate, db: Session = Depends(get_db)):
    return update_return(db, return_id, payload)


@router.post(
    "/{return_id}/issue-certificate",
    response_model=AssetReturnResponse,
    summary="Issue clearance certificate to the employee",
)
def issue_cert(
    return_id:  UUID,
    issued_by:  str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    return issue_certificate(db, return_id, issued_by)


@router.post(
    "/{return_id}/resolve-dispute",
    response_model=AssetReturnResponse,
    summary="Resolve a disputed return",
)
def resolve(
    return_id:        UUID,
    resolution_notes: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    return resolve_dispute(db, return_id, resolution_notes)
