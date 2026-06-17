"""
routers/regularization.py
FastAPI router — Regularization Workflow module (all 4 tabs).
Prefix : /api/attendance/regularization
Auth   : JWT via get_current_user / require_hr_admin
"""

import io
import os
import uuid
from datetime import date
from typing import Optional, List

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    Query, Path, UploadFile, File, Form,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user

from model.HR_Automation.regularization import (
    RequestTypeEnum, RequestStatusEnum,
)
from schema.HR_Automation.regularization import (
    RegularizationRequestIn, RegularizationRequestOut,
    RegularizationListOut, ApproveRejectIn,
    AutoRejectRuleOut, AutoRejectRuleUpdateIn,
    RequestStatisticsOut,
    BulkProcessIn, BulkProcessOut,
    GenerateReportIn, RegularizationReportOut,
    MessageResponse,
)
from services.HR_Automation.regularization_service import (
    RegularizationRequestService,
    AutoRejectService,
    SettingsService,
    BulkProcessingService,
    ReportsService,
    seed_auto_reject_rules,
)

router = APIRouter(
    prefix="/api/attendance/regularization",
    tags=["Regularization Workflow"],
)

UPLOAD_DIR = os.getenv("REGULARIZATION_UPLOAD_DIR", "/tmp/regularization_attachments")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════
# TAB 1 — REQUESTS
# ══════════════════════════════════════════════════════════

@router.get("", response_model=RegularizationListOut)
def list_requests(
    # ── Search box ──
    search:       Optional[str]              = Query(None,
                                                     description="Search by employee name or reason"),
    # ── All Status dropdown ──
    status_filter:Optional[str]              = Query(None, alias="status",
                                                     description="pending|approved|rejected|auto-rejected"),
    # ── All Types dropdown ──
    type_filter:  Optional[str]              = Query(None, alias="type",
                                                     description="missing|incorrect|forgot|wfh|on_duty"),
    # ── Pagination ──
    page:         int                        = Query(1,  ge=1),
    page_size:    int                        = Query(20, ge=1, le=200),
    db:           Session                    = Depends(get_db),
    current_user                             = Depends(get_current_user),
):
    """
    Requests tab — Regularization Requests table.
    Columns: Employee · Type badge · Date/Time · Reason · Status badge
             Submitted · Actions (✓ Approve  ✗ Reject  👁 View  📎 Attachment)

    Filters:
      Search box       → employee name or reason text
      All Status       → pending | approved | rejected | auto-rejected
      All Types        → missing | incorrect | forgot | wfh | on_duty
    """
    st = RequestStatusEnum(status_filter) if status_filter else None
    rt = RequestTypeEnum(type_filter)     if type_filter   else None
    return RegularizationRequestService.list(db, search, st, rt, page, page_size)


@router.post("", response_model=RegularizationRequestOut,
             status_code=status.HTTP_201_CREATED)
async def create_request(
    # JSON body fields
    employeeId:    str                    = Form(...),
    requestType:   RequestTypeEnum        = Form(...),
    reason:        str                    = Form(...),
    remarks:       str                    = Form(...),
    # missing punch
    dateTime:      Optional[str]          = Form(None),
    # incorrect time
    originalTime:  Optional[str]          = Form(None),
    correctedTime: Optional[str]          = Form(None),
    # forgot punch
    date_field:    Optional[str]          = Form(None, alias="date"),
    punchType:     Optional[str]          = Form(None),
    approxTime:    Optional[str]          = Form(None),
    # wfh
    location:      Optional[str]          = Form(None),
    summary:       Optional[str]          = Form(None),
    # on-duty
    fromTime:      Optional[str]          = Form(None),
    toTime:        Optional[str]          = Form(None),
    dutyType:      Optional[str]          = Form(None),
    purpose:       Optional[str]          = Form(None),
    # file attachment
    attachment:    Optional[UploadFile]   = File(None),
    db:            Session                = Depends(get_db),
    current_user                          = Depends(get_current_user),
):
    """
    + New Request button → New Regularization Request modal → Submit Request.

    Modal fields depend on Request Type:
      Missing Punch   → Date & Time (datetime-local)
      Incorrect Time  → Original Time + Corrected Time
      Forgot Punch    → Date + Punch Type (IN/OUT) + Approx Time
      WFH             → Date + Location + Work Summary
      On-Duty         → Date + From/To Time + Duty Type + Purpose/Location

    All types: Reason* · Remarks* · Attachment (PDF/JPG/PNG/DOC)

    Builds 2-level approval workflow:
      Level 1: Manager
      Level 2: HR
    """
    # Save attachment
    attachment_path = None
    if attachment:
        ext  = attachment.filename.rsplit(".", 1)[-1]
        fname = f"{uuid.uuid4()}.{ext}"
        attachment_path = os.path.join(UPLOAD_DIR, fname)
        with open(attachment_path, "wb") as f:
            f.write(await attachment.read())

    # Parse datetime strings to Python objects
    from datetime import datetime as dt
    def _parse_dt(s): return dt.fromisoformat(s) if s else None
    def _parse_d(s):  return dt.fromisoformat(s).date() if s else None

    # Build payload object manually (Form data can't use Pydantic directly with File)
    class _Payload:
        pass

    p = _Payload()
    p.employeeId    = employeeId
    p.requestType   = requestType
    p.reason        = reason
    p.remarks       = remarks
    p.dateTime      = _parse_dt(dateTime)
    p.originalTime  = _parse_dt(originalTime)
    p.correctedTime = _parse_dt(correctedTime)
    p.date          = _parse_d(date_field)
    p.punchType     = punchType
    p.approxTime    = approxTime
    p.location      = location
    p.summary       = summary
    p.fromTime      = fromTime
    p.toTime        = toTime
    p.dutyType      = dutyType
    p.purpose       = purpose

    # Validate required fields by type
    if requestType == RequestTypeEnum.missing and not dateTime:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "dateTime is required for Missing Punch.")
    if requestType == RequestTypeEnum.incorrect and (not originalTime or not correctedTime):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "originalTime and correctedTime are required for Incorrect Time.")
    if requestType == RequestTypeEnum.forgot and not date_field:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "date is required for Forgot Punch.")
    if requestType == RequestTypeEnum.wfh and (not date_field or not location):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "date and location are required for WFH.")
    if requestType == RequestTypeEnum.on_duty and (not date_field or not fromTime or not toTime):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "date, fromTime, toTime are required for On-Duty.")

    return RegularizationRequestService.create(
        db=db,
        payload=p,
        created_by=current_user.id,
        attachment_path=attachment_path,
    )

