# FILE 11 of 12 | routers/Employee_Management/employee_lifecycle.py
# Router: Employee Lifecycle — prefix: /lifecycle
# Includes inline model: EmployeeLifecycleEvent (table: employee_lifecycle_events)
# Endpoints: POST /  GET /{employee_id}  GET /event/{event_id}  DELETE /event/{event_id}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, select
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime

from core.database import Base, get_db


# Inline model definition
class EmployeeLifecycleEvent(Base):
    __tablename__ = "employee_lifecycle_events"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, nullable=False)
    event_type = Column(String(100))  # Promotion, Transfer, Confirmation, Resignation, Termination
    event_date = Column(Date)
    from_value = Column(String(255), nullable=True)   # e.g. previous designation
    to_value = Column(String(255), nullable=True)     # e.g. new designation
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Inline schemas
class LifecycleEventCreate(BaseModel):
    employee_id: int
    event_type: str
    event_date: date
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    remarks: Optional[str] = None


class LifecycleEventResponse(BaseModel):
    id: int
    employee_id: int
    event_type: str
    event_date: Optional[date] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/lifecycle", tags=["Employee Management"])


@router.post("/", response_model=LifecycleEventResponse, status_code=status.HTTP_201_CREATED)
def log_lifecycle_event(payload: LifecycleEventCreate, db: Session = Depends(get_db)):
    obj = EmployeeLifecycleEvent(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{employee_id}", response_model=list[LifecycleEventResponse])
def get_employee_lifecycle(employee_id: int, db: Session = Depends(get_db)):
    events = db.execute(
        select(EmployeeLifecycleEvent).where(
            EmployeeLifecycleEvent.employee_id == employee_id
        )
    ).scalars().all()
    return events


@router.get("/event/{event_id}", response_model=LifecycleEventResponse)
def get_lifecycle_event(event_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(EmployeeLifecycleEvent).where(EmployeeLifecycleEvent.id == event_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Lifecycle event not found")
    return obj


@router.delete("/event/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lifecycle_event(event_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(EmployeeLifecycleEvent).where(EmployeeLifecycleEvent.id == event_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Lifecycle event not found")
    db.delete(obj)
    db.commit()
