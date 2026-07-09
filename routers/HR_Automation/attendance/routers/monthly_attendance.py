
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
import io

from core.database import get_db
from schema.HR_Automation.monthly_attendance import (
    MonthlyAttendanceFilter,
    MonthlyCalendarOut,
    MonthlyFilterOptions,
    DayCodeUpdate,
)
from services.HR_Automation.monthly_attendance_service import monthly_attendance_service as svc

router = APIRouter(
    prefix="/monthly",
    tags=["Monthly Attendance"],
)



@router.get("/filter-options", response_model=MonthlyFilterOptions)
def get_filter_options(db: Session = Depends(get_db)):

    return svc.get_filter_options(db)


@router.get("/calendar", response_model=MonthlyCalendarOut)
def get_calendar(
    employee_id: int  = Query(..., description="Employee ID selected in the Employee search"),
    month:       int  = Query(..., ge=1, le=12, description="Month number e.g. 1 for Jan"),
    year:        int  = Query(..., description="Year e.g. 2026"),
    db: Session = Depends(get_db),
):

    return svc.get_calendar(db, employee_id, month, year)


@router.get("/calendars")
def list_calendars(
    month:         int           = Query(..., ge=1, le=12),
    year:          int           = Query(...),
    employee_id:   Optional[int] = Query(None),
    business_unit: Optional[str] = Query(None),
    location:      Optional[str] = Query(None),
    cost_center:   Optional[str] = Query(None),
    department:    Optional[str] = Query(None),
    db: Session = Depends(get_db),
):

    filters = MonthlyAttendanceFilter(
        month=month,
        year=year,
        employee_id=employee_id,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
    )
    return svc.list_calendars(db, filters)


@router.post("/{employee_id}/replace")
def replace_day(
    employee_id: int,
    att_date:    date,
    payload:     DayCodeUpdate,
    db: Session = Depends(get_db),
):

    return svc.replace_day(db, employee_id, att_date, payload)


@router.post("/{employee_id}/recalculate")
def recalculate(
    employee_id: int,
    month:       int = Query(..., ge=1, le=12),
    year:        int = Query(...),
    db: Session = Depends(get_db),
):

    return svc.recalculate(db, employee_id, month, year)


@router.get("/download")
def download_csv(
    month:         int           = Query(..., ge=1, le=12),
    year:          int           = Query(...),
    employee_id:   Optional[int] = Query(None),
    business_unit: Optional[str] = Query(None),
    location:      Optional[str] = Query(None),
    cost_center:   Optional[str] = Query(None),
    department:    Optional[str] = Query(None),
    db: Session = Depends(get_db),
):

    filters = MonthlyAttendanceFilter(
        month=month, year=year,
        employee_id=employee_id,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
    )
    csv_data = svc.download_csv(db, month, year, filters)
    filename = f"monthly_attendance_{month:02d}_{year}.csv"
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
