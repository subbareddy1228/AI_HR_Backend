from datetime import date

from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from core.database import get_db


from services.HR_Automation.attendance_daily import (
    AttendanceDailyService
)

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance Daily"]
)


@router.get("/daily")
def get_daily(
    attendance_date: date,
    db: Session = Depends(get_db)
):
    return (
        AttendanceDailyCRUD
        .get_daily(
            db,
            attendance_date
        )
    )


@router.get("/monthly")
def get_monthly(
    year: int,
    month: int,
    db: Session = Depends(get_db)
):
    return (
        AttendanceDailyCRUD
        .get_monthly(
            db,
            year,
            month
        )
    )


@router.post(
    "/process/{employee_id}"
)
def process_attendance(
    employee_id: int,
    attendance_date: date,
    db: Session = Depends(get_db)
):
    return (
        AttendanceDailyService
        .process_attendance(
            db,
            employee_id,
            attendance_date
        )
    )