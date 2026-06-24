# routers/HR_Operations/exit_management.py
# ═══════════════════════════════════════════════════════════════════════════════
#  Exit Management & Clearance — Complete Router
#
#  Tab 1 — Exit Cases       →  /hr-ops/exit                    (CRUD + clearance)
#  Tab 2 — Alumni           →  /hr-ops/exit/alumni/*
#  Tab 3 — Settlements      →  /hr-ops/exit/settlements/*
#  Tab 4 — Employee Exits   →  /hr-ops/exit/employee-exits
#  Tab 5 — Trends           →  /hr-ops/exit/trends
#
#  Shared
#    Dashboard stat cards   →  GET /hr-ops/exit/dashboard
#    Filter options         →  GET /hr-ops/exit/filter-options
#    Export                 →  GET /hr-ops/exit/export
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, select, and_, or_
from typing import List, Optional
from datetime import date, timedelta
from decimal import Decimal

from core.database import get_db
from model.HR_Operations.exit_management import ExitManagement, Alumni, Settlement
from model.onboarding.employee import Employee
from schema.HR_Operations.exit_management import (
    ExitManagementCreate, ExitManagementUpdate, ExitManagementResponse,
    ExitDashboard,
    AlumniCreate, AlumniUpdate, AlumniResponse,
    SettlementCreate, SettlementUpdate, SettlementResponse,
    EmployeeExitRecord,
    ExitTrendResponse,
    ExitFilterOptions,
)

