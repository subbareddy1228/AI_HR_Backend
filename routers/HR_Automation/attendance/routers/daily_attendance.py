from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
import io

from core.database import get_db
from schema.HR_Automation.daily_attendance import (
    DailyAttendanceCreate,
    DailyAttendanceUpdate,
    DailyAttendanceFilter,
    DailyAttendanceOut,
    PaginatedDailyAttendance,
    FilterOptions,
    BulkUploadPayload,
)
from services.HR_Automation.daily_attendance_service import daily_attendance_service as svc

router = APIRouter(
    prefix="/attendance/daily",
    tags=["Daily Attendance"],
)




@router.get("/filter-options", response_model=FilterOptions)
def get_filter_options(db: Session = Depends(get_db)):
    
    return svc.get_filter_options(db)



@router.get("/", response_model=PaginatedDailyAttendance)
def list_daily_attendance(
    att_date:      date           = Query(default_factory=date.today, description="Date picker — e.g. 2026-06-15"),
    business_unit: Optional[str]  = Query(None, description="Business Unit dropdown"),
    location:      Optional[str]  = Query(None, description="Location dropdown"),
    cost_center:   Optional[str]  = Query(None, description="Cost Center dropdown"),
    department:    Optional[str]  = Query(None, description="Departments dropdown"),
    employee_id:   Optional[int]  = Query(None, description="All Employees search"),
    late_only:     bool           = Query(False, description="Late Coming Only button"),
    absent_only:   bool           = Query(False, description="Absent Only button"),
    no_punches:    bool           = Query(False, description="No Punches button"),
    page:          int            = Query(1,  ge=1),
    page_size:     int            = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    filters = DailyAttendanceFilter(
        att_date=att_date,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
        employee_id=employee_id,
        late_only=late_only,
        absent_only=absent_only,
        no_punches=no_punches,
        page=page,
        page_size=page_size,
    )
    return svc.list_attendance(db, filters)




@router.get("/{record_id}", response_model=DailyAttendanceOut)
def get_record(record_id: int, db: Session = Depends(get_db)):
    return svc.get_record(db, record_id)




@router.post("/", response_model=DailyAttendanceOut, status_code=201)
def create_record(payload: DailyAttendanceCreate, db: Session = Depends(get_db)):
   
    return svc.create_record(db, payload)




@router.put("/{record_id}", response_model=DailyAttendanceOut)
def update_record(
    record_id: int,
    payload: DailyAttendanceUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_record(db, record_id, payload)




@router.delete("/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    return svc.delete_record(db, record_id)




@router.post("/upload")
def upload_attendance(payload: BulkUploadPayload, db: Session = Depends(get_db)):
  
    return svc.bulk_upload(db, payload)




@router.get("/download")
def download_attendance(
    att_date: date = Query(default_factory=date.today),
    db: Session    = Depends(get_db),
):
    csv_data = svc.download_csv(db, att_date)
    filename = f"daily_attendance_{att_date}.csv"
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )