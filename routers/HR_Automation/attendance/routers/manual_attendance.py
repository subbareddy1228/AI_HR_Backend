"""
routers/manual_attendance.py
FastAPI router — Manual Attendance module.
Prefix : /api/attendance/manual
Auth   : JWT via get_current_user / require_hr_admin

UI summary:
  Page      : paginated table, month arrow nav, 4 org filter dropdowns,
              employee search box, Options dropdown (Download / Upload)
  Table row : Employee (name + code) | P | A | H | W | CO | CL | LW | Save toggle
  Pagination: Previous / Page X of Y / Next
"""

import io
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    Query, Path, UploadFile, File,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user

from schema.HR_Automation.manual_attendance import (
    ManualAttendanceListOut,
    ManualAttendanceRowOut,
    SaveAttendanceRowIn,
    BulkSaveIn,
    DownloadAttendanceIn,
    ImportResultOut,
    FilterOptionsOut,
    MessageResponse,
    # _period_label,
    parse_period,
)
from services.HR_Automation.manual_attendance_service import (
    FilterOptionsService,
    ManualAttendanceListService,
    ManualAttendanceSaveService,
    ManualAttendanceExportService,
    ManualAttendanceImportService,
)

router = APIRouter(
    prefix="/api/attendance/manual",
    tags=["Manual Attendance"],
)


# ─────────────────────────────────────────────────────────
# FILTER OPTIONS  (populate 4 dropdowns on page load)
# GET /api/attendance/manual/filter-options
# ─────────────────────────────────────────────────────────

