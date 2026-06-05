# services/Employee_Management/employee_lifecycle_service.py
# Business logic for all Employee Lifecycle tabs

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status
from datetime import date, datetime
from typing import List, Optional

from model.Employee_Management.employee_lifecycle import (
    EmployeeLifecycleEvent,
    OnboardingTask,
    ProbationReview,
    TransferRequest,
    ExitProcess,
    ContractRenewal,
)
from schema.Employee_Management.employee_lifecycle import (
    # Core event
    LifecycleEventCreate, LifecycleEventUpdate,
    LifecycleAnalyticsResponse, LifecycleEventCount,
    # Onboarding
    OnboardingTaskCreate, OnboardingTaskUpdate,
    # Probation
    ProbationReviewCreate, ProbationReviewUpdate,
    # Transfer
    TransferRequestCreate, TransferRequestUpdate,
    # Exit
    ExitProcessCreate, ExitProcessUpdate, ExitProcessWithClearance,
    # Contract
    ContractRenewalCreate, ContractRenewalUpdate, ContractRenewalResponse,
    # Dashboard / Analytics
    LifecycleDashboardResponse, ExitAnalyticsResponse,
)


# ─── Generic helper ───────────────────────────────────────────────────────────

def _get_or_404(db: Session, model, record_id: int, label: str = "Record"):
    obj = db.execute(
        select(model).where(model.id == record_id, model.is_active == True)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} {record_id} not found",
        )
    return obj


def _touch(obj):
    obj.updated_at = datetime.utcnow()


# ══════════════════════════════════════════════════════════════════════════════
# 1. Core Lifecycle Events
# ══════════════════════════════════════════════════════════════════════════════