# ══════════════════════════════════════════════════════════
# AUTO-REJECT CRON TRIGGER
# ══════════════════════════════════════════════════════════

@router.post("/run-auto-reject", response_model=MessageResponse)
def run_auto_reject(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Manually trigger auto-reject processing.
    In production this is called by a cron job every hour.
    Auto-rejects pending requests that have exceeded their rule's day limit.
    """
    count = AutoRejectService.run(db)
    return {"message": f"Auto-reject complete — {count} request(s) rejected."}


@router.get("/{request_id}", response_model=RegularizationRequestOut)
def get_request(
    request_id:  int     = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """👁 View Details — opens the Request Details & Approval modal."""
    try:
        return RegularizationRequestService.get(db, request_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.post("/{request_id}/decide", response_model=RegularizationRequestOut)
def decide_request(
    request_id:  int            = Path(...),
    payload:     ApproveRejectIn = ...,
    db:          Session        = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    """
    ✓ Approve / ✗ Reject / Request Changes buttons.

    action values:
      approve          → sets status=approved, records approvedAt
      reject           → sets status=rejected, stores rejectionReason
      request_changes  → stays pending, appends remark to workflow

    Updates approval_workflow steps accordingly.
    """
    if payload.action not in ("approve", "reject", "request_changes"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "action must be: approve | reject | request_changes")
    try:
        return RegularizationRequestService.decide(
            db=db,
            request_id=request_id,
            action=payload.action,
            remarks=payload.remarks,
            decided_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.delete("/{request_id}", response_model=MessageResponse)
def delete_request(
    request_id:  int     = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Delete a regularization request (HR Admin only)."""
    try:
        RegularizationRequestService.delete(db, request_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return {"message": f"Request {request_id} deleted."}





# ══════════════════════════════════════════════════════════
# TAB 2 — SETTINGS
# ══════════════════════════════════════════════════════════

@router.get("/settings/rules", response_model=List[AutoRejectRuleOut])
def list_auto_reject_rules(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Settings tab — Auto-Reject Rules table.
    Columns: Request Type · Days · Status (Enabled/Disabled) · Actions (Enable/Disable)
    Default rules: Missing Punch = 7 days · Forgot Punch = 5 days
    """
    return SettingsService.list_rules(db)


@router.patch("/settings/rules/{rule_id}/toggle",
              response_model=AutoRejectRuleOut)
def toggle_auto_reject_rule(
    rule_id:     int     = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Enable / Disable button on each rule row.
    Toggles the rule's enabled flag.
    Button label changes: 'Disable' when enabled · 'Enable' when disabled.
    """
    try:
        return SettingsService.toggle_rule(db, rule_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.put("/settings/rules/{rule_id}", response_model=AutoRejectRuleOut)
def update_auto_reject_rule(
    rule_id:     int                    = Path(...),
    payload:     AutoRejectRuleUpdateIn = ...,
    db:          Session                = Depends(get_db),
    current_user                        = Depends(get_current_user),
):
    """Update days or enabled flag for an auto-reject rule."""
    try:
        return SettingsService.update_rule(db, rule_id, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.get("/settings/statistics", response_model=RequestStatisticsOut)
def get_statistics(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Settings tab — Request Statistics right panel.
    Returns: Total Requests · Pending · Approved · Rejected (coloured count cards).
    """
    return SettingsService.get_statistics(db)


# ══════════════════════════════════════════════════════════
# TAB 3 — BULK PROCESSING
# ══════════════════════════════════════════════════════════

@router.get("/bulk", response_model=List[BulkProcessOut])
def list_bulk_processes(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Bulk Processing tab — history table.
    Columns: Date Range · Issue Type · Processed (N employees)
             Status badge · Processed By
    """
    return BulkProcessingService.list(db)


@router.post("/bulk", response_model=BulkProcessOut,
             status_code=status.HTTP_201_CREATED)
async def process_bulk(
    fromDate:    str                = Form(...),
    toDate:      str                = Form(...),
    issueType:   str                = Form(...),
    employeeIds: Optional[str]      = Form(None,
                                           description="Comma-separated employee IDs. "
                                                       "Leave empty to process all."),
    file:        Optional[UploadFile] = File(None,
                                             description="CSV/Excel with employee IDs"),
    db:          Session            = Depends(get_db),
    current_user                    = Depends(get_current_user),
):
    """
    + Process Bulk button → Bulk Regularization Processing modal.

    Modal fields:
      From Date* · To Date* · Issue Type*
        (System Failure | Device Malfunction | Sync Error | Network Failure | Other)
      Upload Employee List (CSV/Excel — optional, process all if omitted)

    For each affected employee:
      Creates an auto-approved RegularizationRequest for the date range.
    Stores a BulkRegularizationProcess audit record.
    """
    from datetime import datetime as _dt
    from models.regularization import IssueTypeEnum as _IT

    # Parse dates
    try:
        fd = _dt.fromisoformat(fromDate).date()
        td = _dt.fromisoformat(toDate).date()
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Invalid date format. Use YYYY-MM-DD.")

    if td < fd:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "toDate must be >= fromDate.")

    try:
        issue = _IT(issueType)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Invalid issueType '{issueType}'.")

    # Parse employee IDs
    emp_ids = []
    if employeeIds:
        emp_ids = [e.strip() for e in employeeIds.split(",") if e.strip()]

    # Parse CSV file if uploaded
    file_path = None
    if file:
        content = await file.read()
        fname   = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, fname)
        with open(file_path, "wb") as f_out:
            f_out.write(content)

        # Parse CSV to get employee IDs
        if file.filename.lower().endswith(".csv") and not emp_ids:
            import csv as _csv
            reader = _csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            for row in reader:
                code = row.get("code") or row.get("employee_id") or row.get("id")
                if code:
                    emp_ids.append(code.strip())

    class _Payload:
        pass
    p = _Payload()
    p.fromDate    = fd
    p.toDate      = td
    p.issueType   = issue
    p.employeeIds = emp_ids

    batch = BulkProcessingService.process(
        db=db,
        payload=p,
        file_path=file_path,
        processed_by=current_user.id,
        processed_by_name=getattr(current_user, "name", "HR Admin"),
    )
    return BulkProcessOut.model_validate(batch)


# ══════════════════════════════════════════════════════════
# TAB 4 — REPORTS
# ══════════════════════════════════════════════════════════

@router.get("/reports", response_model=List[RegularizationReportOut])
def list_reports(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Reports tab — Generated Reports history table.
    Columns: Date Range · Type · Format badge · Generated At
             File Name · Total Records
    """
    return ReportsService.list(db)


@router.post("/reports/generate")
def generate_report(
    payload:     GenerateReportIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Reports tab → Generate Report button.

    Form fields:
      From Date* · To Date* · Request Type (All | specific) · Format (PDF/Excel/CSV)

    Returns CSV download regardless of selected format (extend with reportlab/openpyxl
    for true PDF/Excel rendering).
    Also saves a RegularizationReport audit row for the Generated Reports table.
    """
    report, csv_bytes = ReportsService.generate(
        db=db,
        payload=payload,
        generated_by=current_user.id,
        generated_by_name=getattr(current_user, "name", "HR Admin"),
    )

    media_type = {
        "pdf":   "text/csv",        # extend with reportlab for true PDF
        "excel": "text/csv",        # extend with openpyxl for true XLSX
        "csv":   "text/csv",
    }.get(payload.format.value, "text/csv")

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={report.file_name}",
            "X-Report-ID":         str(report.id),
            "X-Total-Records":     str(report.total_records),
        },
    )
