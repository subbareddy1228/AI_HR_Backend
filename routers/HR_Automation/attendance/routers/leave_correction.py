"""
routers/leave_correction.py
FastAPI router — Leave Correction module.
Prefix : /api/attendance/leave-correction
Auth   : JWT via get_current_user / require_hr_admin

UI summary:
  Page      : paginated ledger table, month arrow nav, 4 org dropdowns,
              leave type dropdown (9 options), employee search, Options (Download/Upload)
  Table row : EMPLOYEE (name+code) | DESIGNATION | OPENING | ACTIVITY | CORRECTION (input) | CLOSING | Save btn
  Footer    : Note: "Corrections are added at the beginning of the period."
              + Previous / Page X of Y / Next
"""

import io
from datetime import date
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    Query, Path, UploadFile, File,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user

from schema.HR_Automation.leave_correction import (
    LeaveCorrectionListOut,
    LeaveCorrectionRowOut,
    SaveCorrectionIn,
    BulkSaveCorrectionIn,
    FilterOptionsOut,
    ImportResultOut,
    MessageResponse,
    period_label,
    parse_period,
    LEAVE_TYPE_OPTIONS,
    LEAVE_TYPE_CODES,
)
from services.HR_Automation.leave_correction_service import (
    FilterOptionsService,
    LeaveCorrectionListService,
    LeaveCorrectionSaveService,
    LeaveCorrectionExportService,
    LeaveCorrectionImportService,
)

router = APIRouter(
    prefix="/api/attendance/leave-correction",
    tags=["Leave Correction"],
)


# ─────────────────────────────────────────────────────────
# LEAVE TYPE OPTIONS  (populate leave type dropdown)
# GET /api/attendance/leave-correction/leave-types
# ─────────────────────────────────────────────────────────

@router.get("/leave-types")
def get_leave_types(
    current_user = Depends(get_current_user),
):
    """
    Returns the 9 leave type options for the dropdown:
    LV458 - Comp Off · LV454 - Present · LV455 - Absent
    LV456 - Holiday · LV457 - Week Off · LV459 - Casual Leave
    LV1055 - Leave without Pay · LV2638 - Sick Leave · LV2640 - Half Day
    """
    return {"leave_types": LEAVE_TYPE_OPTIONS}


# ─────────────────────────────────────────────────────────
# FILTER OPTIONS  (populate 4 org dropdowns)
# GET /api/attendance/leave-correction/filter-options
# ─────────────────────────────────────────────────────────

@router.get("/filter-options", response_model=FilterOptionsOut)
def get_filter_options(
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    """
    Called on page load to populate:
    Business Unit · Location · Cost Center · Department
    Also returns leave_type_options for the leave type dropdown.
    """
    return FilterOptionsService.get(db)


# ─────────────────────────────────────────────────────────
# MAIN TABLE  (paginated correction ledger)
# GET /api/attendance/leave-correction
# ─────────────────────────────────────────────────────────

@router.get("", response_model=LeaveCorrectionListOut)
def list_corrections(
    # ── Month arrow navigation ──
    year:            Optional[int] = Query(None, ge=2000, le=2100),
    month:           Optional[int] = Query(None, ge=1, le=12),
    period:          Optional[str] = Query(None,
                                           description="MMM-YYYY e.g. 'SEP-2025' — "
                                                       "alternative to year+month"),
    # ── Leave type dropdown (default: LV458 - Comp Off) ──
    leave_type_code: str           = Query("LV458",
                                           description="One of: LV458 LV454 LV455 LV456 "
                                                       "LV457 LV459 LV1055 LV2638 LV2640"),
    # ── 4 org dropdown filters ──
    business_unit:   Optional[str] = Query(None),
    location:        Optional[str] = Query(None),
    cost_center:     Optional[str] = Query(None),
    department:      Optional[str] = Query(None),
    # ── Employee search box (All Employees placeholder) ──
    search:          Optional[str] = Query(None,
                                           description="Employee name or code"),
    # ── Pagination ──
    page:            int           = Query(1,  ge=1),
    page_size:       int           = Query(10, ge=1, le=200),
    db:              Session       = Depends(get_db),
    current_user                   = Depends(get_current_user),
):
    """
    Main endpoint — powers the full Leave Correction table.

    Returns one row per active employee for the selected period + leave type.
    Employees without an existing correction record are auto-initialized:
      - opening  pulled from LeaveBalance
      - activity pulled from approved LeaveApplications
      - correction = 0  (editable)
      - closing  = opening + activity + correction

    Table columns:
    EMPLOYEE (name + code) | DESIGNATION | OPENING | ACTIVITY | CORRECTION | CLOSING | Save btn

    Footer note: "Corrections are added at the beginning of the period."
    """
    # Resolve period — accept either year+month integers or "SEP-2025" string
    if period:
        try:
            y, m = parse_period(period)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    elif year and month:
        y, m = year, month
    else:
        today = date.today()
        y, m  = today.year, today.month

    # Validate leave type code
    if leave_type_code.upper() not in LEAVE_TYPE_CODES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid leave_type_code '{leave_type_code}'. "
            f"Valid values: {sorted(LEAVE_TYPE_CODES)}",
        )

    return LeaveCorrectionListService.list_records(
        db=db,
        year=y,
        month=m,
        leave_type_code=leave_type_code.upper(),
        business_unit=business_unit,
        location=location,
        cost_center=cost_center,
        department=department,
        search=search,
        page=page,
        page_size=page_size,
    )


# ─────────────────────────────────────────────────────────
# SAVE ONE ROW  (green circle save button per row)
# POST /api/attendance/leave-correction/save
# ─────────────────────────────────────────────────────────