@router.get("/filter-options", response_model=FilterOptionsOut)
def get_filter_options(
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    """
    Returns distinct values for:
    Business Unit · Location · Cost Center · Department
    Called on page load to hydrate all 4 dropdowns.
    """
    return FilterOptionsService.get(db)


# ─────────────────────────────────────────────────────────
# MAIN TABLE  (paginated attendance grid)
# GET /api/attendance/manual
# ─────────────────────────────────────────────────────────

@router.get("", response_model=ManualAttendanceListOut)
def list_manual_attendance(
    # ── Month arrow navigation ──
    # Accept either:  year+month integers  OR  period string e.g. "SEP-2025"
    year:          Optional[int] = Query(None, ge=2000, le=2100),
    month:         Optional[int] = Query(None, ge=1, le=12),
    period:        Optional[str] = Query(None,
                                         description="MMM-YYYY e.g. 'SEP-2025' — "
                                                     "alternative to year+month"),
    # ── 4 dropdown filters ──
    business_unit: Optional[str] = Query(None),
    location:      Optional[str] = Query(None),
    cost_center:   Optional[str] = Query(None),
    department:    Optional[str] = Query(None),
    # ── Employee search box ──
    search:        Optional[str] = Query(None,
                                         description="Employee name or code"),
    # ── Pagination (Previous / Page X of Y / Next) ──
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(10, ge=1, le=200),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(get_current_user),
):
    """
    Main endpoint — powers the full Manual Attendance table.

    Returns one row per active employee for the selected month.
    Employees without an existing record get zero-filled rows
    so HR can enter values directly.

    Each row:  Sl.No | Employee (name + code) | P | A | H | W | CO | CL | LW | is_saved
    """
    # Resolve period
    if period:
        try:
            y, m = parse_period(period)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    elif year and month:
        y, m = year, month
    else:
        from datetime import date
        today = date.today()
        y, m  = today.year, today.month

    return ManualAttendanceListService.list_records(
        db=db,
        year=y,
        month=m,
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
        search=search,
        page=page,
        page_size=page_size,
    )


# ─────────────────────────────────────────────────────────
# SAVE ONE ROW  (green toggle / save button per row)
# POST /api/attendance/manual/save
# ─────────────────────────────────────────────────────────

@router.post("/save", response_model=ManualAttendanceRowOut,
             status_code=status.HTTP_200_OK)
def save_attendance_row(
    payload:     SaveAttendanceRowIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Save button (green toggle icon) on each employee row.

    Validates that total days (P+A+H+W+CO+CL+LW) does not exceed
    the number of days in the selected month.

    Upserts the record and returns the updated row
    (frontend updates the toggle state to reflect saved=True).
    """
    try:
        row = ManualAttendanceSaveService.save_row(
            db=db,
            employee_id=payload.employee_id,
            year=payload.year,
            month=payload.month,
            counts=payload.counts.model_dump(),
            saved_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return row


# ─────────────────────────────────────────────────────────
# BULK SAVE  (all rows at once — optional, for future use)
# POST /api/attendance/manual/save-all
# ─────────────────────────────────────────────────────────

@router.post("/save-all", response_model=dict)
def bulk_save(
    payload:     BulkSaveIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Save all visible rows at once.
    Returns count of saved vs failed rows.
    """
    return ManualAttendanceSaveService.bulk_save(
        db=db,
        year=payload.year,
        month=payload.month,
        rows=payload.rows,
        saved_by=current_user.id,
    )


# ─────────────────────────────────────────────────────────
# DOWNLOAD ATTENDANCE  (Options → Download Attendance modal)
# GET /api/attendance/manual/export
# ─────────────────────────────────────────────────────────

@router.get("/export")
def download_attendance(
    # ── Period (already shown in modal header) ──
    year:        int           = Query(..., ge=2000, le=2100),
    month:       int           = Query(..., ge=1, le=12),
    # ── 3 modal filter dropdowns ──
    location:    Optional[str] = Query(None),
    cost_center: Optional[str] = Query(None),
    department:  Optional[str] = Query(None),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """
    Options → Download Attendance → Download button.

    Modal fields: Period (read-only) · Location · Cost Center · Department
    Returns CSV with columns:
      sl_no · employee_code · employee_name · business_unit · location
      cost_center · department · period · P · A · H · W · CO · CL · LW

    Filename: manual_attendance_SEP-2025.csv
    """
    csv_bytes = ManualAttendanceExportService.export_csv(
        db=db,
        year=year,
        month=month,
        location=location,
        cost_center=cost_center,
        department=department,
    )
    filename = f"manual_attendance_{_period_label(year, month)}.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─────────────────────────────────────────────────────────
# UPLOAD ATTENDANCE  (Options → Upload Attendance modal)
# POST /api/attendance/manual/import
# ─────────────────────────────────────────────────────────

@router.post("/import", response_model=ImportResultOut,
             status_code=status.HTTP_201_CREATED)
async def upload_attendance(
    file:        UploadFile = File(...,
                    description="CSV file. Required columns: "
                                "code · period (MMM-YYYY) · P · A · H · W · CO · CL · LW"),
    year:        int        = Query(..., ge=2000, le=2100,
                                    description="Target year for import"),
    month:       int        = Query(..., ge=1, le=12,
                                    description="Target month for import (1-12)"),
    db:          Session    = Depends(get_db),
    current_user            = Depends(get_current_user),
):
    """
    Options → Upload Attendance → Upload button.

    Modal fields: Period (read-only) · Select File (file input)

    Accepts a CSV file. Upserts ManualAttendanceRecord for each row.
    Returns a batch summary with per-row errors for any failed rows.

    Required CSV columns:
      code · period · P · A · H · W · CO · CL · LW

    Optional columns:
      employee_name · business_unit · location · cost_center · department
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only .csv files are accepted.",
        )

    content = await file.read()
    try:
        batch = ManualAttendanceImportService.import_csv(
            db=db,
            file_content=content,
            filename=file.filename,
            year=year,
            month=month,
            uploaded_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    return ImportResultOut(
        batch_id=batch.id,
        filename=batch.filename,
        period_label=_period_label(year, month),
        total_rows=batch.total_rows,
        success_rows=batch.success_rows,
        failed_rows=batch.failed_rows,
        errors=batch.error_log,
    )