router = APIRouter(
    prefix="/hr-ops/exit",
    tags=["HR Operations – Exit Management & Clearance"],
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


def _get_exit_or_404(exit_id: int, db: Session) -> ExitManagement:
    record = db.execute(
        select(ExitManagement).where(ExitManagement.id == exit_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Exit record not found")
    return record


def _enrich_exit(record: ExitManagement, db: Session):
    """Attach employee + compute days_left + auto-recalc clearance_progress."""
    today = date.today()
    if record.last_working_date:
        record.days_left = (record.last_working_date - today).days
    else:
        record.days_left = None

    # Recompute clearance_progress from checklist flags
    flags = [
        record.it_clearance, record.finance_clearance, record.hr_clearance,
        record.admin_clearance, record.assets_returned,
        record.exit_interview_done, record.knowledge_transfer,
    ]
    done  = sum(1 for f in flags if f)
    total = len(flags)
    record.clearance_progress = round(done / total * 100) if total > 0 else 0
    record.pending_items      = total - done

    try:
        emp = _get_employee_or_404(record.employee_id, db)
        record.employee = _employee_dict(emp)
    except HTTPException:
        record.employee = None


def _gen_alumni_code(db: Session) -> str:
    count = db.execute(select(func.count()).select_from(Alumni)).scalar() or 0
    return f"ALM{str(count + 1).zfill(3)}"


# ═════════════════════════════════════════════════════════════════════════════
#  DASHBOARD  —  stat cards (shared across all tabs)
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=ExitDashboard, summary="Dashboard stat cards")
def exit_dashboard(db: Session = Depends(get_db)):
    total_cases = db.execute(
        select(func.count()).select_from(ExitManagement)
    ).scalar() or 0

    pending = db.execute(
        select(func.count()).select_from(ExitManagement)
        .where(ExitManagement.status.in_(["Pending", "In Progress"]))
    ).scalar() or 0

    escalated = db.execute(
        select(func.count()).select_from(ExitManagement)
        .where(ExitManagement.status == "Escalated")
    ).scalar() or 0

    alumni_count = db.execute(
        select(func.count()).select_from(Alumni)
    ).scalar() or 0

    return ExitDashboard(
        total_cases=total_cases,
        pending=pending,
        escalated=escalated,
        alumni=alumni_count,
    )


# ═════════════════════════════════════════════════════════════════════════════
#  FILTER OPTIONS  —  dropdowns
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/filter-options", response_model=ExitFilterOptions)
def filter_options(db: Session = Depends(get_db)):
    locations = db.execute(
        select(Employee.location).distinct().where(Employee.location.isnot(None))
    ).scalars().all()
    departments = db.execute(
        select(Employee.department).distinct().where(Employee.department.isnot(None))
    ).scalars().all()
    return ExitFilterOptions(
        locations=["All Locations"] + sorted(locations),
        departments=["All Departments"] + sorted(departments),
        exit_reasons=["All Reasons", "Resignation", "Termination", "Retirement",
                      "Better Opportunity", "Absconding"],
        statuses=["All Status", "In Progress", "Pending", "Completed",
                  "Escalated", "Cancelled"],
    )


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 1  ·  EXIT CASES  —  CRUD
# ═════════════════════════════════════════════════════════════════════════════

@router.get("", response_model=List[ExitManagementResponse], summary="Exit Cases tab")
def list_exit_cases(
    search:     Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    skip:       int           = Query(0,  ge=0),
    limit:      int           = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(ExitManagement).join(Employee, ExitManagement.employee_id == Employee.id)
    if status and status != "All Status":
        q = q.where(ExitManagement.status == status)
    if department and department != "All Departments":
        q = q.where(Employee.department == department)
    if search:
        q = q.where(
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
            )
        )
    records = db.execute(
        q.order_by(ExitManagement.last_working_date.asc()).offset(skip).limit(limit)
    ).scalars().all()
    for r in records:
        _enrich_exit(r, db)
    return records


@router.post("", response_model=ExitManagementResponse, status_code=201,
             summary="New Exit (+ New Exit button)")
def create_exit(payload: ExitManagementCreate, db: Session = Depends(get_db)):
    _get_employee_or_404(payload.employee_id, db)
    existing = db.execute(
        select(ExitManagement)
        .where(and_(
            ExitManagement.employee_id == payload.employee_id,
            ExitManagement.status.notin_(["Completed", "Cancelled"]),
        ))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Active exit record already exists for this employee")
    record = ExitManagement(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    _enrich_exit(record, db)
    return record


@router.get("/{exit_id}", response_model=ExitManagementResponse)
def get_exit(exit_id: int, db: Session = Depends(get_db)):
    record = _get_exit_or_404(exit_id, db)
    _enrich_exit(record, db)
    return record


@router.patch("/{exit_id}", response_model=ExitManagementResponse)
def update_exit(exit_id: int, payload: ExitManagementUpdate, db: Session = Depends(get_db)):
    record = _get_exit_or_404(exit_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)

    # Auto-complete if all clearance steps done
    flags = [
        record.it_clearance, record.finance_clearance, record.hr_clearance,
        record.admin_clearance, record.assets_returned,
        record.exit_interview_done, record.knowledge_transfer,
    ]
    if all(flags) and record.status == "In Progress":
        record.status = "Completed"

    db.commit()
    db.refresh(record)
    _enrich_exit(record, db)
    return record


@router.delete("/{exit_id}", status_code=204)
def delete_exit(exit_id: int, db: Session = Depends(get_db)):
    record = _get_exit_or_404(exit_id, db)
    db.delete(record)
    db.commit()


# ── Clearance checklist update (single endpoint for all 7 flags) ──────────────
@router.patch("/{exit_id}/clearance", response_model=ExitManagementResponse,
              summary="Update clearance checklist items")
def update_clearance(
    exit_id:             int,
    it_clearance:        Optional[bool] = None,
    finance_clearance:   Optional[bool] = None,
    hr_clearance:        Optional[bool] = None,
    admin_clearance:     Optional[bool] = None,
    assets_returned:     Optional[bool] = None,
    exit_interview_done: Optional[bool] = None,
    knowledge_transfer:  Optional[bool] = None,
    db: Session = Depends(get_db),
):
    record = _get_exit_or_404(exit_id, db)
    if it_clearance        is not None: record.it_clearance        = it_clearance
    if finance_clearance   is not None: record.finance_clearance   = finance_clearance
    if hr_clearance        is not None: record.hr_clearance        = hr_clearance
    if admin_clearance     is not None: record.admin_clearance     = admin_clearance
    if assets_returned     is not None: record.assets_returned     = assets_returned
    if exit_interview_done is not None: record.exit_interview_done = exit_interview_done
    if knowledge_transfer  is not None: record.knowledge_transfer  = knowledge_transfer

    flags = [
        record.it_clearance, record.finance_clearance, record.hr_clearance,
        record.admin_clearance, record.assets_returned,
        record.exit_interview_done, record.knowledge_transfer,
    ]
    if all(flags) and record.status == "In Progress":
        record.status = "Completed"

    db.commit()
    db.refresh(record)
    _enrich_exit(record, db)
    return record


# ── Export (Export button top-right) ─────────────────────────────────────────
@router.get("/export", summary="Export exit cases as JSON")
def export_exits(
    status:     Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = select(ExitManagement).join(Employee, ExitManagement.employee_id == Employee.id)
    if status:
        q = q.where(ExitManagement.status == status)
    if department:
        q = q.where(Employee.department == department)
    records = db.execute(q.order_by(ExitManagement.last_working_date.desc())).scalars().all()
    rows = []
    for r in records:
        try:
            emp = _get_employee_or_404(r.employee_id, db)
            emp_name = f"{emp.first_name} {emp.last_name or ''}".strip()
            emp_code = emp.employee_code or ""
            dept     = emp.department or ""
        except HTTPException:
            emp_name, emp_code, dept = "", "", ""
        rows.append({
            "employee_code":      emp_code,
            "employee_name":      emp_name,
            "department":         dept,
            "exit_type":          r.exit_type,
            "resignation_date":   str(r.resignation_date),
            "last_working_date":  str(r.last_working_date) if r.last_working_date else "",
            "status":             r.status,
            "clearance_progress": r.clearance_progress,
        })
    return {"total": len(rows), "records": rows}


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 2  ·  ALUMNI
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/alumni", response_model=List[AlumniResponse], summary="Alumni tab")
def list_alumni(
    search:     Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status:     Optional[str] = Query(None),    # maps to engagement here
    skip:       int           = Query(0,  ge=0),
    limit:      int           = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Alumni).join(Employee, Alumni.employee_id == Employee.id)
    if department and department != "All Departments":
        q = q.where(Employee.department == department)
    if status and status != "All Status":
        q = q.where(Alumni.engagement == status)
    if search:
        q = q.where(
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
                Alumni.alumni_code.ilike(f"%{search}%"),
            )
        )
    records = db.execute(q.offset(skip).limit(limit)).scalars().all()
    for r in records:
        try:
            emp = _get_employee_or_404(r.employee_id, db)
            r.employee = _employee_dict(emp)
        except HTTPException:
            r.employee = None
    return records


@router.post("/alumni", response_model=AlumniResponse, status_code=201)
def create_alumni(payload: AlumniCreate, db: Session = Depends(get_db)):
    _get_exit_or_404(payload.exit_id, db)
    _get_employee_or_404(payload.employee_id, db)
    existing = db.execute(
        select(Alumni).where(Alumni.employee_id == payload.employee_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Alumni record already exists for this employee")
    code   = _gen_alumni_code(db)
    record = Alumni(**payload.model_dump(), alumni_code=code)
    db.add(record)
    db.commit()
    db.refresh(record)
    record.employee = None
    return record


@router.get("/alumni/{alumni_id}", response_model=AlumniResponse)
def get_alumni(alumni_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(Alumni).where(Alumni.id == alumni_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Alumni record not found")
    try:
        emp = _get_employee_or_404(record.employee_id, db)
        record.employee = _employee_dict(emp)
    except HTTPException:
        record.employee = None
    return record


@router.patch("/alumni/{alumni_id}", response_model=AlumniResponse)
def update_alumni(alumni_id: int, payload: AlumniUpdate, db: Session = Depends(get_db)):
    record = db.execute(
        select(Alumni).where(Alumni.id == alumni_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Alumni record not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    record.employee = None
    return record


@router.delete("/alumni/{alumni_id}", status_code=204)
def delete_alumni(alumni_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(Alumni).where(Alumni.id == alumni_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Alumni record not found")
    db.delete(record)
    db.commit()


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 3  ·  SETTLEMENTS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/settlements", response_model=List[SettlementResponse], summary="Settlements tab")
def list_settlements(
    search:     Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    skip:       int           = Query(0,  ge=0),
    limit:      int           = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Settlement).join(Employee, Settlement.employee_id == Employee.id)
    if status and status != "All Status":
        q = q.where(Settlement.status == status)
    if department and department != "All Departments":
        q = q.where(Employee.department == department)
    if search:
        q = q.where(
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
            )
        )
    records = db.execute(q.order_by(Settlement.settlement_date.desc()).offset(skip).limit(limit)).scalars().all()
    for r in records:
        try:
            emp = _get_employee_or_404(r.employee_id, db)
            r.employee = _employee_dict(emp)
        except HTTPException:
            r.employee = None
    return records


@router.post("/settlements", response_model=SettlementResponse, status_code=201)
def create_settlement(payload: SettlementCreate, db: Session = Depends(get_db)):
    _get_exit_or_404(payload.exit_id, db)
    _get_employee_or_404(payload.employee_id, db)
    record = Settlement(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    record.employee = None
    return record


@router.get("/settlements/{settlement_id}", response_model=SettlementResponse)
def get_settlement(settlement_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(Settlement).where(Settlement.id == settlement_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Settlement record not found")
    try:
        emp = _get_employee_or_404(record.employee_id, db)
        record.employee = _employee_dict(emp)
    except HTTPException:
        record.employee = None
    return record


@router.patch("/settlements/{settlement_id}", response_model=SettlementResponse)
def update_settlement(
    settlement_id: int,
    payload: SettlementUpdate,
    db: Session = Depends(get_db),
):
    record = db.execute(
        select(Settlement).where(Settlement.id == settlement_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Settlement record not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    record.employee = None
    return record


@router.delete("/settlements/{settlement_id}", status_code=204)
def delete_settlement(settlement_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(Settlement).where(Settlement.id == settlement_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Settlement record not found")
    db.delete(record)
    db.commit()


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 4  ·  EMPLOYEE EXITS  (filtered report with Download Excel/PDF)
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/employee-exits",
    response_model=List[EmployeeExitRecord],
    summary="Employee Exits tab — filterable exit history",
)
def employee_exits(
    location:   Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    exit_reason: Optional[str] = Query(None),
    from_date:  Optional[date] = Query(None),
    to_date:    Optional[date] = Query(None),
    skip:       int            = Query(0,  ge=0),
    limit:      int            = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = (
        select(ExitManagement)
        .join(Employee, ExitManagement.employee_id == Employee.id)
        .where(ExitManagement.status != "Cancelled")
    )
    if location and location != "All Locations":
        q = q.where(Employee.location == location)
    if department and department != "All Departments":
        q = q.where(Employee.department == department)
    if exit_reason and exit_reason != "All Reasons":
        q = q.where(ExitManagement.exit_type == exit_reason)
    if from_date:
        q = q.where(ExitManagement.last_working_date >= from_date)
    if to_date:
        q = q.where(ExitManagement.last_working_date <= to_date)

    records = db.execute(
        q.order_by(ExitManagement.last_working_date.desc()).offset(skip).limit(limit)
    ).scalars().all()

    result = []
    for idx, r in enumerate(records, start=1 + skip):
        try:
            emp = _get_employee_or_404(r.employee_id, db)
            emp_info = _employee_dict(emp)
            joining  = emp.joining_date
        except HTTPException:
            emp_info = None
            joining  = None
        result.append(EmployeeExitRecord(
            sn=idx,
            employee_id=r.employee_id,
            employee=emp_info,
            location=emp_info["location"] if emp_info else None,
            department=emp_info["department"] if emp_info else None,
            designation=emp_info["designation"] if emp_info else None,
            joining_date=joining,
            exit_date=r.last_working_date,
            exit_reason=r.exit_type,
        ))
    return result


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 5  ·  TRENDS  (Exit Trend Analysis modal)
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/trends",
    response_model=ExitTrendResponse,
    summary="Exit Trend Analysis modal",
)
def exit_trends(
    period:     str           = Query("Last 3 Months",
                                      description="Last 3 Months | Last 6 Months | Last 1 Year"),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    today     = date.today()
    period_map = {
        "Last 3 Months": 90,
        "Last 6 Months": 180,
        "Last 1 Year":   365,
    }
    days      = period_map.get(period, 90)
    from_date = today - timedelta(days=days)

    q = (
        select(ExitManagement)
        .join(Employee, ExitManagement.employee_id == Employee.id)
        .where(
            and_(
                ExitManagement.last_working_date >= from_date,
                ExitManagement.last_working_date <= today,
                ExitManagement.status != "Cancelled",
            )
        )
    )
    if department and department != "All Departments":
        q = q.where(Employee.department == department)

    records = db.execute(q).scalars().all()
    total   = len(records)

    # Total employees for exit rate denominator
    total_employees = db.execute(
        select(func.count()).select_from(Employee)
    ).scalar() or 1
    exit_rate = round((total / total_employees * 100), 1)

    # Average tenure
    tenures = []
    for r in records:
        try:
            emp = _get_employee_or_404(r.employee_id, db)
            if emp.joining_date and r.last_working_date:
                tenures.append((r.last_working_date - emp.joining_date).days / 365)
        except HTTPException:
            pass
    avg_tenure = round(sum(tenures) / len(tenures), 1) if tenures else 0.0

    # Exit reason breakdown
    by_reason: dict = {}
    for r in records:
        by_reason[r.exit_type] = by_reason.get(r.exit_type, 0) + 1

    top_reason = max(by_reason, key=by_reason.get) if by_reason else "N/A"

    # Department breakdown
    by_dept: dict = {}
    for r in records:
        try:
            emp = _get_employee_or_404(r.employee_id, db)
            dept = emp.department or "Unknown"
        except HTTPException:
            dept = "Unknown"
        by_dept[dept] = by_dept.get(dept, 0) + 1

    return ExitTrendResponse(
        analysis_period=period,
        department=department,
        exit_rate_pct=exit_rate,
        avg_tenure_years=avg_tenure,
        top_exit_reason=top_reason,
        total_exits=total,
        by_reason=by_reason,
        by_department=by_dept,
    )