@router.post("/save", response_model=LeaveCorrectionRowOut)
def save_correction(
    payload:     SaveCorrectionIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Green circle button on each employee row.

    HR edits only the `correction` input field.
    Backend:
      1. Updates LeaveCorrectionRecord.correction
      2. Recomputes closing = opening + activity + correction
      3. Applies delta to LeaveBalance.balance
      4. Sets is_saved = True, saved_at = now()

    Returns the updated row so the frontend can refresh the row in-place.
    """
    if payload.leave_type_code.upper() not in LEAVE_TYPE_CODES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid leave_type_code '{payload.leave_type_code}'.",
        )
    try:
        row = LeaveCorrectionSaveService.save_row(
            db=db,
            employee_id=payload.employee_id,
            leave_type_code=payload.leave_type_code.upper(),
            year=payload.year,
            month=payload.month,
            correction=payload.correction,
            saved_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return row


# ─────────────────────────────────────────────────────────
# BULK SAVE  (save all rows in one call)
# POST /api/attendance/leave-correction/save-all
# ─────────────────────────────────────────────────────────

@router.post("/save-all", response_model=dict)
def bulk_save(
    payload:     BulkSaveCorrectionIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Save all visible rows at once.
    Useful for bulk correction workflows.
    Returns: { saved, failed[], message }
    """
    return LeaveCorrectionSaveService.bulk_save(
        db=db,
        rows=payload.rows,
        saved_by=current_user.id,
    )


# ─────────────────────────────────────────────────────────
# EXPORT CSV  (Options → Download → Download button)
# GET /api/attendance/leave-correction/export
# ─────────────────────────────────────────────────────────

@router.get("/export")
def export_corrections(
    year:            int           = Query(..., ge=2000, le=2100),
    month:           int           = Query(..., ge=1, le=12),
    leave_type_code: Optional[str] = Query(None,
                                           description="Filter by leave type code. "
                                                       "Omit to export all types."),
    location:        Optional[str] = Query(None),
    cost_center:     Optional[str] = Query(None),
    department:      Optional[str] = Query(None),
    db:              Session       = Depends(get_db),
    current_user                   = Depends(get_current_user),
):
    """
    Options → Download → Download button.

    Exports saved correction records as CSV.
    Filename: leave_corrections_SEP-2025.csv

    CSV columns:
    sl_no · employee_code · employee_name · designation
    business_unit · location · cost_center · department
    period · leave_type_code · leave_type_label
    opening · activity · correction · closing
    """
    lt_code = leave_type_code.upper() if leave_type_code else None

    csv_bytes = LeaveCorrectionExportService.export_csv(
        db=db,
        year=year,
        month=month,
        leave_type_code=lt_code,
        location=location,
        cost_center=cost_center,
        department=department,
    )
    filename = f"leave_corrections_{period_label(year, month)}.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─────────────────────────────────────────────────────────
# IMPORT CSV  (Options → Upload → Upload button)
# POST /api/attendance/leave-correction/import
# ─────────────────────────────────────────────────────────

@router.post("/import", response_model=ImportResultOut,
             status_code=status.HTTP_201_CREATED)
async def import_corrections(
    file:            UploadFile    = File(...,
                         description="CSV file. Required columns: "
                                     "code · leave_type_code · period (MMM-YYYY) · correction"),
    year:            int           = Query(..., ge=2000, le=2100,
                                           description="Target year"),
    month:           int           = Query(..., ge=1, le=12,
                                           description="Target month (1-12)"),
    leave_type_code: Optional[str] = Query(None,
                                           description="Default leave type code if not "
                                                       "specified per row in the CSV"),
    db:              Session       = Depends(get_db),
    current_user                   = Depends(get_current_user),
):
    """
    Options → Upload → Upload button.
    Accepts .xlsx / .xls / .csv files (frontend accept='.xlsx,.xls,.csv').
    Backend processes CSV only — convert XLSX on the frontend before upload,
    or extend with openpyxl for direct XLSX parsing.

    Required CSV columns:
      code · leave_type_code · period (MMM-YYYY) · correction

    Optional columns:
      opening · activity

    For each valid row:
      - Upserts LeaveCorrectionRecord
      - Applies correction delta to LeaveBalance

    Returns a batch summary with per-row errors for failed rows.
    """
    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only .csv, .xlsx, or .xls files are accepted.",
        )

    content = await file.read()

    # Convert XLSX/XLS to CSV bytes if needed
    if file.filename.lower().endswith((".xlsx", ".xls")):
        try:
            import openpyxl, io as _io
            wb  = openpyxl.load_workbook(_io.BytesIO(content), read_only=True)
            ws  = wb.active
            buf = _io.StringIO()
            import csv as _csv
            writer = _csv.writer(buf)
            for row in ws.iter_rows(values_only=True):
                writer.writerow([str(c) if c is not None else "" for c in row])
            content = buf.getvalue().encode("utf-8")
        except ImportError:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "openpyxl is required to process XLSX files. "
                "Install it with: pip install openpyxl",
            )

    lt_code = leave_type_code.upper() if leave_type_code else None

    try:
        batch = LeaveCorrectionImportService.import_csv(
            db=db,
            file_content=content,
            filename=file.filename,
            year=year,
            month=month,
            leave_type_code=lt_code,
            uploaded_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    return ImportResultOut(
        batch_id=batch.id,
        filename=batch.filename,
        period_label=period_label(year, month),
        leave_type_code=batch.leave_type_code or "",
        total_rows=batch.total_rows,
        success_rows=batch.success_rows,
        failed_rows=batch.failed_rows,
        errors=batch.error_log,
    )


