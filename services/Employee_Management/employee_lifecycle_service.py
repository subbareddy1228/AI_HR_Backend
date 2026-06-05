# services/Employee_Management/employee_lifecycle_service.py
# Service layer for Employee Lifecycle management
# This file does NOT exist yet — create it here

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from fastapi import HTTPException, status

from model.Employee_Management.employee_lifecycle import EmployeeLifecycleEvent
from schema.Employee_Management.employee_lifecycle import (
    LifecycleEventCreate,
    LifecycleEventUpdate,
    JoiningCreate,
    ProbationCreate,
    ProbationReview,
    TransferCreate,
    PromotionCreate,
    ExitCreate,
    StatusUpdate,
)


# ──────────────────────────────────────────────────────────────────────────────
# Internal helper
# ──────────────────────────────────────────────────────────────────────────────

def _get_or_404(db: Session, event_id: int) -> EmployeeLifecycleEvent:
    obj = db.get(EmployeeLifecycleEvent, event_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lifecycle event not found.",
        )
    return obj


def _create_event(db: Session, **kwargs) -> EmployeeLifecycleEvent:
    obj = EmployeeLifecycleEvent(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ──────────────────────────────────────────────────────────────────────────────
# Generic CRUD (used by admin / migration routes)
# ──────────────────────────────────────────────────────────────────────────────

def create_lifecycle_event(
    db: Session, payload: LifecycleEventCreate
) -> EmployeeLifecycleEvent:
    return _create_event(db, **payload.model_dump())


def get_lifecycle_event(db: Session, event_id: int) -> EmployeeLifecycleEvent:
    return _get_or_404(db, event_id)


def list_lifecycle_events(
    db: Session,
    employee_id: Optional[int] = None,
    stage: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[EmployeeLifecycleEvent]:
    stmt = select(EmployeeLifecycleEvent)
    if employee_id:
        stmt = stmt.where(EmployeeLifecycleEvent.employee_id == employee_id)
    if stage:
        stmt = stmt.where(EmployeeLifecycleEvent.stage == stage)
    if status_filter:
        stmt = stmt.where(EmployeeLifecycleEvent.status == status_filter)
    stmt = stmt.order_by(EmployeeLifecycleEvent.effective_date.desc())
    return db.execute(stmt).scalars().all()


def update_lifecycle_event(
    db: Session, event_id: int, payload: LifecycleEventUpdate
) -> EmployeeLifecycleEvent:
    obj = _get_or_404(db, event_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_lifecycle_event(db: Session, event_id: int) -> None:
    obj = _get_or_404(db, event_id)
    db.delete(obj)
    db.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Stage-specific service functions
# ──────────────────────────────────────────────────────────────────────────────

def initiate_joining(
    db: Session, payload: JoiningCreate
) -> EmployeeLifecycleEvent:
    """Mark an employee as JOINING — called on candidate-to-employee conversion."""
    return _create_event(
        db,
        employee_id=payload.employee_id,
        stage="JOINING",
        status="COMPLETED",
        effective_date=payload.effective_date,
        remarks=payload.remarks,
        initiated_by=payload.initiated_by,
    )


def start_probation(
    db: Session, payload: ProbationCreate
) -> EmployeeLifecycleEvent:
    """Start a probation period. Raises 409 if one is already active."""
    existing = db.execute(
        select(EmployeeLifecycleEvent).where(
            EmployeeLifecycleEvent.employee_id == payload.employee_id,
            EmployeeLifecycleEvent.stage == "PROBATION",
            EmployeeLifecycleEvent.status == "PENDING",
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee already has an active probation event.",
        )

    return _create_event(
        db,
        employee_id=payload.employee_id,
        stage="PROBATION",
        status="PENDING",
        effective_date=payload.effective_date,
        end_date=payload.end_date,
        remarks=payload.remarks,
        initiated_by=payload.initiated_by,
    )


def review_probation(
    db: Session, event_id: int, payload: ProbationReview
) -> EmployeeLifecycleEvent:
    """
    HR/Manager reviews a probation event.
    payload.status must be: CONFIRMED | EXTENDED | TERMINATED
    """
    allowed = {"CONFIRMED", "EXTENDED", "TERMINATED"}
    if payload.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Probation status must be one of {allowed}.",
        )

    obj = _get_or_404(db, event_id)
    if obj.stage != "PROBATION":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event is not a PROBATION event.",
        )

    obj.status = payload.status
    if payload.end_date:
        obj.end_date = payload.end_date
    if payload.remarks:
        obj.remarks = payload.remarks
    if payload.approved_by:
        obj.approved_by = payload.approved_by

    db.commit()
    db.refresh(obj)
    return obj


def initiate_transfer(
    db: Session, payload: TransferCreate
) -> EmployeeLifecycleEvent:
    """Raise a transfer request. sub_type must be INTER_DEPARTMENT / INTER_LOCATION / INTER_COMPANY."""
    valid = {"INTER_DEPARTMENT", "INTER_LOCATION", "INTER_COMPANY"}
    if payload.sub_type not in valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"sub_type must be one of {valid}.",
        )
    return _create_event(
        db,
        employee_id=payload.employee_id,
        stage="TRANSFER",
        status="PENDING",
        effective_date=payload.effective_date,
        from_value=payload.from_value,
        to_value=payload.to_value,
        sub_type=payload.sub_type,
        remarks=payload.remarks,
        initiated_by=payload.initiated_by,
    )


def initiate_promotion(
    db: Session, payload: PromotionCreate
) -> EmployeeLifecycleEvent:
    """Raise a promotion request."""
    return _create_event(
        db,
        employee_id=payload.employee_id,
        stage="PROMOTION",
        status="PENDING",
        effective_date=payload.effective_date,
        from_value=payload.from_value,
        to_value=payload.to_value,
        remarks=payload.remarks,
        initiated_by=payload.initiated_by,
    )


def initiate_exit(
    db: Session, payload: ExitCreate
) -> EmployeeLifecycleEvent:
    """Start exit process. sub_type must be RESIGNATION / TERMINATION / RETIREMENT / ABSCONDING."""
    valid = {"RESIGNATION", "TERMINATION", "RETIREMENT", "ABSCONDING"}
    if payload.sub_type not in valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"sub_type must be one of {valid}.",
        )

    # Guard: prevent duplicate active exit
    active = db.execute(
        select(EmployeeLifecycleEvent).where(
            EmployeeLifecycleEvent.employee_id == payload.employee_id,
            EmployeeLifecycleEvent.stage == "EXIT",
            EmployeeLifecycleEvent.status.in_(["PENDING", "IN_PROGRESS"]),
        )
    ).scalar_one_or_none()

    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee already has an active exit process.",
        )

    return _create_event(
        db,
        employee_id=payload.employee_id,
        stage="EXIT",
        status="PENDING",
        effective_date=payload.effective_date,
        end_date=payload.end_date,
        sub_type=payload.sub_type,
        remarks=payload.remarks,
        initiated_by=payload.initiated_by,
    )


def approve_or_reject_event(
    db: Session, event_id: int, payload: StatusUpdate
) -> EmployeeLifecycleEvent:
    """
    Generic approve / reject / complete for TRANSFER, PROMOTION, EXIT events.
    payload.status: APPROVED | REJECTED | COMPLETED | CANCELLED
    """
    obj = _get_or_404(db, event_id)
    obj.status = payload.status
    if payload.remarks:
        obj.remarks = payload.remarks
    if payload.approved_by:
        obj.approved_by = payload.approved_by
    db.commit()
    db.refresh(obj)
    return obj


def get_employee_timeline(
    db: Session, employee_id: int
) -> List[EmployeeLifecycleEvent]:
    """Return all lifecycle events for an employee sorted oldest-first."""
    return db.execute(
        select(EmployeeLifecycleEvent)
        .where(EmployeeLifecycleEvent.employee_id == employee_id)
        .order_by(EmployeeLifecycleEvent.effective_date.asc())
    ).scalars().all()
