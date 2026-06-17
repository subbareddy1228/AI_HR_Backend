from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from schema.HR_Automation.leave import (
    LeaveRequestCreate,
    LeaveRequestUpdate,
    LeaveRequestOut,
    LeaveApplicationsListResponse,
)
from services.HR_Automation import leave as service

router = APIRouter(prefix="/leave", tags=["Leave"])


@router.get("/", response_model=LeaveApplicationsListResponse)
def list_applications(
    search: Optional[str] = Query(default=None, description="Search by employee name, leave type, or reason"),
    status: Optional[str] = Query(default=None, description="Pending | Approved | Rejected | All Status"),
    db: Session = Depends(get_db),
):
    """Powers the Applications tab: search box + status filter dropdown + table."""
    return service.list_applications(db, search=search, status=status)


@router.post("/", response_model=LeaveRequestOut, status_code=201)
def apply_leave(leave: LeaveRequestCreate, db: Session = Depends(get_db)):
    """Powers the '+ New Application' button on the Applications tab."""
    return service.create_leave(db, leave)


@router.get("/{leave_id}", response_model=LeaveRequestOut)
def get_leave(leave_id: int, db: Session = Depends(get_db)):
    return service.get_leave(db, leave_id)


@router.patch("/{leave_id}", response_model=LeaveRequestOut)
def update_leave_status(leave_id: int, payload: LeaveRequestUpdate, db: Session = Depends(get_db)):
    """Powers the Approve / Reject actions in the Applications tab's Actions column."""
    return service.update_leave_status(db, leave_id, payload)


@router.delete("/{leave_id}")
def delete_leave(leave_id: int, db: Session = Depends(get_db)):
    return service.delete_leave(db, leave_id)
