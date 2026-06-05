"""
routers/daily_punches.py
FastAPI router — Daily Punches module.
Prefix  : /api/attendance/daily-punches
Auth    : JWT via existing get_current_user / require_hr_admin helpers
"""

import uuid
import io
from datetime import date
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Query, Path,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user

from model.HR_Automation.daily_punches import (
    EmployeePunch, PunchDirectionEnum, PunchSourceEnum,
)
from schema.HR_Automation.daily_punches import (
    DailyPunchFilter, DailyPunchListOut, DailyPunchRowOut,
    AddPunchIn, PunchOut, DeletePunchResponse,
    SelfieModalOut, LocationModalOut, AllPunchesOut,
    ImportResultOut, FilterOptionsOut, MessageResponse,
)
from services.HR_Automation.daily_punches import (
    DailyPunchService, PunchManagementService,
    PunchImportService, PunchExportService, SummaryService,
)

router = APIRouter(
    prefix="/api/attendance/daily-punches",
    tags=["Daily Punches"],
)


# ─────────────────────────────────────────────────────────
# FILTER OPTIONS  (populate all 4 dropdowns on page load)
# GET /api/attendance/daily-punches/filter-options
# ─────────────────────────────────────────────────────────

@router.get("/filter-options", response_model=FilterOptionsOut)
def get_filter_options(
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    """
    Returns distinct values for Business Unit, Location, Cost Center, Departments.
    Called on page load to populate the 4 dropdowns.
    """
    return DailyPunchService.get_filter_options(db)


# ─────────────────────────────────────────────────────────
# MAIN TABLE  (paginated, filtered daily punch rows)
# GET /api/attendance/daily-punches
# ─────────────────────────────────────────────────────────

@router.get("", response_model=DailyPunchListOut)
def list_daily_punches(
    # ── Date picker (arrow nav) ──
    punch_date:     date            = Query(default_factory=date.today,
                                           description="DD/MM/YYYY in UI → sent as YYYY-MM-DD"),
    # ── 4 dropdown filters ──
    business_unit:  Optional[str]   = Query(None),
    location:       Optional[str]   = Query(None),
    cost_center:    Optional[str]   = Query(None),
    department:     Optional[str]   = Query(None),
    # ── Radio button filter ──
    status_filter:  Optional[str]   = Query(None,
                                           description="all | late | absent | nopunch"),
    # ── Employee search box ──
    search:         Optional[str]   = Query(None, description="Name / code / designation"),
    # ── Pagination ──
    page:           int             = Query(1, ge=1),
    page_size:      int             = Query(10, ge=1, le=200),
    db:             Session         = Depends(get_db),
    current_user                    = Depends(get_current_user),
):
    """
    Powers the main Daily Punches table.
    Applies all 7 filter controls + pagination.
    Returns: SN · Employee · Designation · Start · End · Duration · Attendance
    """
    f = DailyPunchFilter(
        punch_date=punch_date,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
        status_filter=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )
    return DailyPunchService.list_daily_punches(db, f)


# ─────────────────────────────────────────────────────────
# CAMERA ICON MODAL — Selfie / Registered Face
# GET /api/attendance/daily-punches/{employee_id}/selfie
# ─────────────────────────────────────────────────────────

@router.get("/{employee_id}/selfie", response_model=SelfieModalOut)
def get_selfie(
    employee_id:  str             = Path(...),
    punch_date:   date            = Query(...),
    direction:    str             = Query("IN", description="IN or OUT"),
    db:           Session         = Depends(get_db),
    current_user                  = Depends(get_current_user),
):
    """
    Opens the Selfie Punch Image modal (camera icon on Start or End column).
    Returns: Registered Face URL + Punch Image URL for side-by-side display.
    """
    direction = direction.upper()
    if direction not in ("IN", "OUT"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "direction must be IN or OUT")
    return DailyPunchService.get_selfie_data(db, employee_id, punch_date, direction)


# ─────────────────────────────────────────────────────────
# GPS PIN MODAL — Location Map
# GET /api/attendance/daily-punches/{employee_id}/location
# ─────────────────────────────────────────────────────────

@router.get("/{employee_id}/location", response_model=LocationModalOut)
def get_location(
    employee_id: str   = Path(...),
    punch_date:  date  = Query(...),
    direction:   str   = Query("IN", description="IN or OUT"),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Opens the Location modal (GPS pin icon on Start or End column).
    Returns: lat/lng + Google Maps embed URL for the iframe.
    """
    direction = direction.upper()
    if direction not in ("IN", "OUT"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "direction must be IN or OUT")
    return DailyPunchService.get_location_data(db, employee_id, punch_date, direction)


# ─────────────────────────────────────────────────────────
# ALL PUNCHES MODAL  (... button)
# GET /api/attendance/daily-punches/{employee_id}/all-punches
# ─────────────────────────────────────────────────────────

@router.get("/{employee_id}/all-punches", response_model=AllPunchesOut)
def get_all_punches(
    employee_id: str   = Path(...),
    punch_date:  date  = Query(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Opens the '...' All Punches modal.
    Returns all raw punch events for employee on selected date with IN/OUT badge
    and trash icon (delete) per punch.
    """
    return DailyPunchService.get_all_punches(db, employee_id, punch_date)


# ─────────────────────────────────────────────────────────
# ADD TIME PUNCH  (+ button → Insert modal)
# POST /api/attendance/daily-punches/punch
# ─────────────────────────────────────────────────────────

@router.post("/punch", response_model=PunchOut, status_code=status.HTTP_201_CREATED)
def add_punch(
    payload:     AddPunchIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Add Time Punch modal → Insert button.
    Fields: Employee · Punch Date · Punch Time (HH:MM:SS) · Punch Type · Remarks
    Automatically recalculates the daily summary after insertion.
    """
    try:
        punch = PunchManagementService.add_punch(
            db=db,
            employee_id=payload.employee_id,
            punch_date=payload.punch_date,
            punch_time_str=payload.punch_time,
            direction=payload.direction,
            source=payload.source,
            remarks=payload.remarks,
            latitude=payload.latitude,
            longitude=payload.longitude,
            location_url=payload.location_url,
            added_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return PunchOut.model_validate(punch)


# ─────────────────────────────────────────────────────────
# DELETE PUNCH  (trash icon inside All Punches modal)
# DELETE /api/attendance/daily-punches/punch/{punch_id}
# ─────────────────────────────────────────────────────────

@router.delete("/punch/{punch_id}", response_model=DeletePunchResponse)
def delete_punch(
    punch_id:    uuid.UUID = Path(...),
    db:          Session   = Depends(get_db),
    current_user           = Depends(get_current_user),
):
    """
    Delete a single punch entry (trash icon in the '...' modal list).
    Automatically recalculates the daily summary.
    """
    try:
        punch = PunchManagementService.delete_punch(db, punch_id, deleted_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return {"message": "Punch deleted successfully.", "punch_id": punch.id}


# ─────────────────────────────────────────────────────────
# EXPORT CSV  (Options → Download button)
# GET /api/attendance/daily-punches/export
# ─────────────────────────────────────────────────────────

@router.get("/export")
def export_csv(
    punch_date:     date            = Query(default_factory=date.today),
    business_unit:  Optional[str]   = Query(None),
    location:       Optional[str]   = Query(None),
    cost_center:    Optional[str]   = Query(None),
    department:     Optional[str]   = Query(None),
    status_filter:  Optional[str]   = Query(None),
    search:         Optional[str]   = Query(None),
    db:             Session         = Depends(get_db),
    current_user                    = Depends(get_current_user),
):
    """
    Options → Download button.
    Exports the currently visible (filtered) rows as CSV.
    Filename: daily_punches_YYYY_MM_DD.csv
    """
    f = DailyPunchFilter(
        punch_date=punch_date,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
        status_filter=status_filter,
        search=search,
        page=1,
        page_size=10_000,   # export all matching rows
    )
    result   = DailyPunchService.list_daily_punches(db, f)
    csv_bytes = PunchExportService.export_csv(result["items"], punch_date)
    filename  = f"daily_punches_{punch_date.strftime('%Y_%m_%d')}.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─────────────────────────────────────────────────────────
# IMPORT CSV  (Options → Upload button)
# POST /api/attendance/daily-punches/import
# ─────────────────────────────────────────────────────────

@router.post("/import", response_model=ImportResultOut, status_code=status.HTTP_201_CREATED)
async def import_csv(
    file:        UploadFile = File(..., description="CSV file — columns: code,date,time,direction,source,remarks"),
    db:          Session    = Depends(get_db),
    current_user            = Depends(get_current_user),
):
    """
    Options → Upload button.
    Accepts CSV with columns: code · date (YYYY-MM-DD) · time (HH:MM:SS) · direction (IN/OUT)
    Optional columns: source · remarks
    Returns import batch summary with per-row errors.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .csv files are supported.")

    content = await file.read()
    try:
        batch = PunchImportService.import_csv(
            db=db,
            file_content=content,
            filename=file.filename,
            uploaded_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    return ImportResultOut(
        batch_id=batch.id,
        filename=batch.filename,
        total_rows=batch.total_rows,
        success_rows=batch.success_rows,
        failed_rows=batch.failed_rows,
        errors=batch.error_log,
    )


# ─────────────────────────────────────────────────────────
# RECALCULATE SUMMARY  (admin utility)
# POST /api/attendance/daily-punches/recalculate
# ─────────────────────────────────────────────────────────

@router.post("/recalculate", response_model=MessageResponse)
def recalculate_summary(
    employee_id: str  = Query(...),
    punch_date:  date = Query(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Force-recalculate the daily summary for a specific employee + date.
    Useful after bulk edits or sync operations.
    """
    SummaryService.recalculate(db, employee_id, punch_date)
    return {"message": f"Summary recalculated for {employee_id} on {punch_date}."}


# ─────────────────────────────────────────────────────────
# PUNCH LEGEND  (static reference — shown in footer)
# GET /api/attendance/daily-punches/legend
# ─────────────────────────────────────────────────────────

@router.get("/legend")
def get_punch_legend():
    """
    Returns the Punch Legend shown at the bottom of the page.
    Remote · Selfie · Web/Chat · QR Scan · Biometric Fetch · Biometric Sync
    Manual · Excel Import · Missed · Time Relax · Travel · API
    + Processed / Pending status definitions.
    """
    return {
        "sources": [
            {"key": "remote",          "label": "Remote",          "icon": "fe-send",        "color": "info"},
            {"key": "selfie",          "label": "Selfie",          "icon": "fe-camera",      "color": "danger"},
            {"key": "web_chat",        "label": "Web/Chat",        "icon": "fe-globe",       "color": "success"},
            {"key": "qr_scan",         "label": "QR Scan",         "icon": "fe-grid",        "color": "dark"},
            {"key": "biometric_fetch", "label": "Biometric Fetch", "icon": "fe-fingerprint", "color": "dark"},
            {"key": "biometric_sync",  "label": "Biometric Sync",  "icon": "fe-refresh-cw",  "color": "warning"},
            {"key": "manual",          "label": "Manual",          "icon": "fe-edit",        "color": "muted"},
            {"key": "excel_import",    "label": "Excel Import",    "icon": "fe-file-text",   "color": "success"},
            {"key": "missed",          "label": "Missed",          "icon": "fe-clock",       "color": "danger"},
            {"key": "time_relax",      "label": "Time Relax",      "icon": "fe-clock",       "color": "warning"},
            {"key": "travel",          "label": "Travel",          "icon": "fe-truck",       "color": "primary"},
            {"key": "api",             "label": "API",             "icon": "fe-power",       "color": "success"},
        ],
        "statuses": [
            {"key": "processed", "label": "XX - Processed", "color": "success"},
            {"key": "pending",   "label": "XX - Pending",   "color": "danger"},
        ],
    }
