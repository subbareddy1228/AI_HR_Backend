# routers/Employee_Management/employee_lifecycle.py
# D5 - Employee Org & Lifecycle
# Prefix: /api/employees/lifecycle
# Tags: Employee Management

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from core.database import get_db
from schema.Employee_Management.employee_lifecycle import (
    LifecycleEventCreate,
    LifecycleEventUpdate,
    LifecycleEventResponse,
    LifecycleAnalyticsResponse,
)
from services.Employee_Management.employee_lifecycle_service import (
    log_lifecycle_event,
    get_employee_lifecycle,
    get_lifecycle_event,
    update_lifecycle_event,
    delete_lifecycle_event,
    get_lifecycle_analytics,
    get_all_events_by_type,
)

router = APIRouter(prefix="/lifecycle", tags=["Employee Management"])


# ── POST /lifecycle/  ──────────────────────────────────────────────────────────
@router.post("/", response_model=LifecycleEventResponse, status_code=status.HTTP_201_CREATED,
             summary="Log a new lifecycle event for an employee")
def create_lifecycle_event(
    payload: LifecycleEventCreate,
    db: Session = Depends(get_db),
):
    """
    Log any employment lifecycle event — joining, promotion, transfer,
    confirmation, resignation, termination, etc.
    """
    return log_lifecycle_event(db, payload)


# ── GET /lifecycle/employee/{employee_id}  ─────────────────────────────────────
@router.get(
    "/employee/{employee_id}",
    response_model=List[LifecycleEventResponse],
    summary="Get all lifecycle events for an employee",
)
def list_employee_lifecycle(
    employee_id: int,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Returns the complete employment timeline for an employee.
    Optionally filter by event_type, from_date, to_date.
    """
    return get_employee_lifecycle(db, employee_id, event_type, from_date, to_date)


# ── GET /lifecycle/employee/{employee_id}/analytics  ──────────────────────────
@router.get(
    "/employee/{employee_id}/analytics",
    response_model=LifecycleAnalyticsResponse,
    summary="Get lifecycle analytics / summary for an employee",
)
def lifecycle_analytics(
    employee_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns analytics for an employee:
    - tenure in days
    - promotions / transfers count
    - current designation, department, status
    - full event-type breakdown
    - confirmation status
    """
    return get_lifecycle_analytics(db, employee_id)


# ── GET /lifecycle/event/{event_id}  ──────────────────────────────────────────
@router.get(
    "/event/{event_id}",
    response_model=LifecycleEventResponse,
    summary="Get a single lifecycle event by ID",
)
def get_event(event_id: int, db: Session = Depends(get_db)):
    return get_lifecycle_event(db, event_id)


# ── PUT /lifecycle/event/{event_id}  ──────────────────────────────────────────
@router.put(
    "/event/{event_id}",
    response_model=LifecycleEventResponse,
    summary="Update a lifecycle event",
)
def update_event(
    event_id: int,
    payload: LifecycleEventUpdate,
    db: Session = Depends(get_db),
):
    return update_lifecycle_event(db, event_id, payload)


# ── DELETE /lifecycle/event/{event_id}  ───────────────────────────────────────
@router.delete(
    "/event/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a lifecycle event",
)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    delete_lifecycle_event(db, event_id)


# ── GET /lifecycle/report/by-type  ────────────────────────────────────────────
@router.get(
    "/report/by-type",
    response_model=List[LifecycleEventResponse],
    summary="Get all events of a specific type (org-wide report)",
)
def report_by_type(
    event_type: str = Query(..., description="e.g. Promotion, Resignation, Transfer"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Useful for HR reports: 'Show me all promotions this quarter',
    'Show all resignations this month', etc.
    """
    return get_all_events_by_type(db, event_type, from_date, to_date)
