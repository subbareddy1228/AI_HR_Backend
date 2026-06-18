import csv
import io
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from core.database import get_db
from model.HR_Automation.regularization import (
    RegularizationRequest,
    RegularizationAutoRejectRule,
    RegularizationStatus,
)
from model.onboarding.employee import Employee
from schema.HR_Automation.regularization import (
    RegularizationRequestCreate,
    RegularizationRequestUpdate,
    RegularizationRequestResponse,
    RegularizationReviewAction,
    PaginatedRegularizationRequests,
    AutoRejectRuleCreate,
    AutoRejectRuleUpdate,
    AutoRejectRuleResponse,
    RegularizationStatistics,
    BulkRegularizationCreate,
    BulkRegularizationResult,
    ReportFormat,
)

router = APIRouter(prefix="/regularization", tags=["Regularization"])


DEFAULT_AUTO_REJECT_RULES = [
    {"request_type": "Missing Punch", "days_threshold": 7, "is_enabled": True},
    {"request_type": "Forgot Punch", "days_threshold": 5, "is_enabled": True},
]

REQUEST_TYPES = [
    "Missing Punch",
    "Forgot Punch",
    "Wrong Punch In",
    "Wrong Punch Out",
    "Early Departure",
    "Late Arrival",
    "Work From Home",
    "On Duty",
    "Other",
]




def _ensure_default_rules(db: Session) -> None:
    existing_types = {r.request_type for r in db.query(RegularizationAutoRejectRule).all()}
    created = False
    for default in DEFAULT_AUTO_REJECT_RULES:
        if default["request_type"] not in existing_types:
            db.add(RegularizationAutoRejectRule(**default))
            created = True
    if created:
        db.commit()


def _apply_auto_reject(db: Session) -> None:
   
    rules = db.query(RegularizationAutoRejectRule).filter(
        RegularizationAutoRejectRule.is_enabled == True  # noqa: E712
    ).all()
    if not rules:
        return

    now = datetime.utcnow()
    changed = False
    for rule in rules:
        cutoff = now - timedelta(days=rule.days_threshold)
        stale = db.query(RegularizationRequest).filter(
            RegularizationRequest.request_type == rule.request_type,
            RegularizationRequest.status == RegularizationStatus.pending,
            RegularizationRequest.submitted_at <= cutoff,
        ).all()
        for req in stale:
            req.status = RegularizationStatus.rejected
            req.review_comments = (
                f"Auto-rejected — no action taken within {rule.days_threshold} day(s)."
            )
            req.reviewed_at = now
            changed = True

    if changed:
        db.commit()


def _employee_lookup(db: Session, employee_ids: List[int]) -> dict:
    if not employee_ids:
        return {}
    rows = db.query(Employee).filter(Employee.id.in_(set(employee_ids))).all()
    return {e.id: e for e in rows}


def _employee_full_name(employee: Optional[Employee]) -> Optional[str]:
    if not employee:
        return None
    parts = [employee.first_name, employee.middle_name, employee.last_name]
    return " ".join(p for p in parts if p) or None


def _serialize(req: RegularizationRequest, employee: Optional[Employee]) -> dict:
    return {
        "id": req.id,
        "employee_id": req.employee_id,
        "employee_name": _employee_full_name(employee),
        "employee_code": employee.employee_code if employee else None,
        "department": employee.department if employee else None,
        "request_type": req.request_type,
        "request_date": req.request_date,
        "original_check_in": req.original_check_in,
        "original_check_out": req.original_check_out,
        "requested_check_in": req.requested_check_in,
        "requested_check_out": req.requested_check_out,
        "reason": req.reason,
        "status": req.status.value if hasattr(req.status, "value") else req.status,
        "submitted_at": req.submitted_at,
        "reviewed_by": req.reviewed_by,
        "reviewed_at": req.reviewed_at,
        "review_comments": req.review_comments,
        "is_bulk": req.is_bulk,
    }




