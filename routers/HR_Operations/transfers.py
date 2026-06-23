# routers/HR_Operations/transfers.py
# ═══════════════════════════════════════════════════════════════════════════════
#  Transfer & Movement Management — Complete Router
#
#  Tab 1 — All Transfers          →  GET  /hr-ops/transfers
#  Tab 2 — Pending Approvals      →  GET  /hr-ops/transfers/pending-approvals
#  Tab 3 — Transfer History       →  GET  /hr-ops/transfers/history
#  Tab 4 — Organization Chart     →  GET  /hr-ops/transfers/org-chart
#  Tab 5 — Reports & Analytics    →  GET  /hr-ops/transfers/reports
#
#  Core CRUD                      →  POST / GET / PATCH / DELETE  /hr-ops/transfers/*
#  Quick actions                  →  approve, reject, complete, bulk-approve
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, select, and_, or_, distinct
from typing import List, Optional
from datetime import date

from core.database import get_db
from model.HR_Operations.transfer import Transfer
from model.onboarding.employee import Employee
from schema.HR_Operations.transfer import (
    TransferCreate, TransferUpdate, TransferResponse,
    ApprovalAction,
    OrgChartAnalytics, DepartmentFlow, LocationFlow, TopRoute,
    TransferReport, TransferTypeDistribution, DepartmentStat, StatusDistribution,
)

router = APIRouter(
    prefix="/hr-ops/transfers",
    tags=["HR Operations – Transfer & Movement Management"],
)


# ─────────────────────────────────────────────────────────────────────────────
#  INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_employee_or_404(employee_id: int, db: Session) -> Employee:
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found",
        )
    return emp


def _employee_dict(emp: Employee) -> dict:
    return {
        "id":            emp.id,
        "first_name":    emp.first_name,
        "last_name":     emp.last_name,
        "employee_code": emp.employee_code,
        "designation":   emp.designation,
        "department":    emp.department,
        "location":      emp.location,
    }


def _attach_employee(record: Transfer, db: Session):
    try:
        emp = _get_employee_or_404(record.employee_id, db)
        record.employee = _employee_dict(emp)
    except HTTPException:
        record.employee = None


