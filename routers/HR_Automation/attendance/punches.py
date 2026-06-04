from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from core.database import get_db

from schema.HR_Automation.attendance_punch import (
    AttendancePunchCreate
)

from services.HR_Automation.attendance_punch import (
    AttendancePunchService
)

router = APIRouter(
    prefix="/attendance/punches",
    tags=["Attendance Punches"]
)


@router.post("/")
def create_punch(
    payload: AttendancePunchCreate,
    db: Session = Depends(get_db)
):
    return AttendancePunchService.create_punch(
        db,
        payload
    )


@router.get("/")
def get_punches(
    db: Session = Depends(get_db)
):
    return AttendancePunchCRUD.get_all(
        db
    )


@router.get("/{employee_id}")
def get_employee_punches(
    employee_id: int,
    db: Session = Depends(get_db)
):
    return AttendancePunchService.get_employee_punches(
        db,
        employee_id
    )


@router.delete("/{punch_id}")
def delete_punch(
    punch_id: int,
    db: Session = Depends(get_db)
):
    obj = AttendancePunchCRUD.get_by_id(
        db,
        punch_id
    )

    if not obj:
        raise HTTPException(
            status_code=404,
            detail="Punch not found"
        )

    AttendancePunchCRUD.delete(
        db,
        obj
    )

    return {
        "message": "Deleted successfully"
    }