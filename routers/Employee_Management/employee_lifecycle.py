from fastapi import APIRouter

router = APIRouter()

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, extract
from typing import List, Optional
from datetime import datetime, date

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User

from model.HR_Operations.employee_confirmation import EmployeeConfirmation
from model.HR_Operations.promotion import Promotion
from model.HR_Operations.transfer import Transfer
from model.HR_Operations.exit_management import Resignation
from model.HR_Operations.notice_period import NoticePeriod
from model.onboarding.employee import Employee

from schema.HR_Operations.employee_confirmation import (
    EmployeeConfirmationCreate,
    EmployeeConfirmationUpdate,
    EmployeeConfirmationResponse,
)
from schema.HR_Operations.promotion import (
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
)
from schema.HR_Operations.transfer import (
    TransferCreate,
    TransferUpdate,
    TransferResponse,
)
from schema.HR_Operations.exit_management import (
    ResignationCreate,
    ResignationResponse,
    ResignationAccept
)
from schema.HR_Operations.notice_period import (
    NoticePeriodCreate,
    NoticePeriodUpdate,
    NoticePeriodResponse,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/employee-lifecycle", tags=["Employee Lifecycle"])


# ── Dashboard response schemas (defined inline — no separate file needed) ─────

class LifecycleDashboardStats(BaseModel):
    new_joinings_this_month: int
    pending_probation_reviews: int
    transfer_requests_awaiting_approval: int
    active_exits_in_process: int


class LifecycleSummaryBar(BaseModel):
    joining_tasks: int
    active_employees: int
    transfer_requests: int
    exit_processes: int
    contract_renewals: int


class LifecycleStageItem(BaseModel):
    stage: str
    status: str
    effective_date: Optional[date] = None
    details: Optional[str] = None


class EmployeeLifecycleTimeline(BaseModel):
    employee_id: int
    stages: List[LifecycleStageItem]


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/stats", response_model=LifecycleDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Drives the 4 stat cards:
    New Joinings | Pending Probation | Transfer Requests | Active Exits
    """
    now = datetime.utcnow()

    new_joinings = db.execute(
        select(func.count()).select_from(Employee).where(
            extract("month", Employee.joining_date) == now.month,
            extract("year", Employee.joining_date) == now.year,
        )
    ).scalar_one()

    pending_probation = db.execute(
        select(func.count()).select_from(EmployeeConfirmation).where(
            EmployeeConfirmation.status == "PENDING"
        )
    ).scalar_one()

    transfer_requests = db.execute(
        select(func.count()).select_from(Transfer).where(
            Transfer.status == "PENDING"
        )
    ).scalar_one()

    active_exits = db.execute(
        select(func.count()).select_from(Resignation).where(
            Resignation.status.in_(["INITIATED", "IN_PROGRESS"])
        )
    ).scalar_one()

    return LifecycleDashboardStats(
        new_joinings_this_month=new_joinings,
        pending_probation_reviews=pending_probation,
        transfer_requests_awaiting_approval=transfer_requests,
        active_exits_in_process=active_exits,
    )


@router.get("/dashboard/summary", response_model=LifecycleSummaryBar)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Drives the bottom summary bar:
    Joining | Active | Transfers | Exit | Contracts
    """
    joining_tasks = db.execute(
        select(func.count()).select_from(EmployeeConfirmation).where(
            EmployeeConfirmation.status == "PENDING"
        )
    ).scalar_one()

    active_employees = db.execute(
        select(func.count()).select_from(Employee).where(
            Employee.is_active == True
        )
    ).scalar_one()

    transfer_requests = db.execute(
        select(func.count()).select_from(Transfer).where(
            Transfer.status.in_(["PENDING", "APPROVED"])
        )
    ).scalar_one()

    exit_processes = db.execute(
        select(func.count()).select_from(Resignation).where(
            Resignation.status.in_(["INITIATED", "IN_PROGRESS"])
        )
    ).scalar_one()

    contract_renewals = db.execute(
        select(func.count()).select_from(EmployeeConfirmation).where(
            EmployeeConfirmation.status == "EXTENDED"
        )
    ).scalar_one()

    return LifecycleSummaryBar(
        joining_tasks=joining_tasks,
        active_employees=active_employees,
        transfer_requests=transfer_requests,
        exit_processes=exit_processes,
        contract_renewals=contract_renewals,
    )


# ══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE TIMELINE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/timeline/{employee_id}", response_model=EmployeeLifecycleTimeline)
def get_employee_timeline(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full lifecycle timeline for one employee — joining to exit."""
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    stages = []

    # Joining
    stages.append(LifecycleStageItem(
        stage="JOINING",
        status="COMPLETED",
        effective_date=emp.joining_date,
        details=f"Joined on {emp.joining_date}",
    ))

    # Probation
    for c in db.execute(
        select(EmployeeConfirmation)
        .where(EmployeeConfirmation.employee_id == employee_id)
        .order_by(EmployeeConfirmation.created_at)
    ).scalars().all():
        stages.append(LifecycleStageItem(
            stage="PROBATION",
            status=c.status,
            effective_date=c.probation_start_date,
            details=f"Probation: {c.probation_start_date} → {c.probation_end_date}",
        ))

    # Transfers
    for t in db.execute(
        select(Transfer)
        .where(Transfer.employee_id == employee_id)
        .order_by(Transfer.effective_date)
    ).scalars().all():
        stages.append(LifecycleStageItem(
            stage="TRANSFER",
            status=t.status,
            effective_date=t.effective_date,
            details=f"{t.from_department} → {t.to_department} ({t.transfer_type})",
        ))

    # Promotions
    for p in db.execute(
        select(Promotion)
        .where(Promotion.employee_id == employee_id)
        .order_by(Promotion.effective_date)
    ).scalars().all():
        stages.append(LifecycleStageItem(
            stage="PROMOTION",
            status=p.status,
            effective_date=p.effective_date,
            details=f"{p.from_designation} → {p.to_designation}",
        ))

    # Notice Period
    for n in db.execute(
        select(NoticePeriod)
        .where(NoticePeriod.employee_id == employee_id)
        .order_by(NoticePeriod.notice_start_date)
    ).scalars().all():
        stages.append(LifecycleStageItem(
            stage="NOTICE",
            status=n.status,
            effective_date=n.notice_start_date,
            details=f"Notice period: {n.notice_period_days} days",
        ))

    # Exit
    for e in db.execute(
        select(Resignation)
        .where(Resignation.employee_id == employee_id)
        .order_by(Resignation.resignation_date)
    ).scalars().all():
        stages.append(LifecycleStageItem(
            stage="EXIT",
            status=e.status,
            effective_date=e.resignation_date,
            details=f"{e.exit_type} | Clearance: {e.clearance_status}",
        ))

    stages.sort(key=lambda x: x.effective_date or date(1900, 1, 1))
    return EmployeeLifecycleTimeline(employee_id=employee_id, stages=stages)


# ══════════════════════════════════════════════════════════════════════════════
# PROBATION & CONFIRMATION
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/probation", response_model=EmployeeConfirmationResponse, status_code=201)
def start_probation(
    payload: EmployeeConfirmationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    """Start probation for a new joiner."""
    existing = db.execute(
        select(EmployeeConfirmation).where(
            EmployeeConfirmation.employee_id == payload.employee_id,
            EmployeeConfirmation.status == "PENDING",
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Employee already has an active probation.")
    obj = EmployeeConfirmation(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/probation", response_model=List[EmployeeConfirmationResponse])
def list_probations(
    status: Optional[str] = Query(None, description="PENDING | CONFIRMED | EXTENDED | TERMINATED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(EmployeeConfirmation)
    if status:
        stmt = stmt.where(EmployeeConfirmation.status == status)
    return db.execute(stmt).scalars().all()


@router.get("/probation/{employee_id}", response_model=List[EmployeeConfirmationResponse])
def get_probation_by_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.employee_id == employee_id)
    ).scalars().all()


@router.patch("/probation/{confirmation_id}", response_model=EmployeeConfirmationResponse)
def review_probation(
    confirmation_id: int,
    payload: EmployeeConfirmationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin", "hr_manager"])),
):
    """Review probation — CONFIRMED | EXTENDED | TERMINATED."""
    obj = db.get(EmployeeConfirmation, confirmation_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Probation record not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


# ══════════════════════════════════════════════════════════════════════════════
# TRANSFERS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/transfer", response_model=TransferResponse, status_code=201)
def initiate_transfer(
    payload: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin", "hr_manager"])),
):
    """Initiate a transfer request."""
    valid = {"INTER_DEPARTMENT", "INTER_LOCATION", "INTER_COMPANY"}
    if payload.transfer_type not in valid:
        raise HTTPException(status_code=400, detail=f"transfer_type must be one of {valid}.")
    obj = Transfer(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/transfer", response_model=List[TransferResponse])
def list_transfers(
    employee_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="PENDING | APPROVED | REJECTED | COMPLETED"),
    transfer_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Transfer)
    if employee_id:
        stmt = stmt.where(Transfer.employee_id == employee_id)
    if status:
        stmt = stmt.where(Transfer.status == status)
    if transfer_type:
        stmt = stmt.where(Transfer.transfer_type == transfer_type)
    return db.execute(stmt).scalars().all()


@router.get("/transfer/{transfer_id}", response_model=TransferResponse)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = db.get(Transfer, transfer_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Transfer not found.")
    return obj


@router.patch("/transfer/{transfer_id}", response_model=TransferResponse)
def action_transfer(
    transfer_id: int,
    payload: TransferUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin", "hr_manager"])),
):
    """Approve / reject / complete a transfer."""
    obj = db.get(Transfer, transfer_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Transfer not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


# ══════════════════════════════════════════════════════════════════════════════
# PROMOTIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/promotion", response_model=PromotionResponse, status_code=201)
def initiate_promotion(
    payload: PromotionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin", "hr_manager"])),
):
    obj = Promotion(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/promotion", response_model=List[PromotionResponse])
def list_promotions(
    employee_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="PENDING | APPROVED | REJECTED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Promotion)
    if employee_id:
        stmt = stmt.where(Promotion.employee_id == employee_id)
    if status:
        stmt = stmt.where(Promotion.status == status)
    return db.execute(stmt).scalars().all()


@router.get("/promotion/{promotion_id}", response_model=PromotionResponse)
def get_promotion(
    promotion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = db.get(Promotion, promotion_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Promotion not found.")
    return obj


@router.patch("/promotion/{promotion_id}", response_model=PromotionResponse)
def action_promotion(
    promotion_id: int,
    payload: PromotionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin", "hr_manager"])),
):
    """Approve or reject a promotion."""
    obj = db.get(Promotion, promotion_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Promotion not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


# ══════════════════════════════════════════════════════════════════════════════
# EXIT MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/exit", response_model=ResignationResponse, status_code=201)
def initiate_exit(
    payload: ResignationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    """Start exit process for an employee."""
    valid = {"RESIGNATION", "TERMINATION", "RETIREMENT", "ABSCONDING"}
    if payload.exit_type not in valid:
        raise HTTPException(status_code=400, detail=f"exit_type must be one of {valid}.")
    existing = db.execute(
        select(Resignation).where(
            Resignation.employee_id == payload.employee_id,
            Resignation.status.in_(["INITIATED", "IN_PROGRESS"]),
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Employee already has an active exit process.")
    obj = Resignation(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/exit", response_model=List[ResignationResponse])
def list_exits(
    status: Optional[str] = Query(None, description="INITIATED | IN_PROGRESS | COMPLETED | CANCELLED"),
    exit_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Resignation)
    if status:
        stmt = stmt.where(Resignation.status == status)
    if exit_type:
        stmt = stmt.where(Resignation.exit_type == exit_type)
    return db.execute(stmt).scalars().all()


@router.get("/exit/{employee_id}", response_model=List[ResignationResponse])
def get_exit_by_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.execute(
        select(Resignation).where(Resignation.employee_id == employee_id)
    ).scalars().all()


@router.patch("/exit/{exit_id}", response_model=ResignationResponse)
def update_exit(
    exit_id: int,
    payload: ResignationAccept,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    """Update exit — status, clearance, exit interview."""
    obj = db.get(Resignation, exit_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Exit record not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


# ══════════════════════════════════════════════════════════════════════════════
# NOTICE PERIOD
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/notice-period", response_model=NoticePeriodResponse, status_code=201)
def create_notice_period(
    payload: NoticePeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    obj = NoticePeriod(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/notice-period", response_model=List[NoticePeriodResponse])
def list_notice_periods(
    status: Optional[str] = Query(None, description="SERVING | COMPLETED | WAIVED | BUYOUT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(NoticePeriod)
    if status:
        stmt = stmt.where(NoticePeriod.status == status)
    return db.execute(stmt).scalars().all()


@router.get("/notice-period/{employee_id}", response_model=List[NoticePeriodResponse])
def get_notice_period_by_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.execute(
        select(NoticePeriod).where(NoticePeriod.employee_id == employee_id)
    ).scalars().all()


@router.patch("/notice-period/{notice_id}", response_model=NoticePeriodResponse)
def update_notice_period(
    notice_id: int,
    payload: NoticePeriodUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    """Update notice period — waiver, buyout, serving days."""
    obj = db.get(NoticePeriod, notice_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Notice period record not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj
