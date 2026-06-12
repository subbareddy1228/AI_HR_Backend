import csv
import io
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Body
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from model.HR_Operations.transfer import Transfer
from schema.HR_Operations.transfer import (
    TransferCreate,
    TransferUpdate,
    TransferResponse,
    TransferApprovePayload,
    TransferRejectPayload,
    BulkUploadResult,
    AnalyticsResponse,
    TransferStatsSummary,
    TypeDistribution,
    DepartmentStats,
    StatusDistribution,
    OrgChartAnalyticsResponse,
    DepartmentFlow,
    LocationFlow,
    TopRoute,
)

router = APIRouter(prefix="/transfers", tags=["Transfers & Movement"])




def _next_transfer_id(db: Session) -> str:
    
    count = db.query(func.count(Transfer.id)).scalar() or 0
    return f"TR{str(count + 1).zfill(3)}"


def _get_or_404(record_id: int, db: Session) -> Transfer:
    record = db.query(Transfer).filter(Transfer.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Transfer #{record_id} not found.")
    return record


def _avg_processing_days(records: list) -> float:
    
    deltas = [
        (r.updated_at - r.created_at).days
        for r in records
        if r.status in ("APPROVED", "COMPLETED") and r.updated_at and r.created_at
    ]
    return round(sum(deltas) / len(deltas), 1) if deltas else 0.0






@router.get(
    "/pending",
    response_model=List[TransferResponse],
    summary="[Tab] Pending Approvals – transfers awaiting action",
)
def list_pending_approvals(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Transfer).filter(Transfer.status == "PENDING")
    if search:
        like = f"%{search}%"
        q = q.filter(
            Transfer.transfer_id.ilike(like)
            | Transfer.from_department.ilike(like)
            | Transfer.to_department.ilike(like)
            | Transfer.from_location.ilike(like)
            | Transfer.to_location.ilike(like)
        )
    return q.order_by(Transfer.created_at.asc()).all()



@router.get(
    "/history",
    response_model=List[TransferResponse],
    summary="[Tab] Transfer History – completed / approved / rejected",
)
def transfer_history(
    status: Optional[str] = Query(
        None,
        description="Filter by status: APPROVED | REJECTED | COMPLETED",
    ),
    employee_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Transfer).filter(Transfer.status != "PENDING")

    if status:
        q = q.filter(Transfer.status == status.upper())
    if employee_id:
        q = q.filter(Transfer.employee_id == employee_id)
    if search:
        like = f"%{search}%"
        q = q.filter(
            Transfer.transfer_id.ilike(like)
            | Transfer.from_department.ilike(like)
            | Transfer.to_department.ilike(like)
        )

    return q.order_by(Transfer.updated_at.desc()).offset(skip).limit(limit).all()




@router.get(
    "/analytics/summary",
    response_model=AnalyticsResponse,
    summary="[Tab] Reports & Analytics – stat cards + distributions",
)
def analytics_summary(db: Session = Depends(get_db)):
    
    records = db.query(Transfer).all()
    total   = len(records)

    
    status_counts: dict = {"PENDING": 0, "APPROVED": 0, "REJECTED": 0, "COMPLETED": 0}
    for r in records:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    approved_total = status_counts["APPROVED"] + status_counts["COMPLETED"]
    approval_rate  = round(approved_total / total * 100, 1) if total else 0.0

    summary = TransferStatsSummary(
        total=total,
        pending=status_counts["PENDING"],
        approved=status_counts["APPROVED"],
        rejected=status_counts["REJECTED"],
        completed=status_counts["COMPLETED"],
        approval_rate_pct=approval_rate,
        avg_processing_days=_avg_processing_days(records),
    )

    
    type_counts: dict = {}
    for r in records:
        type_counts[r.transfer_type] = type_counts.get(r.transfer_type, 0) + 1

    type_distribution = [
        TypeDistribution(
            transfer_type=t,
            count=c,
            percentage=round(c / total * 100, 1) if total else 0.0,
        )
        for t, c in sorted(type_counts.items())
    ]

    
    dept_in:  dict = {}
    dept_out: dict = {}
    for r in records:
        dept_in[r.to_department]   = dept_in.get(r.to_department, 0)   + 1
        dept_out[r.from_department]= dept_out.get(r.from_department, 0)+ 1

    all_depts = sorted(set(dept_in) | set(dept_out))
    department_stats = [
        DepartmentStats(
            department=d,
            transfers_in=dept_in.get(d, 0),
            transfers_out=dept_out.get(d, 0),
            net_change=dept_in.get(d, 0) - dept_out.get(d, 0),
        )
        for d in all_depts
    ]

    
    status_distribution = [
        StatusDistribution(status=s, count=c)
        for s, c in status_counts.items()
    ]

    
    locations = {r.from_location for r in records if r.from_location} | \
                {r.to_location   for r in records if r.to_location}

    return AnalyticsResponse(
        summary=summary,
        type_distribution=type_distribution,
        department_stats=department_stats,
        status_distribution=status_distribution,
        departments_involved=len(all_depts),
        locations_involved=len(locations),
    )


@router.get(
    "/analytics/export",
    summary="[Quick Action] Generate Reports – download all transfers as CSV",
)
def export_csv(db: Session = Depends(get_db)):
    
    records = db.query(Transfer).order_by(Transfer.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Transfer ID", "Employee ID", "From Department", "To Department",
        "From Location", "To Location", "Type", "Effective Date",
        "Status", "Approved By", "Reason", "Remarks", "Created At", "Updated At",
    ])
    for r in records:
        writer.writerow([
            r.transfer_id,
            r.employee_id,
            r.from_department,
            r.to_department,
            r.from_location  or "",
            r.to_location    or "",
            r.transfer_type,
            str(r.effective_date),
            r.status,
            r.approved_by    or "",
            r.reason         or "",
            r.remarks        or "",
            r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transfers_export.csv"},
    )



@router.get(
    "/analytics/org-chart",
    response_model=OrgChartAnalyticsResponse,
    summary="[Tab] Organisation Chart – department & location transfer flows",
)
def org_chart_analytics(db: Session = Depends(get_db)):
    
    records = db.query(Transfer).all()

    dept_flows: dict = {}
    loc_flows:  dict = {}

    for r in records:
        dk = (r.from_department, r.to_department)
        dept_flows[dk] = dept_flows.get(dk, 0) + 1

        if r.from_location and r.to_location:
            lk = (r.from_location, r.to_location)
            loc_flows[lk] = loc_flows.get(lk, 0) + 1

    department_transfer_flow = [
        DepartmentFlow(from_department=f, to_department=t, count=c)
        for (f, t), c in sorted(dept_flows.items(), key=lambda x: -x[1])
    ]

    location_transfer_flow = [
        LocationFlow(from_location=f, to_location=t, count=c)
        for (f, t), c in sorted(loc_flows.items(), key=lambda x: -x[1])
    ]

    
    top_routes = []
    seen = set()
    for r in sorted(records, key=lambda x: x.id):
        key = (r.from_department, r.to_department, r.from_location, r.to_location)
        if key not in seen:
            seen.add(key)
            top_routes.append(
                TopRoute(
                    from_dept=r.from_department,
                    to_dept=r.to_department,
                    from_location=r.from_location,
                    to_location=r.to_location,
                    count=dept_flows.get((r.from_department, r.to_department), 0),
                    status=r.status,
                )
            )

    return OrgChartAnalyticsResponse(
        department_transfer_flow=department_transfer_flow,
        location_transfer_flow=location_transfer_flow,
        top_transfer_routes=top_routes[:10],
    )




@router.post(
    "/bulk-upload",
    response_model=BulkUploadResult,
    summary="[Quick Action] Bulk Upload (CSV) – create multiple transfers at once",
)
async def bulk_upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader   = csv.DictReader(io.StringIO(text))
    created: List[str] = []
    errors:  List[dict] = []

    for idx, row in enumerate(reader, start=2):   # row 1 is the header
        try:
            from datetime import date as _date
            record = Transfer(
                transfer_id     = _next_transfer_id(db),
                employee_id     = int(row["employee_id"].strip()),
                from_department = row["from_department"].strip(),
                to_department   = row["to_department"].strip(),
                from_location   = row.get("from_location", "").strip() or None,
                to_location     = row.get("to_location",   "").strip() or None,
                transfer_type   = row["transfer_type"].strip().upper().replace(" ", "_"),
                effective_date  = _date.fromisoformat(row["effective_date"].strip()),
                reason          = row.get("reason", "").strip() or None,
                status          = "PENDING",
            )
            db.add(record)
            db.flush()   # assign DB id so _next_transfer_id increments correctly
            created.append(record.transfer_id)
        except Exception as exc:
            db.rollback()
            errors.append({"row": idx, "error": str(exc), "data": dict(row)})

    if created:
        db.commit()

    return BulkUploadResult(
        created_count=len(created),
        error_count=len(errors),
        created_ids=created,
        errors=errors,
    )



@router.get(
    "/",
    response_model=List[TransferResponse],
    summary="[Tab] All Transfers – list with search & filters",
)
def list_all_transfers(
    search: Optional[str] = Query(
        None,
        description="Free-text search: Transfer ID, department, or location",
    ),
    transfer_type: Optional[str] = Query(
        None,
        description="INTERNAL_TRANSFER | LOCATION_TRANSFER | PROMOTION_TRANSFER | DEPARTMENT_TRANSFER",
    ),
    status: Optional[str] = Query(
        None,
        description="PENDING | APPROVED | REJECTED | COMPLETED",
    ),
    employee_id: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="ISO date, e.g. 2024-01-01"),
    to_date:   Optional[str] = Query(None, description="ISO date, e.g. 2024-12-31"),
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    from datetime import date as _date

    q = db.query(Transfer)

    if search:
        like = f"%{search}%"
        q = q.filter(
            Transfer.transfer_id.ilike(like)
            | Transfer.from_department.ilike(like)
            | Transfer.to_department.ilike(like)
            | Transfer.from_location.ilike(like)
            | Transfer.to_location.ilike(like)
        )
    if transfer_type:
        q = q.filter(Transfer.transfer_type == transfer_type.upper().replace(" ", "_"))
    if status:
        q = q.filter(Transfer.status == status.upper())
    if employee_id:
        q = q.filter(Transfer.employee_id == employee_id)
    if from_date:
        q = q.filter(Transfer.effective_date >= _date.fromisoformat(from_date))
    if to_date:
        q = q.filter(Transfer.effective_date <= _date.fromisoformat(to_date))

    return q.order_by(Transfer.created_at.desc()).offset(skip).limit(limit).all()


@router.post(
    "/",
    response_model=TransferResponse,
    status_code=201,
    summary="[Quick Action] New Transfer Request",
)
def create_transfer(payload: TransferCreate, db: Session = Depends(get_db)):
   
    record = Transfer(
        **payload.model_dump(),
        transfer_id=_next_transfer_id(db),
        status="PENDING",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record




@router.get(
    "/{record_id}",
    response_model=TransferResponse,
    summary="Get a single transfer by DB id (eye icon)",
)
def get_transfer(record_id: int, db: Session = Depends(get_db)):
    return _get_or_404(record_id, db)


@router.patch(
    "/{record_id}",
    response_model=TransferResponse,
    summary="Update transfer fields (pencil icon)",
)
def update_transfer(
    record_id: int,
    payload: TransferUpdate,
    db: Session = Depends(get_db),
):
    record = _get_or_404(record_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.delete(
    "/{record_id}",
    summary="Delete a transfer record",
)
def delete_transfer(record_id: int, db: Session = Depends(get_db)):
    record = _get_or_404(record_id, db)
    db.delete(record)
    db.commit()
    return {"message": f"Transfer {record.transfer_id or record.id} deleted successfully."}



@router.post(
    "/{record_id}/approve",
    response_model=TransferResponse,
    summary="Approve a PENDING transfer (green tick button)",
)
def approve_transfer(
    record_id: int,
    payload: TransferApprovePayload,
    db: Session = Depends(get_db),
):
    record = _get_or_404(record_id, db)
    if record.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Transfer is '{record.status}'. Only PENDING transfers can be approved.",
        )
    record.status      = "APPROVED"
    record.approved_by = payload.approved_by
    record.remarks     = payload.remarks
    record.updated_at  = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.post(
    "/{record_id}/reject",
    response_model=TransferResponse,
    summary="Reject a PENDING transfer (red X button)",
)
def reject_transfer(
    record_id: int,
    payload: TransferRejectPayload,
    db: Session = Depends(get_db),
):
    record = _get_or_404(record_id, db)
    if record.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Transfer is '{record.status}'. Only PENDING transfers can be rejected.",
        )
    record.status      = "REJECTED"
    record.approved_by = payload.reviewed_by
    record.remarks     = payload.remarks
    record.updated_at  = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.post(
    "/{record_id}/complete",
    response_model=TransferResponse,
    summary="Mark an APPROVED transfer as COMPLETED",
)
def complete_transfer(record_id: int, db: Session = Depends(get_db)):
    
    record = _get_or_404(record_id, db)
    if record.status != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail=f"Transfer is '{record.status}'. Only APPROVED transfers can be completed.",
        )
    record.status     = "COMPLETED"
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record
