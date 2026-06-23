"""
routers/daily_attendance.py
FastAPI router — Daily Attendance module.
Prefix : /api/attendance/daily
Auth   : JWT via existing get_current_user / require_hr_admin helpers
"""

import io
import uuid
from datetime import date
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Query, Path)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db

from model.HR_Automation.daily_attendance import PunchDirectionEnum, PunchTypeEnum
from schema.HR_Automation.daily_attendance import (
    DailyAttendanceFilter, DailyAttendanceListOut,
    AttendanceCardOut, AllPunchesOut,
    AddAttendancePunchIn, AddAttendancePunchOut,
    DeletePunchOut, FilterOptionsOut, ImportResultOut,
    MessageResponse)
from services.HR_Automation.daily_attendance_service import (
    FilterOptionsService, DailyAttendanceService,
    PunchManagementService, ImportExportService, _build_card)

router = APIRouter(
    prefix="/api/attendance/daily",
    tags=["Daily Attendance"])


# ─────────────────────────────────────────────────────────
# FILTER OPTIONS  (populate 4 dropdowns on page load)
# GET /api/attendance/daily/filter-options
# ─────────────────────────────────────────────────────────

@router.get("/filter-options", response_model=FilterOptionsOut)
def get_filter_options(
    db:           Session = Depends(get_db)
):
    """
    Returns distinct values for Business Unit · Location · Cost Center · Departments.
    Called once on page load to hydrate all 4 dropdowns.
    """
    return FilterOptionsService.get(db)


# ─────────────────────────────────────────────────────────
# MAIN CARD LIST  (all employee attendance cards)
# GET /api/attendance/daily
# ─────────────────────────────────────────────────────────

@router.get("", response_model=DailyAttendanceListOut)
def list_attendance(
    # ── Date arrow navigation ──
    attendance_date: date           = Query(default_factory=date.today,
                                           description="YYYY-MM-DD — shown as DD-Mon-YYYY in UI"),
    # ── 4 dropdown filters ──
    business_unit:   Optional[str]  = Query(None),
    location:        Optional[str]  = Query(None),
    cost_center:     Optional[str]  = Query(None),
    department:      Optional[str]  = Query(None),
    # ── Radio button filter ──
    status_filter:   Optional[str]  = Query(None,
                                           description="all | late | absent | nopunch"),
    # ── Employee search box ──
    search:          Optional[str]  = Query(None, description="Name / code / designation"),
    db:              Session        = Depends(get_db)
):
    """
    Returns all attendance cards for the selected date, filtered and sorted.

    Each card contains:
    - Header  : name (code) | location icon | designation icon | department icon
    - Left    : date label | status badge | note text
    - Middle  : shift label (General) | 3-bar timeline | punch_in / punch_out below bars
    - Right   : In-Time "8 h 35 m" | + button | … button
    """
    f = DailyAttendanceFilter(
        attendance_date=attendance_date,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
        status_filter=status_filter,
        search=search)
    return DailyAttendanceService.list_cards(db, f)

# ─────────────────────────────────────────────────────────
# EXPORT CSV  (Options → Download)
# GET /api/attendance/daily/export
# ─────────────────────────────────────────────────────────

@router.get("/export")
def export_csv(
    attendance_date: date           = Query(default_factory=date.today),
    business_unit:   Optional[str]  = Query(None),
    location:        Optional[str]  = Query(None),
    cost_center:     Optional[str]  = Query(None),
    department:      Optional[str]  = Query(None),
    status_filter:   Optional[str]  = Query(None),
    search:          Optional[str]  = Query(None),
    db:              Session        = Depends(get_db)
):
    """
    Options → Download button.
    Exports the currently filtered attendance cards as CSV.
    Filename: daily_attendance_YYYY_MM_DD.csv
    Columns: code · name · date · status · location · designation
             department · punch_in · punch_out · punch_type · in_time
    """
    f = DailyAttendanceFilter(
        attendance_date=attendance_date,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
        status_filter=status_filter,
        search=search)
    result    = DailyAttendanceService.list_cards(db, f)
    csv_bytes = ImportExportService.export_csv(result["items"], attendance_date)
    filename  = f"daily_attendance_{attendance_date.strftime('%Y_%m_%d')}.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"})


# ─────────────────────────────────────────────────────────
# SINGLE EMPLOYEE CARD
# GET /api/attendance/daily/{employee_id}
# ─────────────────────────────────────────────────────────

