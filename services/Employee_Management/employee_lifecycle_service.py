# services/Employee_Management/employee_lifecycle_service.py
# D5 - Employee Org & Lifecycle
# Business logic for lifecycle event CRUD + analytics

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status
from datetime import date, datetime
from typing import List, Optional

from model.Employee_Management.employee_lifecycle import EmployeeLifecycleEvent
from schema.Employee_Management.employee_lifecycle import (
    LifecycleEventCreate,
    LifecycleEventUpdate,
    LifecycleAnalyticsResponse,
    LifecycleEventCount,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_or_404(db: Session, event_id: int) -> EmployeeLifecycleEvent:
    obj = db.execute(
        select(EmployeeLifecycleEvent).where(
            EmployeeLifecycleEvent.id == event_id,
            EmployeeLifecycleEvent.is_active == True,
        )
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lifecycle event {event_id} not found",
        )
    return obj


# ─── CRUD ─────────────────────────────────────────────────────────────────────

def log_lifecycle_event(
    db: Session, payload: LifecycleEventCreate
) -> EmployeeLifecycleEvent:
    """Create a new lifecycle event for an employee."""
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
    """Return all active lifecycle events for an employee, with optional filters."""
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
    """Return a single lifecycle event by id."""
    return _get_or_404(db, event_id)


def update_lifecycle_event(
    db: Session, event_id: int, payload: LifecycleEventUpdate
) -> EmployeeLifecycleEvent:
    """Update an existing lifecycle event."""
    obj = _get_or_404(db, event_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def delete_lifecycle_event(db: Session, event_id: int) -> None:
    """Soft-delete a lifecycle event."""
    obj = _get_or_404(db, event_id)
    obj.is_active = False
    obj.updated_at = datetime.utcnow()
    db.commit()


# ─── Analytics ────────────────────────────────────────────────────────────────

def get_lifecycle_analytics(
    db: Session, employee_id: int
) -> LifecycleAnalyticsResponse:
    """
    Compute a summary of lifecycle events for an employee:
    - total events
    - breakdown by event type
    - tenure (days since joining)
    - promotion / transfer counts
    - current designation / department (from latest events)
    - confirmation status
    """
    events: List[EmployeeLifecycleEvent] = db.execute(
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

    # Count by type
    type_counts: dict = {}
    for e in events:
        type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1

    events_by_type = [
        LifecycleEventCount(event_type=k, count=v) for k, v in type_counts.items()
    ]

    # Joining date + tenure
    joining_event = next(
        (e for e in events if e.event_type == "Joining"), None
    )
    joining_date = joining_event.event_date if joining_event else None
    tenure_days = (date.today() - joining_date).days if joining_date else None

    # Latest designation from Promotion / Designation_Change / Joining events
    current_designation: Optional[str] = None
    for e in reversed(events):
        if e.event_type in ("Promotion", "Designation_Change", "Joining") and e.to_designation:
            current_designation = e.to_designation
            break
        if e.event_type in ("Promotion", "Designation_Change") and e.to_value:
            current_designation = e.to_value
            break

    # Latest department from Department_Change / Transfer / Joining events
    current_department: Optional[str] = None
    for e in reversed(events):
        if e.event_type in ("Department_Change", "Transfer", "Joining") and e.to_department:
            current_department = e.to_department
            break

    # Current status (latest Resignation / Termination / Reinstatement / Joining)
    current_status: Optional[str] = None
    status_map = {
        "Joining": "Active",
        "Rehire": "Active",
        "Reinstatement": "Active",
        "Resignation": "Resigned",
        "Termination": "Terminated",
        "Retirement": "Retired",
        "Suspension": "Suspended",
    }
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
        transfers_count=type_counts.get("Transfer", 0)
                       + type_counts.get("Department_Change", 0)
                       + type_counts.get("Location_Change", 0),
        is_confirmed="Confirmation" in type_counts,
        current_status=current_status,
    )


def get_all_events_by_type(
    db: Session, event_type: str, from_date: Optional[date] = None, to_date: Optional[date] = None
) -> List[EmployeeLifecycleEvent]:
    """Fetch all lifecycle events of a given type across all employees (for reports)."""
    query = select(EmployeeLifecycleEvent).where(
        EmployeeLifecycleEvent.event_type == event_type,
        EmployeeLifecycleEvent.is_active == True,
    )
    if from_date:
        query = query.where(EmployeeLifecycleEvent.event_date >= from_date)
    if to_date:
        query = query.where(EmployeeLifecycleEvent.event_date <= to_date)
    return db.execute(query.order_by(EmployeeLifecycleEvent.event_date.desc())).scalars().all()