def log_lifecycle_event(db: Session, payload: LifecycleEventCreate) -> EmployeeLifecycleEvent:
    obj = EmployeeLifecycleEvent(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_employee_lifecycle(
    db: Session,
    employee_id: int,
    event_type: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> List[EmployeeLifecycleEvent]:
    query = select(EmployeeLifecycleEvent).where(
        EmployeeLifecycleEvent.employee_id == employee_id,
        EmployeeLifecycleEvent.is_active == True,
    )
    if event_type:
        query = query.where(EmployeeLifecycleEvent.event_type == event_type)
    if from_date:
        query = query.where(EmployeeLifecycleEvent.event_date >= from_date)
    if to_date:
        query = query.where(EmployeeLifecycleEvent.event_date <= to_date)
    return db.execute(query.order_by(EmployeeLifecycleEvent.event_date.desc())).scalars().all()


def get_lifecycle_event(db: Session, event_id: int) -> EmployeeLifecycleEvent:
    return _get_or_404(db, EmployeeLifecycleEvent, event_id, "Lifecycle event")


def update_lifecycle_event(
    db: Session, event_id: int, payload: LifecycleEventUpdate
) -> EmployeeLifecycleEvent:
    obj = _get_or_404(db, EmployeeLifecycleEvent, event_id, "Lifecycle event")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_lifecycle_event(db: Session, event_id: int) -> None:
    obj = _get_or_404(db, EmployeeLifecycleEvent, event_id, "Lifecycle event")
    obj.is_active = False
    _touch(obj)
    db.commit()


def get_all_events_by_type(
    db: Session, event_type: str,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> List[EmployeeLifecycleEvent]:
    query = select(EmployeeLifecycleEvent).where(
        EmployeeLifecycleEvent.event_type == event_type,
        EmployeeLifecycleEvent.is_active == True,
    )
    if from_date:
        query = query.where(EmployeeLifecycleEvent.event_date >= from_date)
    if to_date:
        query = query.where(EmployeeLifecycleEvent.event_date <= to_date)
    return db.execute(query.order_by(EmployeeLifecycleEvent.event_date.desc())).scalars().all()


def get_lifecycle_analytics(db: Session, employee_id: int) -> LifecycleAnalyticsResponse:
    events = db.execute(
        select(EmployeeLifecycleEvent).where(
            EmployeeLifecycleEvent.employee_id == employee_id,
            EmployeeLifecycleEvent.is_active == True,
        ).order_by(EmployeeLifecycleEvent.event_date.asc())
    ).scalars().all()

    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lifecycle events found for employee {employee_id}",
        )

    type_counts: dict = {}
    for e in events:
        type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1

    events_by_type = [LifecycleEventCount(event_type=k, count=v) for k, v in type_counts.items()]

    joining_event = next((e for e in events if e.event_type == "Joining"), None)
    joining_date = joining_event.event_date if joining_event else None
    tenure_days = (date.today() - joining_date).days if joining_date else None

    current_designation: Optional[str] = None
    for e in reversed(events):
        if e.event_type in ("Promotion", "Designation_Change", "Joining") and e.to_designation:
            current_designation = e.to_designation
            break
        if e.event_type in ("Promotion", "Designation_Change") and e.to_value:
            current_designation = e.to_value
            break

    current_department: Optional[str] = None
    for e in reversed(events):
        if e.event_type in ("Department_Change", "Transfer", "Joining") and e.to_department:
            current_department = e.to_department
            break

    status_map = {
        "Joining": "Active", "Rehire": "Active", "Reinstatement": "Active",
        "Resignation": "Resigned", "Termination": "Terminated",
        "Retirement": "Retired", "Suspension": "Suspended",
    }
    current_status: Optional[str] = None
    for e in reversed(events):
        if e.event_type in status_map:
            current_status = status_map[e.event_type]
            break

    return LifecycleAnalyticsResponse(
        employee_id=employee_id,
        total_events=len(events),
        events_by_type=events_by_type,
        tenure_days=tenure_days,
        joining_date=joining_date,
        current_designation=current_designation,
        current_department=current_department,
        promotions_count=type_counts.get("Promotion", 0),
        transfers_count=(
            type_counts.get("Transfer", 0)
            + type_counts.get("Department_Change", 0)
            + type_counts.get("Location_Change", 0)
        ),
        is_confirmed="Confirmation" in type_counts,
        current_status=current_status,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Onboarding Tasks
# ══════════════════════════════════════════════════════════════════════════════

def create_onboarding_task(db: Session, payload: OnboardingTaskCreate) -> OnboardingTask:
    obj = OnboardingTask(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_onboarding_tasks(
    db: Session, employee_id: Optional[int] = None, status: Optional[str] = None
) -> List[OnboardingTask]:
    query = select(OnboardingTask).where(OnboardingTask.is_active == True)
    if employee_id:
        query = query.where(OnboardingTask.employee_id == employee_id)
    if status:
        query = query.where(OnboardingTask.status == status)
    return db.execute(query.order_by(OnboardingTask.due_date.asc())).scalars().all()


def get_onboarding_task(db: Session, task_id: int) -> OnboardingTask:
    return _get_or_404(db, OnboardingTask, task_id, "Onboarding task")


def update_onboarding_task(
    db: Session, task_id: int, payload: OnboardingTaskUpdate
) -> OnboardingTask:
    obj = _get_or_404(db, OnboardingTask, task_id, "Onboarding task")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == "completed" and not obj.completed_at:
        obj.completed_at = datetime.utcnow()
    for field, value in data.items():
        setattr(obj, field, value)
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return obj


def complete_onboarding_task(db: Session, task_id: int) -> OnboardingTask:
    obj = _get_or_404(db, OnboardingTask, task_id, "Onboarding task")
    obj.status = "completed"
    obj.completed_at = datetime.utcnow()
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_onboarding_task(db: Session, task_id: int) -> None:
    obj = _get_or_404(db, OnboardingTask, task_id, "Onboarding task")
    obj.is_active = False
    _touch(obj)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# 3. Probation Reviews
# ══════════════════════════════════════════════════════════════════════════════

def create_probation_review(db: Session, payload: ProbationReviewCreate) -> ProbationReview:
    obj = ProbationReview(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_probation_reviews(
    db: Session, employee_id: Optional[int] = None, status: Optional[str] = None
) -> List[ProbationReview]:
    query = select(ProbationReview).where(ProbationReview.is_active == True)
    if employee_id:
        query = query.where(ProbationReview.employee_id == employee_id)
    if status:
        query = query.where(ProbationReview.status == status)
    return db.execute(query.order_by(ProbationReview.review_date.asc())).scalars().all()


def get_probation_review(db: Session, review_id: int) -> ProbationReview:
    return _get_or_404(db, ProbationReview, review_id, "Probation review")


def update_probation_review(
    db: Session, review_id: int, payload: ProbationReviewUpdate
) -> ProbationReview:
    obj = _get_or_404(db, ProbationReview, review_id, "Probation review")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return obj


def start_probation_review(db: Session, review_id: int) -> ProbationReview:
    obj = _get_or_404(db, ProbationReview, review_id, "Probation review")
    obj.status = "in-progress"
    obj.manager_review_status = "In Progress"
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return obj


def complete_probation_review(db: Session, review_id: int, rating: str) -> ProbationReview:
    obj = _get_or_404(db, ProbationReview, review_id, "Probation review")
    obj.status = "completed"
    obj.rating = rating
    obj.manager_review_status = "Completed"
    obj.letter_generation_status = "Completed"
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ══════════════════════════════════════════════════════════════════════════════
# 4. Transfer Requests
# ══════════════════════════════════════════════════════════════════════════════

def create_transfer_request(db: Session, payload: TransferRequestCreate) -> TransferRequest:
    obj = TransferRequest(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_transfer_requests(
    db: Session, employee_id: Optional[int] = None, status: Optional[str] = None
) -> List[TransferRequest]:
    query = select(TransferRequest).where(TransferRequest.is_active == True)
    if employee_id:
        query = query.where(TransferRequest.employee_id == employee_id)
    if status:
        query = query.where(TransferRequest.status == status)
    return db.execute(query.order_by(TransferRequest.request_date.desc())).scalars().all()


def get_transfer_request(db: Session, transfer_id: int) -> TransferRequest:
    return _get_or_404(db, TransferRequest, transfer_id, "Transfer request")


def update_transfer_request(
    db: Session, transfer_id: int, payload: TransferRequestUpdate
) -> TransferRequest:
    obj = _get_or_404(db, TransferRequest, transfer_id, "Transfer request")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == "approved":
        obj.approved_at = datetime.utcnow()
        obj.workflow_stage = 4
    for field, value in data.items():
        setattr(obj, field, value)
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return obj


def approve_transfer(db: Session, transfer_id: int, approver_id: Optional[int] = None) -> TransferRequest:
    obj = _get_or_404(db, TransferRequest, transfer_id, "Transfer request")
    obj.status = "approved"
    obj.approved_by = approver_id
    obj.approved_at = datetime.utcnow()
    obj.workflow_stage = 4
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return obj


def reject_transfer(db: Session, transfer_id: int, remarks: Optional[str] = None) -> TransferRequest:
    obj = _get_or_404(db, TransferRequest, transfer_id, "Transfer request")
    obj.status = "rejected"
    if remarks:
        obj.remarks = remarks
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_transfer_request(db: Session, transfer_id: int) -> None:
    obj = _get_or_404(db, TransferRequest, transfer_id, "Transfer request")
    obj.is_active = False
    _touch(obj)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# 5. Exit Processes
# ══════════════════════════════════════════════════════════════════════════════

def _clearance_pending(obj: ExitProcess) -> int:
    return sum([
        not obj.it_clearance,
        not obj.admin_clearance,
        not obj.finance_clearance,
        not obj.hr_clearance,
    ])


def _to_exit_with_clearance(obj: ExitProcess) -> ExitProcessWithClearance:
    data = ExitProcessWithClearance.model_validate(obj)
    data.clearance_pending = _clearance_pending(obj)
    return data


def initiate_exit(db: Session, payload: ExitProcessCreate) -> ExitProcess:
    obj = ExitProcess(**payload.model_dump())
    obj.status = "initiated"
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_exit_processes(
    db: Session, employee_id: Optional[int] = None, status: Optional[str] = None
) -> List[ExitProcessWithClearance]:
    query = select(ExitProcess).where(ExitProcess.is_active == True)
    if employee_id:
        query = query.where(ExitProcess.employee_id == employee_id)
    if status:
        query = query.where(ExitProcess.status == status)
    rows = db.execute(query.order_by(ExitProcess.created_at.desc())).scalars().all()
    return [_to_exit_with_clearance(r) for r in rows]


def get_exit_process(db: Session, exit_id: int) -> ExitProcessWithClearance:
    obj = _get_or_404(db, ExitProcess, exit_id, "Exit process")
    return _to_exit_with_clearance(obj)


def update_exit_process(
    db: Session, exit_id: int, payload: ExitProcessUpdate
) -> ExitProcessWithClearance:
    obj = _get_or_404(db, ExitProcess, exit_id, "Exit process")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    # auto-complete when all clearances done
    if all([obj.it_clearance, obj.admin_clearance, obj.finance_clearance, obj.hr_clearance]):
        obj.status = "completed"
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return _to_exit_with_clearance(obj)


def generate_relieving_letter(db: Session, exit_id: int) -> ExitProcessWithClearance:
    obj = _get_or_404(db, ExitProcess, exit_id, "Exit process")
    obj.relieving_letter_generated = True
    obj.relieving_letter_date = date.today()
    _touch(obj)
    db.commit()
    db.refresh(obj)
    return _to_exit_with_clearance(obj)


def delete_exit_process(db: Session, exit_id: int) -> None:
    obj = _get_or_404(db, ExitProcess, exit_id, "Exit process")
    obj.is_active = False
    _touch(obj)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# 6. Contract Renewals
# ══════════════════════════════════════════════════════════════════════════════

def _days_remaining(obj: ContractRenewal) -> Optional[int]:
    if obj.contract_end:
        delta = (obj.contract_end - date.today()).days
        return max(delta, 0)
    return None


def create_contract_renewal(db: Session, payload: ContractRenewalCreate) -> ContractRenewal:
    obj = ContractRenewal(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_contract_renewals(
    db: Session, employee_id: Optional[int] = None, renewal_status: Optional[str] = None
) -> List[ContractRenewalResponse]:
    query = select(ContractRenewal).where(ContractRenewal.is_active == True)
    if employee_id:
        query = query.where(ContractRenewal.employee_id == employee_id)
    if renewal_status:
        query = query.where(ContractRenewal.renewal_status == renewal_status)
    rows = db.execute(query.order_by(ContractRenewal.contract_end.asc())).scalars().all()
    results = []
    for r in rows:
        resp = ContractRenewalResponse.model_validate(r)
        resp.days_remaining = _days_remaining(r)
        results.append(resp)
    return results


def get_contract_renewal(db: Session, contract_id: int) -> ContractRenewalResponse:
    obj = _get_or_404(db, ContractRenewal, contract_id, "Contract renewal")
    resp = ContractRenewalResponse.model_validate(obj)
    resp.days_remaining = _days_remaining(obj)
    return resp


def update_contract_renewal(
    db: Session, contract_id: int, payload: ContractRenewalUpdate
) -> ContractRenewalResponse:
    obj = _get_or_404(db, ContractRenewal, contract_id, "Contract renewal")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    _touch(obj)
    db.commit()
    db.refresh(obj)
    resp = ContractRenewalResponse.model_validate(obj)
    resp.days_remaining = _days_remaining(obj)
    return resp


def delete_contract_renewal(db: Session, contract_id: int) -> None:
    obj = _get_or_404(db, ContractRenewal, contract_id, "Contract renewal")
    obj.is_active = False
    _touch(obj)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# 7. Dashboard Summary
# ══════════════════════════════════════════════════════════════════════════════

def get_lifecycle_dashboard(db: Session) -> LifecycleDashboardResponse:
    today = date.today()
    month_start = today.replace(day=1)

    new_joinings = db.execute(
        select(func.count()).select_from(EmployeeLifecycleEvent).where(
            EmployeeLifecycleEvent.event_type == "Joining",
            EmployeeLifecycleEvent.event_date >= month_start,
            EmployeeLifecycleEvent.is_active == True,
        )
    ).scalar_one()

    pending_probation = db.execute(
        select(func.count()).select_from(ProbationReview).where(
            ProbationReview.status == "pending",
            ProbationReview.is_active == True,
        )
    ).scalar_one()

    transfer_awaiting = db.execute(
        select(func.count()).select_from(TransferRequest).where(
            TransferRequest.status == "pending",
            TransferRequest.is_active == True,
        )
    ).scalar_one()

    active_exits = db.execute(
        select(func.count()).select_from(ExitProcess).where(
            ExitProcess.status == "in-process",
            ExitProcess.is_active == True,
        )
    ).scalar_one()

    onboarding_total = db.execute(
        select(func.count()).select_from(OnboardingTask).where(OnboardingTask.is_active == True)
    ).scalar_one()

    transfer_total = db.execute(
        select(func.count()).select_from(TransferRequest).where(TransferRequest.is_active == True)
    ).scalar_one()

    exit_total = db.execute(
        select(func.count()).select_from(ExitProcess).where(ExitProcess.is_active == True)
    ).scalar_one()

    contract_total = db.execute(
        select(func.count()).select_from(ContractRenewal).where(ContractRenewal.is_active == True)
    ).scalar_one()

    return LifecycleDashboardResponse(
        new_joinings_this_month=new_joinings,
        pending_probation_reviews=pending_probation,
        transfer_requests_awaiting=transfer_awaiting,
        active_exits=active_exits,
        onboarding_tasks_total=onboarding_total,
        transfer_requests_total=transfer_total,
        exit_processes_total=exit_total,
        contract_renewals_total=contract_total,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 8. Exit Analytics  (Reports & Analytics tab)
# ══════════════════════════════════════════════════════════════════════════════

def get_exit_analytics(db: Session) -> ExitAnalyticsResponse:
    exits = db.execute(
        select(ExitProcess).where(ExitProcess.is_active == True)
    ).scalars().all()

    total = len(exits)
    voluntary = sum(1 for e in exits if (e.exit_type or "").lower() == "voluntary")
    involuntary = sum(1 for e in exits if (e.exit_type or "").lower() == "involuntary")

    # Avg tenure
    tenures = []
    for e in exits:
        if e.notice_period_start and e.last_working_day:
            tenures.append((e.last_working_day - e.notice_period_start).days / 365.0)
    avg_tenure = round(sum(tenures) / len(tenures), 1) if tenures else 0.0

    # Exit reason tallies
    reason_counts: dict = {}
    for e in exits:
        r = e.exit_reason or "Unknown"
        reason_counts[r] = reason_counts.get(r, 0) + 1

    top_reasons = []
    if total > 0:
        top_reasons = [
            {"reason": r, "percentage": round(c / total * 100, 1)}
            for r, c in sorted(reason_counts.items(), key=lambda x: -x[1])
        ]

    # Simple attrition rate = exits / (exits + active)
    active_events = db.execute(
        select(func.count()).select_from(EmployeeLifecycleEvent).where(
            EmployeeLifecycleEvent.event_type == "Joining",
            EmployeeLifecycleEvent.is_active == True,
        )
    ).scalar_one()
    denom = active_events or 1
    attrition_rate = round(total / denom * 100, 1)

    return ExitAnalyticsResponse(
        attrition_rate=attrition_rate,
        voluntary_exits=voluntary,
        involuntary_exits=involuntary,
        avg_tenure_years=avg_tenure,
        top_exit_reasons=top_reasons,
    )
