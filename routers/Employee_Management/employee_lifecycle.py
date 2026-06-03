from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from schema.Employee_Management.employee_lifecycle import LifecycleEventCreate, LifecycleEventResponse
from services.Employee_Management.employee_lifecycle_service import (
    log_lifecycle_event,
    get_employee_lifecycle,
    get_lifecycle_event,
    delete_lifecycle_event,
)

router = APIRouter(prefix="/lifecycle", tags=["Employee Management"])


@router.post("/", response_model=LifecycleEventResponse, status_code=status.HTTP_201_CREATED)
def log_lifecycle_event_route(payload: LifecycleEventCreate, db: Session = Depends(get_db)):
    return log_lifecycle_event(db, payload)


@router.get("/{employee_id}", response_model=list[LifecycleEventResponse])
def get_employee_lifecycle_route(employee_id: int, db: Session = Depends(get_db)):
    return get_employee_lifecycle(db, employee_id)


@router.get("/event/{event_id}", response_model=LifecycleEventResponse)
def get_lifecycle_event_route(event_id: int, db: Session = Depends(get_db)):
    return get_lifecycle_event(db, event_id)


@router.delete("/event/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lifecycle_event_route(event_id: int, db: Session = Depends(get_db)):
    delete_lifecycle_event(db, event_id)