@router.get("/{employee_id}", response_model=AttendanceCardOut)
def get_employee_card(
    employee_id:     str  = Path(...),
    attendance_date: date = Query(...),
    db:              Session = Depends(get_db)
):
    """Returns the attendance card for a single employee on a given date."""
    from model.HR_Automation.daily_attendance import DailyAttendanceRecord
    record = db.query(DailyAttendanceRecord).filter_by(
        employee_id=employee_id, attendance_date=attendance_date
    ).first()
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            f"No attendance record for {employee_id} on {attendance_date}.")
    return _build_card(db, record)


# ─────────────────────────────────────────────────────────
# ALL PUNCHES MODAL  (… button)
# GET /api/attendance/daily/{employee_id}/punches
# ─────────────────────────────────────────────────────────

@router.get("/{employee_id}/punches", response_model=AllPunchesOut)
def get_all_punches(
    employee_id:     str  = Path(...),
    attendance_date: date = Query(...),
    db:              Session = Depends(get_db)
):
    """
    Opens the '…' All Punches modal.
    Returns all punch entries (IN/OUT with badge + trash icon) for employee + date.
    """
    return DailyAttendanceService.get_all_punches(db, employee_id, attendance_date)


# ─────────────────────────────────────────────────────────
# ADD TIME PUNCH  (+ button → modal → Insert)
# POST /api/attendance/daily/punch
# ─────────────────────────────────────────────────────────

@router.post("/punch", response_model=AddAttendancePunchOut,
             status_code=status.HTTP_201_CREATED)
def add_punch(
    payload:     AddAttendancePunchIn,
    db:          Session = Depends(get_db)
):
    """
    Add Time Punch modal → Insert button.

    Modal fields:
    - Employee Name (display only)
    - Punch Date   (date picker)
    - Punch Time   (HH · MM · SS three inputs)
    - Punch Type   (Selfie / Remote / Manual dropdown)
    - Remarks      (optional text)

    After insert: recalculates status, note, in_time_minutes for the day record.
    Returns the new punch + updated attendance card.
    """
    try:
        entry, record = PunchManagementService.add_punch(
            db=db,
            employee_id=payload.employee_id,
            punch_date=payload.punch_date,
            punch_time_str=payload.punch_time,
            direction=payload.direction,
            punch_type=payload.punch_type,
            remarks=payload.remarks,
            added_by=1)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    return {
        "message":        "Punch added successfully.",
        "punch":          entry,
        "updated_record": _build_card(db, record),
    }


# ─────────────────────────────────────────────────────────
# DELETE PUNCH  (trash icon inside … modal)
# DELETE /api/attendance/daily/punch/{punch_id}
# ─────────────────────────────────────────────────────────

@router.delete("/punch/{punch_id}", response_model=DeletePunchOut)
def delete_punch(
    punch_id:    uuid.UUID = Path(...),
    db:          Session   = Depends(get_db)
):
    """
    Trash icon in the '…' All Punches modal.
    Deletes a single punch entry and recalculates the attendance record.
    """
    try:
        entry, record = PunchManagementService.delete_punch(
            db=db,
            punch_id=str(punch_id),
            deleted_by=1)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))

    return {
        "message":        "Punch deleted successfully.",
        "punch_id":       entry.id,
        "updated_record": _build_card(db, record) if record else None,
    }





# ─────────────────────────────────────────────────────────
# IMPORT CSV  (Options → Upload)
# POST /api/attendance/daily/import
# ─────────────────────────────────────────────────────────

@router.post("/import", response_model=ImportResultOut,
             status_code=status.HTTP_201_CREATED)
async def import_csv(
    file:        UploadFile = File(...,
                    description="CSV — columns: code, date, punch_in, punch_out, "
                                "punch_type, status, location, department, "
                                "cost_center, business_unit, note"),
    db:          Session    = Depends(get_db)
):
    """
    Options → Upload button.
    Parses the CSV, creates / updates DailyAttendanceRecord rows,
    inserts AttendancePunchEntry rows, then recalculates each record.
    Returns a per-row error log for any failed rows.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Only .csv files are accepted.")

    content = await file.read()
    result  = ImportExportService.import_csv(
        db=db,
        file_content=content,
        filename=file.filename,
        uploaded_by=1)
    return result