

from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from schema.Company_Settings.location import (
    CompanyLocationCreate,
    CompanyLocationUpdate,
    CompanyLocationResponse,
    CompanyLocationListResponse,
)
from services.Company_Settings.location_service import (
    get_all_locations,
    get_location,
    create_location,
    update_location,
    delete_location,
    set_default_location,
)

router = APIRouter(
    prefix="/company-settings/locations",
    tags=["Company Settings – Locations"],
)


@router.get("/", response_model=CompanyLocationListResponse)
def list_locations(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    locations = get_all_locations(db, current_user.tenant_id)
    return CompanyLocationListResponse(locations=locations, total=len(locations))


@router.get("/{location_id}", response_model=CompanyLocationResponse)
def read_location(
    location_id:  int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    return get_location(db, current_user.tenant_id, location_id)


@router.post("/", response_model=CompanyLocationResponse, status_code=status.HTTP_201_CREATED)
def add_location(
    data:         CompanyLocationCreate,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    return create_location(db, current_user.tenant_id, data, current_user.id)


@router.put("/{location_id}", response_model=CompanyLocationResponse)
def edit_location(
    location_id:  int,
    data:         CompanyLocationUpdate,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    return update_location(db, current_user.tenant_id, location_id, data, current_user.id)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_location(
    location_id:  int,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    delete_location(db, current_user.tenant_id, location_id, current_user.id)


@router.patch("/{location_id}/set-default", response_model=CompanyLocationResponse)
def mark_default(
    location_id:  int,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    
    return set_default_location(db, current_user.tenant_id, location_id, current_user.id)
