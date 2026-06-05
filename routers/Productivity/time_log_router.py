from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from core.database import get_db

from model.Productivity.time_log import TimeLog
from schema.Productivity.time_log import TimeLogCreate, TimeLogUpdate, TimeLogResponse

router = APIRouter(prefix="/time-logs", tags=["Productivity"])


@router.post("/", response_model=TimeLogResponse, status_code=status.HTTP_201_CREATED)
def create_log(payload: TimeLogCreate, db: Session = Depends(get_db)):
    log = TimeLog(**payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/", response_model=list[TimeLogResponse])
def list_logs(
    employee:  Optional[str] = Query(None),
    project:   Optional[str] = Query(None),
    log_date:  Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(TimeLog)
    if employee:
        query = query.filter(TimeLog.employee == employee)
    if project:
        query = query.filter(TimeLog.project == project)
    if log_date:
        query = query.filter(TimeLog.log_date == log_date)
    return query.order_by(TimeLog.created_at.desc()).all()


@router.get("/summary/by-project")
def hours_by_project(db: Session = Depends(get_db)):
    """Total hours grouped by project — used by Time Tracking page bar chart."""
    rows = db.query(
        TimeLog.project,
        func.sum(TimeLog.hours).label("total_hours")
    ).group_by(TimeLog.project).order_by(func.sum(TimeLog.hours).desc()).all()
    return [{"project": r.project, "total_hours": round(r.total_hours, 2)} for r in rows]


@router.get("/summary/by-employee")
def hours_by_employee(db: Session = Depends(get_db)):
    """Total hours grouped by employee."""
    rows = db.query(
        TimeLog.employee,
        func.sum(TimeLog.hours).label("total_hours")
    ).group_by(TimeLog.employee).order_by(func.sum(TimeLog.hours).desc()).all()
    return [{"employee": r.employee, "total_hours": round(r.total_hours, 2)} for r in rows]


@router.get("/{log_id}", response_model=TimeLogResponse)
def get_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(TimeLog).filter(TimeLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Time log not found")
    return log


@router.patch("/{log_id}", response_model=TimeLogResponse)
def update_log(log_id: int, payload: TimeLogUpdate, db: Session = Depends(get_db)):
    log = db.query(TimeLog).filter(TimeLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Time log not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(log, key, value)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/{log_id}")
def delete_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(TimeLog).filter(TimeLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Time log not found")
    db.delete(log)
    db.commit()
    return {"message": "Time log deleted successfully"}
