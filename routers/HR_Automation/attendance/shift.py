# routers/HR_Automation/attendance/shift_management.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db

from schema.HR_Automation.shift import (
    ShiftCreate,
    ShiftUpdate
)

from schema.HR_Automation.shift_assignment import (
    ShiftAssignmentCreate
)

from schema.HR_Automation.shift_roster import (
    ShiftRosterCreate
)

from schema.HR_Automation.shift_swap import (
    ShiftSwapCreate
)

from services.HR_Automation.shift import (
    ShiftService
)

from services.HR_Automation.shift_assignment import (
    ShiftAssignmentService
)

from services.HR_Automation.shift_roster import (
    ShiftRosterService
)

from services.HR_Automation.shift_swap import (
    ShiftSwapService
)

router = APIRouter(
    prefix="/attendance/shifts",
    tags=["Shift Management"]
)

# ==========================================
# SHIFT CRUD
# ==========================================

@router.post("/")
def create_shift(
    payload: ShiftCreate,
    db: Session = Depends(get_db)
):
    return ShiftService.create_shift(db, payload)


@router.get("/")
def get_shifts(
    db: Session = Depends(get_db)
):
    return ShiftService.get_shifts(db)


@router.get("/{shift_id}")
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db)
):
    shift = ShiftService.get_shift_by_id(
        db,
        shift_id
    )

    if not shift:
        raise HTTPException(
            status_code=404,
            detail="Shift not found"
        )

    return shift


@router.put("/{shift_id}")
def update_shift(
    shift_id: int,
    payload: ShiftUpdate,
    db: Session = Depends(get_db)
):
    return ShiftService.update_shift(
        db,
        shift_id,
        payload
    )


@router.delete("/{shift_id}")
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db)
):
    return ShiftService.delete_shift(
        db,
        shift_id
    )


# ==========================================
# SHIFT ASSIGNMENTS
# ==========================================

@router.post("/assignments")
def assign_shift(
    payload: ShiftAssignmentCreate,
    db: Session = Depends(get_db)
):
    return ShiftAssignmentService.assign_shift(
        db,
        payload
    )


@router.get("/assignments")
def get_assignments(
    db: Session = Depends(get_db)
):
    return ShiftAssignmentService.get_assignments(
        db
    )


# ==========================================
# SHIFT ROSTERS
# ==========================================

@router.post("/rosters")
def create_roster(
    payload: ShiftRosterCreate,
    db: Session = Depends(get_db)
):
    return ShiftRosterService.create_roster(
        db,
        payload
    )


@router.get("/rosters")
def get_rosters(
    db: Session = Depends(get_db)
):
    return ShiftRosterService.get_rosters(
        db
    )


# ==========================================
# SHIFT SWAP REQUESTS
# ==========================================

@router.post("/swaps")
def create_swap_request(
    payload: ShiftSwapCreate,
    db: Session = Depends(get_db)
):
    return ShiftSwapService.create_request(
        db,
        payload
    )


@router.get("/swaps")
def get_swap_requests(
    db: Session = Depends(get_db)
):
    return ShiftSwapService.get_requests(
        db
    )


@router.put("/swaps/{swap_id}/approve")
def approve_swap(
    swap_id: int,
    db: Session = Depends(get_db)
):
    return ShiftSwapService.approve_request(
        db,
        swap_id
    )


@router.put("/swaps/{swap_id}/reject")
def reject_swap(
    swap_id: int,
    db: Session = Depends(get_db)
):
    return ShiftSwapService.reject_request(
        db,
        swap_id
    )