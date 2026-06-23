"""
routers/HR_Operations/employee_confirmation.py

Employee Confirmation Management — full backend matching the dashboard:

  Dashboard      : Total / Pending Review / Pending Approval / Confirmed / Overdue / Due This Week
  Quick Actions  : Send Reminders / Approve Pending / Export Data / Auto Trigger Reviews
  List + filters : status / department / eligibility / search / sort
  Approval flow  : Manager -> HR -> Dept Head -> Authority (per-stage actions)
  Extend         : extend probation ("Extended 1x" tracking)
  Reports        : date range + department + status -> JSON / CSV / PDF / EXCEL
  Bulk actions   : multi-select reminder / approve / mark-under-review
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db
from model.HR_Operations.employee_confirmation import (
    EmployeeConfirmation,
    ConfirmationApprovalStage,
)
from model.onboarding.employee import Employee
from schema.HR_Operations.employee_confirmation import (
    EmployeeConfirmationCreate,
    EmployeeConfirmationUpdate,
    EmployeeConfirmationResponse,
    ExtendProbationRequest,
    ApprovalStageResponse,
    ApprovalStageAction,
    ConfirmationDashboardStats,
    SendRemindersResponse,
    ApprovePendingResponse,
    AutoTriggerReviewsResponse,
    BulkActionRequest,
    ConfirmationReportRequest,
)
from services.employee_confirmation_service import (
    seed_approval_stages,
    resolve_confirmation_status,
    compute_eligibility,
    compute_time_status,
    refresh_overdue_status,
    get_dashboard_stats,
    send_reminders,
    approve_pending,
    auto_trigger_reviews,
    export_report_json,
    export_report_csv,
    export_report_excel,
    export_report_pdf,
)

router = APIRouter(prefix="/api/hr-operations/confirmations", tags=["HR Operations - Employee Confirmation"])


# ======================================================
# HELPERS
# ======================================================
def _get_employee_or_404(db: Session, employee_id: int) -> Employee:
    employee = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


def _get_confirmation_or_404(db: Session, confirmation_id: int) -> EmployeeConfirmation:
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == confirmation_id)
    ).scalar_one_or_none()
    if not conf:
        raise HTTPException(status_code=404, detail="Confirmation case not found")
    return conf


def _employee_mini(employee: Optional[Employee]) -> Optional[dict]:
    if not employee:
        return None
    full_name = " ".join(p for p in [employee.first_name, employee.middle_name, employee.last_name] if p)
    return {
        "id": employee.id,
        "employee_code": employee.employee_code,
        "full_name": full_name,
        "department": employee.department,
        "designation": employee.designation,
    }


def _get_stages(db: Session, confirmation_id: int) -> list:
    return (
        db.execute(
            select(ConfirmationApprovalStage)
            .where(ConfirmationApprovalStage.confirmation_id == confirmation_id)
            .order_by(ConfirmationApprovalStage.stage_order)
        )
        .scalars()
        .all()
    )


def _serialize_confirmation(db: Session, conf: EmployeeConfirmation, employee: Optional[Employee]) -> dict:
    data = EmployeeConfirmationResponse.model_validate(conf).model_dump()
    data["employee"] = _employee_mini(employee)

    stages = _get_stages(db, conf.id)
    data["approval_stages"] = [ApprovalStageResponse.model_validate(s).model_dump() for s in stages]

    time_status = compute_time_status(conf)
    data["days_until_due"] = time_status["days_until_due"]
    data["is_overdue"] = time_status["is_overdue"]

    return data


# ======================================================
# 1. DASHBOARD
# ======================================================
@router.get("/dashboard", response_model=ConfirmationDashboardStats)
def get_confirmation_dashboard(db: Session = Depends(get_db)):
    """Powers the Total / Pending Review / Pending Approval / Confirmed / Overdue / Due This Week tiles."""
    return get_dashboard_stats(db)


# ======================================================
# 2. CREATE / LIST / GET / UPDATE / DELETE
# ======================================================
@router.post("", response_model=EmployeeConfirmationResponse, status_code=status.HTTP_201_CREATED)
def create_confirmation_case(payload: EmployeeConfirmationCreate, db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, payload.employee_id)

    case = EmployeeConfirmation(**payload.model_dump())
    db.add(case)
    db.flush()  # get case.id

    seed_approval_stages(db, case.id)

    db.commit()
    db.refresh(case)
    return _serialize_confirmation(db, case, employee)


@router.get("", response_model=List[EmployeeConfirmationResponse])
def list_confirmation_cases(
    search: Optional[str] = Query(None, description="Search by employee name or code"),
    status_filter: Optional[str] = Query(None, alias="status"),
    department: Optional[str] = Query(None),
    eligibility: Optional[str] = Query(None, description="ELIGIBLE | CONDITIONAL | NOT_ELIGIBLE"),
    sort_by: str = Query("due_date", description="due_date | name | days_remaining | joining_date"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(EmployeeConfirmation, Employee).join(
        Employee, EmployeeConfirmation.employee_id == Employee.id
    )

    if status_filter:
        query = query.where(EmployeeConfirmation.status == status_filter.upper())
    if department:
        query = query.where(Employee.department.ilike(f"%{department}%"))
    if eligibility:
        query = query.where(EmployeeConfirmation.eligibility == eligibility.upper())
    if search:
        like = f"%{search}%"
        query = query.where(
            (Employee.first_name.ilike(like))
            | (Employee.last_name.ilike(like))
            | (Employee.employee_code.ilike(like))
        )

    if sort_by == "name":
        query = query.order_by(Employee.first_name.asc())
    elif sort_by == "joining_date":
        query = query.order_by(Employee.joining_date.asc())
    elif sort_by == "days_remaining":
        query = query.order_by(EmployeeConfirmation.probation_end_date.asc())
    else:  # due_date
        query = query.order_by(EmployeeConfirmation.probation_end_date.asc())

    query = query.offset(offset).limit(limit)

    rows = db.execute(query).all()

    # refresh overdue flags lazily on read
    for conf, _ in rows:
        refresh_overdue_status(db, conf)
        conf.eligibility = compute_eligibility(conf)
    db.commit()

    return [_serialize_confirmation(db, conf, emp) for conf, emp in rows]


@router.get("/{confirmation_id}", response_model=EmployeeConfirmationResponse)
def get_confirmation_case(confirmation_id: int, db: Session = Depends(get_db)):
    conf = _get_confirmation_or_404(db, confirmation_id)
    refresh_overdue_status(db, conf)
    conf.eligibility = compute_eligibility(conf)
    db.commit()

    employee = _get_employee_or_404(db, conf.employee_id)
    return _serialize_confirmation(db, conf, employee)


@router.put("/{confirmation_id}", response_model=EmployeeConfirmationResponse)
def update_confirmation_case(confirmation_id: int, payload: EmployeeConfirmationUpdate, db: Session = Depends(get_db)):
    conf = _get_confirmation_or_404(db, confirmation_id)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(conf, key, value)

    conf.eligibility = compute_eligibility(conf)
    refresh_overdue_status(db, conf)

    db.commit()
    db.refresh(conf)
    employee = _get_employee_or_404(db, conf.employee_id)
    return _serialize_confirmation(db, conf, employee)


@router.delete("/{confirmation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_confirmation_case(confirmation_id: int, db: Session = Depends(get_db)):
    conf = _get_confirmation_or_404(db, confirmation_id)
    db.delete(conf)
    db.commit()


# ======================================================
# 3. APPROVAL WORKFLOW (Manager -> HR -> Dept Head -> Authority)
# ======================================================
@router.post("/{confirmation_id}/approval-stages/action", response_model=EmployeeConfirmationResponse)
def act_on_approval_stage(confirmation_id: int, payload: ApprovalStageAction, db: Session = Depends(get_db)):
    conf = _get_confirmation_or_404(db, confirmation_id)

    stage = db.execute(
        select(ConfirmationApprovalStage).where(
            ConfirmationApprovalStage.confirmation_id == confirmation_id,
            ConfirmationApprovalStage.stage_name == payload.stage_name.upper(),
        )
    ).scalar_one_or_none()

    if not stage:
        raise HTTPException(status_code=404, detail="Approval stage not found for this case")
    if stage.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Stage {stage.stage_name} is already {stage.status}")

    decision = payload.decision.upper()
    if decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="decision must be APPROVED or REJECTED")

    from datetime import datetime as _dt

    stage.status = decision
    stage.approver_id = payload.approver_id
    stage.remarks = payload.remarks
    stage.acted_at = _dt.utcnow()

    # manager stage doubles as the "manager recommendation" badge
    if stage.stage_name == "MANAGER":
        conf.manager_recommendation = "RECOMMENDED" if decision == "APPROVED" else "NOT_RECOMMENDED"

    new_status = resolve_confirmation_status(db, conf)
    conf.status = new_status
    if new_status == "CONFIRMED":
        conf.confirmation_date = date.today()

    refresh_overdue_status(db, conf)

    db.commit()
    db.refresh(conf)
    employee = _get_employee_or_404(db, conf.employee_id)
    return _serialize_confirmation(db, conf, employee)


@router.get("/{confirmation_id}/approval-stages", response_model=List[ApprovalStageResponse])
def list_approval_stages(confirmation_id: int, db: Session = Depends(get_db)):
    _get_confirmation_or_404(db, confirmation_id)
    return _get_stages(db, confirmation_id)


# ======================================================
# 4. EXTEND PROBATION  ("Extended 1x" tracking)
# ======================================================
@router.post("/{confirmation_id}/extend", response_model=EmployeeConfirmationResponse)
def extend_probation(confirmation_id: int, payload: ExtendProbationRequest, db: Session = Depends(get_db)):
    conf = _get_confirmation_or_404(db, confirmation_id)

    conf.extended_till = payload.extended_till
    conf.extension_count = (conf.extension_count or 0) + 1
    conf.status = "EXTENDED"
    if payload.remarks:
        conf.remarks = payload.remarks

    conf.eligibility = compute_eligibility(conf)

    db.commit()
    db.refresh(conf)
    employee = _get_employee_or_404(db, conf.employee_id)
    return _serialize_confirmation(db, conf, employee)


# ======================================================
# 5. QUICK ACTIONS
# ======================================================
@router.post("/actions/send-reminders", response_model=SendRemindersResponse)
def action_send_reminders(db: Session = Depends(get_db)):
    return send_reminders(db)


@router.post("/actions/approve-pending", response_model=ApprovePendingResponse)
def action_approve_pending(db: Session = Depends(get_db)):
    return approve_pending(db)


@router.post("/actions/auto-trigger-reviews", response_model=AutoTriggerReviewsResponse)
def action_auto_trigger_reviews(db: Session = Depends(get_db)):
    return auto_trigger_reviews(db)


@router.post("/actions/bulk")
def action_bulk(payload: BulkActionRequest, db: Session = Depends(get_db)):
    action = payload.action.upper()
    affected = 0

    cases = (
        db.execute(
            select(EmployeeConfirmation).where(EmployeeConfirmation.id.in_(payload.confirmation_ids))
        )
        .scalars()
        .all()
    )

    from datetime import datetime as _dt

    for case in cases:
        if action == "SEND_REMINDER":
            case.last_reminder_sent_at = _dt.utcnow()
            affected += 1
        elif action == "MARK_UNDER_REVIEW":
            case.status = "UNDER_REVIEW"
            affected += 1
        elif action == "APPROVE_PENDING":
            next_stage = (
                db.query(ConfirmationApprovalStage)
                .filter(
                    ConfirmationApprovalStage.confirmation_id == case.id,
                    ConfirmationApprovalStage.status == "PENDING",
                )
                .order_by(ConfirmationApprovalStage.stage_order)
                .first()
            )
            if next_stage:
                next_stage.status = "APPROVED"
                next_stage.acted_at = _dt.utcnow()
                case.status = resolve_confirmation_status(db, case)
                affected += 1
        else:
            raise HTTPException(status_code=400, detail="action must be SEND_REMINDER, APPROVE_PENDING, or MARK_UNDER_REVIEW")

    db.commit()
    return {"affected": affected, "action": action}


# ======================================================
# 6. REPORTS
# ======================================================
@router.post("/reports/preview")
def preview_confirmation_report(payload: ConfirmationReportRequest, db: Session = Depends(get_db)):
    """Powers the 'Report Preview' box in the Confirmation Reports modal."""
    data = export_report_json(db, payload.start_date, payload.end_date, payload.department, payload.status)
    return {
        "total_records": data["total_records"],
        "includes": [
            "Confirmation statistics and analytics",
            "Employee-wise confirmation status",
            "Department-wise confirmation rates",
            "Extension analysis",
            "Time-to-confirmation metrics",
        ],
    }


@router.post("/reports/generate")
def generate_confirmation_report(payload: ConfirmationReportRequest, db: Session = Depends(get_db)):
    fmt = payload.export_format.upper()

    if fmt == "JSON":
        data = export_report_json(db, payload.start_date, payload.end_date, payload.department, payload.status)
        return JSONResponse(content=data)

    if fmt == "CSV":
        buffer = export_report_csv(db, payload.start_date, payload.end_date, payload.department, payload.status)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="confirmation_report.csv"'},
        )

    if fmt == "EXCEL":
        buffer = export_report_excel(db, payload.start_date, payload.end_date, payload.department, payload.status)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="confirmation_report.xlsx"'},
        )

    if fmt == "PDF":
        buffer = export_report_pdf(db, payload.start_date, payload.end_date, payload.department, payload.status)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="confirmation_report.pdf"'},
        )

    raise HTTPException(status_code=400, detail="export_format must be one of JSON, CSV, PDF, EXCEL")


@router.get("/export/data")
def export_data(db: Session = Depends(get_db)):
    """Powers the 'Export Data' quick action button -> quick JSON dump of all cases."""
    rows = db.execute(
        select(EmployeeConfirmation, Employee).join(Employee, EmployeeConfirmation.employee_id == Employee.id)
    ).all()

    records = []
    for conf, emp in rows:
        full_name = " ".join(p for p in [emp.first_name, emp.middle_name, emp.last_name] if p)
        records.append({
            "employee": full_name,
            "employee_code": emp.employee_code,
            "department": emp.department,
            "status": conf.status,
            "eligibility": conf.eligibility,
            "probation_end_date": conf.probation_end_date.isoformat(),
        })

    return {"total": len(records), "records": records}