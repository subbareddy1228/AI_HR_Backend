from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status

from model.Employee_Management.employee_lifecycle import EmployeeLifecycleEvent
from schema.Employee_Management.employee_lifecycle import LifecycleEventCreate


def log_lifecycle_event(db: Session, payload: LifecycleEventCreate) -> EmployeeLifecycleEvent:
    obj = EmployeeLifecycleEvent(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_employee_lifecycle(db: Session, employee_id: int) -> list[EmployeeLifecycleEvent]:
    return db.execute(
        select(EmployeeLifecycleEvent).where(
            EmployeeLifecycleEvent.employee_id == employee_id
        )
    ).scalars().all()


def get_lifecycle_event(db: Session, event_id: int) -> EmployeeLifecycleEvent:
    obj = db.execute(
        select(EmployeeLifecycleEvent).where(EmployeeLifecycleEvent.id == event_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lifecycle event not found")
    return obj


def delete_lifecycle_event(db: Session, event_id: int) -> None:
    obj = get_lifecycle_event(db, event_id)
    db.delete(obj)
    db.commit()