def _get_transfer_or_404(transfer_id: int, db: Session) -> Transfer:
    record = db.execute(
        select(Transfer).where(Transfer.id == transfer_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Transfer record not found")
    return record


def _gen_transfer_code(db: Session) -> str:
    count = db.execute(select(func.count()).select_from(Transfer)).scalar() or 0
    return f"TRO{str(count + 1).zfill(2)}"


def _apply_search_filters(q, search: Optional[str], status_filter: Optional[str]):
    """Apply common search + status filters to a Transfer query joined with Employee."""
    if status_filter and status_filter not in ("ALL", "All"):
        q = q.where(Transfer.status == status_filter)
    if search:
        q = q.where(
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
                Employee.department.ilike(f"%{search}%"),
                Transfer.transfer_code.ilike(f"%{search}%"),
                Transfer.from_department.ilike(f"%{search}%"),
                Transfer.to_department.ilike(f"%{search}%"),
            )
        )
    return q


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 1  ·  ALL TRANSFERS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("", response_model=List[TransferResponse], summary="All Transfers tab")
def list_all_transfers(
    search:        Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    transfer_type: Optional[str] = Query(None),
    skip:          int           = Query(0,  ge=0),
    limit:         int           = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Transfer).join(Employee, Transfer.employee_id == Employee.id)
    q = _apply_search_filters(q, search, status_filter)
    if transfer_type:
        q = q.where(Transfer.transfer_type == transfer_type)
    records = db.execute(q.order_by(Transfer.created_at.desc()).offset(skip).limit(limit)).scalars().all()
    for r in records:
        _attach_employee(r, db)
    return records


# ── Create new transfer (+ NEW TRANSFER button) ───────────────────────────────
@router.post("", response_model=TransferResponse, status_code=201, summary="Create new transfer")
def create_transfer(payload: TransferCreate, db: Session = Depends(get_db)):
    _get_employee_or_404(payload.employee_id, db)
    code   = _gen_transfer_code(db)
    record = Transfer(**payload.model_dump(), transfer_code=code)
    db.add(record)
    db.commit()
    db.refresh(record)
    _attach_employee(record, db)
    return record


# ── Get single ────────────────────────────────────────────────────────────────
@router.get("/{transfer_id}", response_model=TransferResponse)
def get_transfer(transfer_id: int, db: Session = Depends(get_db)):
    record = _get_transfer_or_404(transfer_id, db)
    _attach_employee(record, db)
    return record


# ── Update ────────────────────────────────────────────────────────────────────
@router.patch("/{transfer_id}", response_model=TransferResponse)
def update_transfer(
    transfer_id: int,
    payload: TransferUpdate,
    db: Session = Depends(get_db),
):
    record = _get_transfer_or_404(transfer_id, db)
    data   = payload.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(record, field, value)

    # If Completed, update the employee's department / location / designation
    if record.status == "Completed" and not record.employee_record_updated:
        try:
            emp = _get_employee_or_404(record.employee_id, db)
            emp.department  = record.to_department
            if record.to_location:
                emp.location = record.to_location
            if record.to_designation:
                emp.designation = record.to_designation
            record.employee_record_updated = True
        except HTTPException:
            pass

    db.commit()
    db.refresh(record)
    _attach_employee(record, db)
    return record


# ── Delete ────────────────────────────────────────────────────────────────────
@router.delete("/{transfer_id}", status_code=204)
def delete_transfer(transfer_id: int, db: Session = Depends(get_db)):
    record = _get_transfer_or_404(transfer_id, db)
    db.delete(record)
    db.commit()


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 2  ·  PENDING APPROVALS
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/pending-approvals",
    response_model=List[TransferResponse],
    summary="Pending Approvals tab",
)
def list_pending_approvals(
    search: Optional[str] = Query(None),
    skip:   int           = Query(0,  ge=0),
    limit:  int           = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = (
        select(Transfer)
        .join(Employee, Transfer.employee_id == Employee.id)
        .where(Transfer.status == "Pending")
    )
    q = _apply_search_filters(q, search, None)
    records = db.execute(q.order_by(Transfer.effective_date.asc()).offset(skip).limit(limit)).scalars().all()
    for r in records:
        _attach_employee(r, db)
    return records


# ── Approve single ────────────────────────────────────────────────────────────
@router.patch(
    "/{transfer_id}/approve",
    response_model=TransferResponse,
    summary="Approve a transfer",
)
def approve_transfer(
    transfer_id: int,
    payload: ApprovalAction,
    db: Session = Depends(get_db),
):
    record = _get_transfer_or_404(transfer_id, db)
    if record.status != "Pending":
        raise HTTPException(
            status_code=400,
            detail=f"Transfer is already '{record.status}', cannot approve",
        )
    record.status      = "Approved"
    record.approved_by = payload.approved_by
    record.approved_date = date.today()
    if payload.remarks:
        record.remarks = payload.remarks
    db.commit()
    db.refresh(record)
    _attach_employee(record, db)
    return record


# ── Reject single ─────────────────────────────────────────────────────────────
@router.patch(
    "/{transfer_id}/reject",
    response_model=TransferResponse,
    summary="Reject a transfer",
)
def reject_transfer(
    transfer_id: int,
    payload: ApprovalAction,
    db: Session = Depends(get_db),
):
    record = _get_transfer_or_404(transfer_id, db)
    if record.status not in ("Pending", "Approved"):
        raise HTTPException(
            status_code=400,
            detail=f"Transfer is '{record.status}', cannot reject",
        )
    record.status      = "Rejected"
    record.approved_by = payload.approved_by
    if payload.remarks:
        record.remarks = payload.remarks
    db.commit()
    db.refresh(record)
    _attach_employee(record, db)
    return record


# ── Mark as Completed ─────────────────────────────────────────────────────────
@router.patch(
    "/{transfer_id}/complete",
    response_model=TransferResponse,
    summary="Mark transfer as Completed and update employee record",
)
def complete_transfer(transfer_id: int, db: Session = Depends(get_db)):
    record = _get_transfer_or_404(transfer_id, db)
    if record.status != "Approved":
        raise HTTPException(
            status_code=400,
            detail="Only Approved transfers can be marked Completed",
        )
    record.status = "Completed"
    # Update employee record
    try:
        emp = _get_employee_or_404(record.employee_id, db)
        emp.department  = record.to_department
        if record.to_location:
            emp.location    = record.to_location
        if record.to_designation:
            emp.designation = record.to_designation
        record.employee_record_updated = True
    except HTTPException:
        pass
    db.commit()
    db.refresh(record)
    _attach_employee(record, db)
    return record


# ── Bulk approve ──────────────────────────────────────────────────────────────
@router.post("/bulk-approve", summary="Bulk approve pending transfers")
def bulk_approve(
    transfer_ids: List[int],
    approved_by:  Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    records = db.execute(
        select(Transfer)
        .where(and_(Transfer.id.in_(transfer_ids), Transfer.status == "Pending"))
    ).scalars().all()
    updated = 0
    for r in records:
        r.status       = "Approved"
        r.approved_by  = approved_by
        r.approved_date = date.today()
        updated += 1
    db.commit()
    return {"approved": updated, "skipped": len(transfer_ids) - updated}


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 3  ·  TRANSFER HISTORY  (all statuses, most recent first)
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/history",
    response_model=List[TransferResponse],
    summary="Transfer History tab",
)
def transfer_history(
    search:        Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    transfer_type: Optional[str] = Query(None),
    from_date:     Optional[date] = Query(None),
    to_date:       Optional[date] = Query(None),
    skip:          int            = Query(0,  ge=0),
    limit:         int            = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Transfer).join(Employee, Transfer.employee_id == Employee.id)
    q = _apply_search_filters(q, search, status_filter)
    if transfer_type:
        q = q.where(Transfer.transfer_type == transfer_type)
    if from_date:
        q = q.where(Transfer.effective_date >= from_date)
    if to_date:
        q = q.where(Transfer.effective_date <= to_date)
    records = db.execute(
        q.order_by(Transfer.effective_date.desc()).offset(skip).limit(limit)
    ).scalars().all()
    for r in records:
        _attach_employee(r, db)
    return records


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 4  ·  ORGANIZATION CHART — Transfer Analytics
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/org-chart",
    response_model=OrgChartAnalytics,
    summary="Organization Transfer Analytics (Org Chart tab)",
)
def org_chart_analytics(db: Session = Depends(get_db)):
    # ── Department flow ───────────────────────────────────────────────────────
    all_depts = set()
    dept_in:  dict[str, int] = {}
    dept_out: dict[str, int] = {}

    transfers = db.execute(select(Transfer)).scalars().all()
    for t in transfers:
        all_depts.add(t.from_department)
        all_depts.add(t.to_department)
        dept_out[t.from_department] = dept_out.get(t.from_department, 0) + 1
        dept_in[t.to_department]    = dept_in.get(t.to_department, 0) + 1

    department_flows = [
        DepartmentFlow(
            department=d,
            transfers_in=dept_in.get(d, 0),
            transfers_out=dept_out.get(d, 0),
            net_change=dept_in.get(d, 0) - dept_out.get(d, 0),
        )
        for d in sorted(all_depts)
    ]

    # ── Location flow ─────────────────────────────────────────────────────────
    all_locs  = set()
    loc_in:   dict[str, int] = {}
    loc_out:  dict[str, int] = {}

    for t in transfers:
        if t.from_location:
            all_locs.add(t.from_location)
            loc_out[t.from_location] = loc_out.get(t.from_location, 0) + 1
        if t.to_location:
            all_locs.add(t.to_location)
            loc_in[t.to_location] = loc_in.get(t.to_location, 0) + 1

    location_flows = [
        LocationFlow(
            location=l,
            transfers_in=loc_in.get(l, 0),
            transfers_out=loc_out.get(l, 0),
            net_change=loc_in.get(l, 0) - loc_out.get(l, 0),
        )
        for l in sorted(all_locs)
    ]

    # ── Top transfer routes ───────────────────────────────────────────────────
    route_counts: dict[tuple, int] = {}
    for t in transfers:
        key = (t.from_department, t.from_location, t.to_department, t.to_location)
        route_counts[key] = route_counts.get(key, 0) + 1

    top_routes = [
        TopRoute(
            from_department=k[0],
            from_location=k[1],
            to_department=k[2],
            to_location=k[3],
            transfer_count=v,
            status="Active",
        )
        for k, v in sorted(route_counts.items(), key=lambda x: -x[1])[:10]
    ]

    return OrgChartAnalytics(
        department_flows=department_flows,
        location_flows=location_flows,
        top_routes=top_routes,
    )


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 5  ·  REPORTS & ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/reports",
    response_model=TransferReport,
    summary="Reports & Analytics tab",
)
def transfer_reports(db: Session = Depends(get_db)):
    transfers = db.execute(select(Transfer)).scalars().all()
    total     = len(transfers)

    # Approval rate  (Approved + Completed / total)
    approved_count = sum(1 for t in transfers if t.status in ("Approved", "Completed"))
    approval_rate  = round((approved_count / total * 100) if total > 0 else 0.0, 1)

    # Departments and locations involved
    depts = set(t.from_department for t in transfers) | set(t.to_department for t in transfers)
    locs  = (
        set(t.from_location for t in transfers if t.from_location)
        | set(t.to_location for t in transfers if t.to_location)
    )

    # Transfer type distribution
    type_counts: dict[str, int] = {}
    for t in transfers:
        type_counts[t.transfer_type] = type_counts.get(t.transfer_type, 0) + 1

    type_distribution = [
        TransferTypeDistribution(
            transfer_type=tt,
            count=cnt,
            percentage=round((cnt / total * 100) if total > 0 else 0.0, 1),
        )
        for tt, cnt in sorted(type_counts.items(), key=lambda x: -x[1])
    ]

    # Department transfer statistics (in/out/net)
    all_depts = set(t.from_department for t in transfers) | set(t.to_department for t in transfers)
    dept_in:  dict[str, int] = {}
    dept_out: dict[str, int] = {}
    for t in transfers:
        dept_out[t.from_department] = dept_out.get(t.from_department, 0) + 1
        dept_in[t.to_department]    = dept_in.get(t.to_department, 0) + 1

    department_stats = [
        DepartmentStat(
            department=d,
            transfers_in=dept_in.get(d, 0),
            transfers_out=dept_out.get(d, 0),
            net_change=dept_in.get(d, 0) - dept_out.get(d, 0),
        )
        for d in sorted(all_depts)
    ]

    # Status distribution  (Pending | Approved | Rejected | Completed)
    status_counts: dict[str, int] = {}
    for t in transfers:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1

    status_distribution = [
        StatusDistribution(status=s, count=c)
        for s, c in sorted(status_counts.items(), key=lambda x: -x[1])
    ]

    return TransferReport(
        total_transfers=total,
        approval_rate_pct=approval_rate,
        departments_involved=len(depts),
        locations_involved=len(locs),
        type_distribution=type_distribution,
        department_stats=department_stats,
        status_distribution=status_distribution,
    )


# ── Export CSV-ready JSON ─────────────────────────────────────────────────────
@router.get("/reports/export", summary="Export transfers as CSV-ready JSON")
def export_transfers(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    q = select(Transfer)
    if status_filter:
        q = q.where(Transfer.status == status_filter)
    records = db.execute(q.order_by(Transfer.effective_date.desc())).scalars().all()
    rows = []
    for r in records:
        try:
            emp = _get_employee_or_404(r.employee_id, db)
            emp_name = f"{emp.first_name} {emp.last_name or ''}".strip()
            emp_code = emp.employee_code or ""
        except HTTPException:
            emp_name, emp_code = "", ""
        rows.append({
            "transfer_code":    r.transfer_code,
            "employee_code":    emp_code,
            "employee_name":    emp_name,
            "from_department":  r.from_department,
            "to_department":    r.to_department,
            "from_location":    r.from_location,
            "to_location":      r.to_location,
            "transfer_type":    r.transfer_type,
            "effective_date":   str(r.effective_date),
            "status":           r.status,
        })
    return {"total": len(rows), "records": rows}
