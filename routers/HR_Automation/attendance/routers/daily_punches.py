from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import io, csv

from core.database import get_db
from schema.HR_Automation.daily_punches import (
    DailyPunchCreate, DailyPunchUpdate, DailyPunchOut,
    DailyPunchesFilter,
    ManualPunchCreate,
    RegularisePunch,
    PaginatedDailyPunchesResponse,
)
from services.HR_Automation.daily_punches_service import daily_punches_service as svc

router = APIRouter(
    prefix="/daily-punches",
    tags=["Daily Punches"],
)




@router.get("/list", response_model=PaginatedDailyPunchesResponse)
def list_daily_punches(
    
    punch_date:     date             = Query(default_factory=date.today,
                                             description="Date shown in the date picker (e.g. 2026-06-15)"),
   
    employee_id:    Optional[int]    = Query(None, description="Filter by specific employee"),

    
    business_unit:  Optional[str]    = Query(None),
    location:       Optional[str]    = Query(None),
    cost_center:    Optional[str]    = Query(None),
    department:     Optional[str]    = Query(None),

   
    late_only:      bool             = Query(False, description="Late Coming Only button"),
    absent_only:    bool             = Query(False, description="Absent Only button"),
    no_punches:     bool             = Query(False, description="No Punches button"),

    
    page:           int              = Query(1, ge=1),
    page_size:      int              = Query(20, ge=1, le=200),

    db: Session = Depends(get_db),
):
    filters = DailyPunchesFilter(
        punch_date=punch_date,
        employee_id=employee_id,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
        late_only=late_only,
        absent_only=absent_only,
        no_punches=no_punches,
        page=page,
        page_size=page_size,
    )
    return svc.get_daily_punches(db, filters)




@router.get("/filter-options")
def filter_options(db: Session = Depends(get_db)):
   
    return svc.get_filter_options(db)



@router.get("/employee/{employee_id}", response_model=List[DailyPunchOut])
def get_employee_punches(
    employee_id: int,
    punch_date:  date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
):
    return svc.get_employee_punches(db, employee_id, punch_date)




@router.post("/punches", response_model=DailyPunchOut, status_code=201)
def record_punch(payload: DailyPunchCreate, db: Session = Depends(get_db)):
    
    return svc.record_punch(db, payload)




@router.post("/manual-punch", response_model=DailyPunchOut, status_code=201)
def add_manual_punch(payload: ManualPunchCreate, db: Session = Depends(get_db)):
   
    return svc.add_manual_punch(db, payload)




@router.patch("/punches/{punch_id}", response_model=DailyPunchOut)
def update_punch(punch_id: int, payload: DailyPunchUpdate, db: Session = Depends(get_db)):
    
    try:
        return svc.update_punch(db, punch_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/punches/{punch_id}")
def delete_punch(punch_id: int, db: Session = Depends(get_db)):
    
    if not svc.delete_punch(db, punch_id):
        raise HTTPException(status_code=404, detail="Punch not found")
    return {"message": "Punch deleted and summary recomputed"}




@router.post("/regularise", response_model=DailyPunchOut)
def regularise_punch(payload: RegularisePunch, db: Session = Depends(get_db)):
   
    try:
        return svc.regularise_punch(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



@router.post("/mark-processed")
def mark_processed(summary_ids: List[int], db: Session = Depends(get_db)):
   
    count = svc.mark_processed(db, summary_ids)
    return {"message": f"{count} record(s) marked as processed"}




@router.get("/export")
def export_daily_punches(
    punch_date:     date             = Query(default_factory=date.today),
    employee_id:    Optional[int]    = Query(None),
    business_unit:  Optional[str]    = Query(None),
    location:       Optional[str]    = Query(None),
    cost_center:    Optional[str]    = Query(None),
    department:     Optional[str]    = Query(None),
    late_only:      bool             = Query(False),
    absent_only:    bool             = Query(False),
    no_punches:     bool             = Query(False),
    db: Session = Depends(get_db),
):
    filters = DailyPunchesFilter(
        punch_date=punch_date,
        employee_id=employee_id,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
        late_only=late_only,
        absent_only=absent_only,
        no_punches=no_punches,
        page=1,
        page_size=10_000,   # large cap for export
    )
    result = svc.get_daily_punches(db, filters)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "SN", "Employee", "Code", "Designation",
        "Date", "Start", "End", "Duration",
        "Attendance", "Late", "Department", "Business Unit",
        "Location", "Cost Center", "Status",
    ])
    for row in result.items:
        writer.writerow([
            row.sn,
            row.employee_name,
            row.employee_code or "",
            row.designation or "",
            row.summary_date.isoformat(),
            row.start.time or "--",
            row.end.time or "--",
            row.duration,
            row.attendance_mark.value,
            "Yes" if row.is_late else "No",
            row.department or "",
            row.business_unit or "",
            row.location_name or "",
            row.cost_center or "",
            row.process_status.value,
        ])

    output.seek(0)
    filename = f"daily_punches_{punch_date}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