@router.get("/requests", response_model=PaginatedRegularizationRequests)
def list_requests(
    search: Optional[str] = Query(None, description="Search by employee name or employee code"),
    status: Optional[str] = Query(None, description="Pending | Approved | Rejected"),
    request_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    _apply_auto_reject(db)

    query = db.query(RegularizationRequest)
    if status and status.lower() != "all":
        query = query.filter(RegularizationRequest.status == status)
    if request_type and request_type.lower() != "all":
        query = query.filter(RegularizationRequest.request_type == request_type)

    requests = query.order_by(RegularizationRequest.submitted_at.desc()).all()
    employees = _employee_lookup(db, [r.employee_id for r in requests])

    if search:
        needle = search.strip().lower()
        filtered = []
        for r in requests:
            emp = employees.get(r.employee_id)
            name = (_employee_full_name(emp) or "").lower()
            code = (emp.employee_code or "").lower() if emp else ""
            if needle in name or needle in code:
                filtered.append(r)
        requests = filtered

    items = [_serialize(r, employees.get(r.employee_id)) for r in requests]
    return {"total": len(items), "items": items}


@router.post("/requests", response_model=RegularizationRequestResponse, status_code=201)
def create_request(payload: RegularizationRequestCreate, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    req = RegularizationRequest(**payload.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    return _serialize(req, employee)


@router.get("/requests/{request_id}", response_model=RegularizationRequestResponse)
def get_request(request_id: int, db: Session = Depends(get_db)):
    req = db.query(RegularizationRequest).filter(RegularizationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Regularization request not found")
    employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
    return _serialize(req, employee)


@router.patch("/requests/{request_id}", response_model=RegularizationRequestResponse)
def update_request(
    request_id: int, payload: RegularizationRequestUpdate, db: Session = Depends(get_db)
):
    req = db.query(RegularizationRequest).filter(RegularizationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Regularization request not found")
    if req.status != RegularizationStatus.pending:
        raise HTTPException(status_code=400, detail="Only pending requests can be edited")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(req, key, value)
    db.commit()
    db.refresh(req)
    employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
    return _serialize(req, employee)


@router.post("/requests/{request_id}/review", response_model=RegularizationRequestResponse)
def review_request(
    request_id: int, payload: RegularizationReviewAction, db: Session = Depends(get_db)
):
    
    req = db.query(RegularizationRequest).filter(RegularizationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Regularization request not found")
    if req.status != RegularizationStatus.pending:
        raise HTTPException(status_code=400, detail=f"Request is already {req.status.value}")
    if payload.status not in ("Approved", "Rejected"):
        raise HTTPException(status_code=400, detail="status must be Approved or Rejected")

    req.status = RegularizationStatus(payload.status)
    req.review_comments = payload.review_comments
    req.reviewed_by = payload.reviewed_by
    req.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
    return _serialize(req, employee)


@router.delete("/requests/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db)):
    req = db.query(RegularizationRequest).filter(RegularizationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Regularization request not found")
    db.delete(req)
    db.commit()
    return {"message": "Regularization request deleted successfully"}


@router.get("/request-types")
def list_request_types():
   
    return REQUEST_TYPES




@router.get("/settings/auto-reject-rules", response_model=List[AutoRejectRuleResponse])
def list_auto_reject_rules(db: Session = Depends(get_db)):
    _ensure_default_rules(db)
    return db.query(RegularizationAutoRejectRule).order_by(RegularizationAutoRejectRule.id).all()


@router.post("/settings/auto-reject-rules", response_model=AutoRejectRuleResponse, status_code=201)
def create_auto_reject_rule(payload: AutoRejectRuleCreate, db: Session = Depends(get_db)):
    existing = db.query(RegularizationAutoRejectRule).filter(
        RegularizationAutoRejectRule.request_type == payload.request_type
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="A rule for this request type already exists")
    rule = RegularizationAutoRejectRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/settings/auto-reject-rules/{rule_id}", response_model=AutoRejectRuleResponse)
def update_auto_reject_rule(
    rule_id: int, payload: AutoRejectRuleUpdate, db: Session = Depends(get_db)
):
    rule = db.query(RegularizationAutoRejectRule).filter(
        RegularizationAutoRejectRule.id == rule_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Auto-reject rule not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/settings/auto-reject-rules/{rule_id}/toggle", response_model=AutoRejectRuleResponse)
def toggle_auto_reject_rule(rule_id: int, db: Session = Depends(get_db)):
    
    rule = db.query(RegularizationAutoRejectRule).filter(
        RegularizationAutoRejectRule.id == rule_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Auto-reject rule not found")
    rule.is_enabled = not rule.is_enabled
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/settings/auto-reject-rules/{rule_id}")
def delete_auto_reject_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(RegularizationAutoRejectRule).filter(
        RegularizationAutoRejectRule.id == rule_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Auto-reject rule not found")
    db.delete(rule)
    db.commit()
    return {"message": "Auto-reject rule deleted successfully"}


@router.get("/settings/statistics", response_model=RegularizationStatistics)
def get_statistics(db: Session = Depends(get_db)):
    
    _apply_auto_reject(db)

    total = db.query(func.count(RegularizationRequest.id)).scalar() or 0
    pending = db.query(func.count(RegularizationRequest.id)).filter(
        RegularizationRequest.status == RegularizationStatus.pending
    ).scalar() or 0
    approved = db.query(func.count(RegularizationRequest.id)).filter(
        RegularizationRequest.status == RegularizationStatus.approved
    ).scalar() or 0
    rejected = db.query(func.count(RegularizationRequest.id)).filter(
        RegularizationRequest.status == RegularizationStatus.rejected
    ).scalar() or 0

    return {
        "total_requests": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
    }




@router.post("/bulk-process", response_model=BulkRegularizationResult, status_code=201)
def bulk_process(payload: BulkRegularizationCreate, db: Session = Depends(get_db)):
    
    employees = db.query(Employee).filter(Employee.id.in_(payload.employee_ids)).all()
    found_ids = {e.id for e in employees}
    missing = [eid for eid in payload.employee_ids if eid not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Employees not found: {missing}")

    batch_id = uuid.uuid4().hex[:12]
    now = datetime.utcnow()
    created_ids: List[int] = []

    for emp_id in payload.employee_ids:
        req = RegularizationRequest(
            employee_id=emp_id,
            request_type=payload.request_type,
            request_date=payload.request_date,
            requested_check_in=payload.requested_check_in,
            requested_check_out=payload.requested_check_out,
            reason=payload.reason,
            is_bulk=True,
            bulk_batch_id=batch_id,
            status=RegularizationStatus.approved if payload.auto_approve else RegularizationStatus.pending,
            reviewed_at=now if payload.auto_approve else None,
            review_comments="Auto-approved via bulk processing" if payload.auto_approve else None,
        )
        db.add(req)
        db.flush()
        created_ids.append(req.id)

    db.commit()
    return {
        "batch_id": batch_id,
        "created_count": len(created_ids),
        "auto_approved": payload.auto_approve,
        "request_ids": created_ids,
    }


@router.get("/bulk-process/{batch_id}", response_model=PaginatedRegularizationRequests)
def get_bulk_batch(batch_id: str, db: Session = Depends(get_db)):
    requests = db.query(RegularizationRequest).filter(
        RegularizationRequest.bulk_batch_id == batch_id
    ).all()
    if not requests:
        raise HTTPException(status_code=404, detail="Batch not found")
    employees = _employee_lookup(db, [r.employee_id for r in requests])
    items = [_serialize(r, employees.get(r.employee_id)) for r in requests]
    return {"total": len(items), "items": items}




REPORT_HEADERS = [
    "Employee", "Employee Code", "Type", "Date",
    "Requested In", "Requested Out", "Reason", "Status", "Submitted",
]


def _report_rows(db: Session, from_date: date, to_date: date, request_type: Optional[str]) -> List[dict]:
    query = db.query(RegularizationRequest).filter(
        RegularizationRequest.request_date >= from_date,
        RegularizationRequest.request_date <= to_date,
    )
    if request_type and request_type.lower() != "all":
        query = query.filter(RegularizationRequest.request_type == request_type)

    requests = query.order_by(RegularizationRequest.request_date).all()
    employees = _employee_lookup(db, [r.employee_id for r in requests])

    rows = []
    for r in requests:
        emp = employees.get(r.employee_id)
        rows.append({
            "Employee": _employee_full_name(emp) or f"#{r.employee_id}",
            "Employee Code": emp.employee_code if emp else "",
            "Type": r.request_type,
            "Date": r.request_date.isoformat(),
            "Requested In": r.requested_check_in or "",
            "Requested Out": r.requested_check_out or "",
            "Reason": r.reason,
            "Status": r.status.value if hasattr(r.status, "value") else r.status,
            "Submitted": r.submitted_at.strftime("%Y-%m-%d %H:%M"),
        })
    return rows


def _csv_response(rows: List[dict], filename_base: str) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REPORT_HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename_base}.csv"},
    )


def _excel_response(rows: List[dict], filename_base: str) -> StreamingResponse:
    

    wb = Workbook()
    ws = wb.active
    ws.title = "Regularization Report"
    ws.append(REPORT_HEADERS)
    for row in rows:
        ws.append([row.get(h, "") for h in REPORT_HEADERS])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename_base}.xlsx"},
    )


def _pdf_response(rows: List[dict], filename_base: str, from_date: date, to_date: date) -> StreamingResponse:
    

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Regularization Report", styles["Title"]),
        Paragraph(f"{from_date.isoformat()} to {to_date.isoformat()}", styles["Normal"]),
        Spacer(1, 12),
    ]

    data = [REPORT_HEADERS] + [[row.get(h, "") for h in REPORT_HEADERS] for row in rows]
    if not rows:
        data.append(["No records found for the selected filters."] + [""] * (len(REPORT_HEADERS) - 1))

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename_base}.pdf"},
    )


@router.get("/reports/generate")
def generate_report(
    from_date: date = Query(...),
    to_date: date = Query(...),
    request_type: Optional[str] = Query(None),
    format: ReportFormat = Query(ReportFormat.pdf),
    db: Session = Depends(get_db),
):
    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date must be before to_date")

    rows = _report_rows(db, from_date, to_date, request_type)
    filename_base = f"regularization_report_{from_date}_{to_date}"

    if format == ReportFormat.csv:
        return _csv_response(rows, filename_base)
    if format == ReportFormat.excel:
        return _excel_response(rows, filename_base)
    return _pdf_response(rows, filename_base, from_date, to_date)