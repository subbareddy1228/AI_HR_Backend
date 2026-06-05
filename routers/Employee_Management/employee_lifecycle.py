# routers/Employee_Management/employee_lifecycle.py
# REPLACE the current empty stub with this full implementation

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from schema.Employee_Management.employee_lifecycle import (
    LifecycleEventCreate,
    LifecycleEventUpdate,
    LifecycleEventResponse,
    EmployeeTimeline,
    JoiningCreate,
    ProbationCreate,
    ProbationReview,
    TransferCreate,
    PromotionCreate,
    ExitCreate,
    StatusUpdate,
)
from services.Employee_Management.employee_lifecycle_service import (
    create_lifecycle_event,
    get_lifecycle_event,
    list_lifecycle_events,
    update_lifecycle_event,
    delete_lifecycle_event,
    initiate_joining,
    start_probation,
    review_probation,
    initiate_transfer,
    initiate_promotion,
    initiate_exit,
    approve_or_reject_event,
    get_employee_timeline,
)

router = APIRouter(
    prefix="/api/employee-lifecycle",
    tags=["Employee Lifecycle"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Generic CRUD
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/events", response_model=LifecycleEventResponse, status_code=201)
def create_event(
    payload: LifecycleEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    """Create a lifecycle event manually (admin / data migration use)."""
    return create_lifecycle_event(db, payload)


@router.get("/events", response_model=List[LifecycleEventResponse])
def list_events(
    employee_id: Optional[int] = Query(None),
    stage: Optional[str] = Query(
        None,
        description="JOINING | PROBATION | CONFIRMED | TRANSFER | PROMOTION | EXIT",
    ),
    status: Optional[str] = Query(
        None,
        description="PENDING | APPROVED | REJECTED | COMPLETED | CANCELLED",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all lifecycle events with optional filters."""
    return list_lifecycle_events(
        db,
        employee_id=employee_id,
        stage=stage,
        status_filter=status,
    )


@router.get("/events/{event_id}", response_model=LifecycleEventResponse)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single lifecycle event by ID."""
    return get_lifecycle_event(db, event_id)


@router.put("/events/{event_id}", response_model=LifecycleEventResponse)
def update_event(
    event_id: int,
    payload: LifecycleEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    """Update a lifecycle event."""
    return update_lifecycle_event(db, event_id, payload)


@router.delete("/events/{event_id}", status_code=204)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin"])),
):
    """Delete a lifecycle event (superadmin only)."""
    delete_lifecycle_event(db, event_id)


# ──────────────────────────────────────────────────────────────────────────────
# Employee Timeline
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/timeline/{employee_id}", response_model=EmployeeTimeline)
def employee_timeline(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Full lifecycle timeline for one employee (oldest event first).
    Used by frontend to render the stage progress / history view.
    """
    events = get_employee_timeline(db, employee_id)
    return EmployeeTimeline(employee_id=employee_id, events=events)


# ──────────────────────────────────────────────────────────────────────────────
# Stage-specific endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/joining", response_model=LifecycleEventResponse, status_code=201)
def joining(
    payload: JoiningCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    """Trigger JOINING event when a candidate converts to an employee."""
    return initiate_joining(db, payload)


@router.post("/probation", response_model=LifecycleEventResponse, status_code=201)
def probation_start(
    payload: ProbationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    """Start a probation period for an employee."""
    return start_probation(db, payload)


@router.patch("/probation/{event_id}/review", response_model=LifecycleEventResponse)
def probation_review(
    event_id: int,
    payload: ProbationReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin", "hr_manager"])),
):
    """
    Submit probation review outcome.
    status must be: CONFIRMED | EXTENDED | TERMINATED
    """
    return review_probation(db, event_id, payload)


@router.post("/transfer", response_model=LifecycleEventResponse, status_code=201)
def transfer(
    payload: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin", "hr_manager"])),
):
    """
    Initiate a transfer request.
    sub_type: INTER_DEPARTMENT | INTER_LOCATION | INTER_COMPANY
    """
    return initiate_transfer(db, payload)


@router.post("/promotion", response_model=LifecycleEventResponse, status_code=201)
def promotion(
    payload: PromotionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin", "hr_manager"])),
):
    """Initiate a promotion for an employee."""
    return initiate_promotion(db, payload)


@router.post("/exit", response_model=LifecycleEventResponse, status_code=201)
def exit_initiate(
    payload: ExitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin"])),
):
    """
    Start the exit process for an employee.
    sub_type: RESIGNATION | TERMINATION | RETIREMENT | ABSCONDING
    """
    return initiate_exit(db, payload)


@router.patch("/events/{event_id}/action", response_model=LifecycleEventResponse)
def action_event(
    event_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "hr_admin", "hr_manager"])),
):
    """
    Approve / reject / complete any PENDING event (TRANSFER, PROMOTION, EXIT).
    status: APPROVED | REJECTED | COMPLETED | CANCELLED
    """
    return approve_or_reject_event(db, event_id, payload)
