from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from core.database import get_db

from model.Productivity.employee_score import EmployeeProductivity
from schema.Productivity.employee_score import (
    EmployeeProductivityCreate, EmployeeProductivityUpdate, EmployeeProductivityResponse
)

router = APIRouter(prefix="/employee-scores", tags=["Productivity"])


@router.post("/", response_model=EmployeeProductivityResponse, status_code=status.HTTP_201_CREATED)
def create_score(payload: EmployeeProductivityCreate, db: Session = Depends(get_db)):
    score = EmployeeProductivity(**payload.model_dump())
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


@router.get("/", response_model=list[EmployeeProductivityResponse])
def list_scores(
    department: Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    period:     Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(EmployeeProductivity)
    if department:
        query = query.filter(EmployeeProductivity.department == department)
    if status:
        query = query.filter(EmployeeProductivity.status == status)
    if period:
        query = query.filter(EmployeeProductivity.period == period)
    return query.order_by(EmployeeProductivity.score.desc()).all()


@router.get("/top-performers")
def top_performers(limit: int = Query(5, ge=1, le=50), db: Session = Depends(get_db)):
    """Top N employees by score — used by Productivity Dashboard leaderboard."""
    return db.query(EmployeeProductivity)\
        .order_by(EmployeeProductivity.score.desc())\
        .limit(limit).all()


@router.get("/dept-summary")
def dept_summary(db: Session = Depends(get_db)):
    """Average score per department — used by Reports page dept table."""
    rows = db.query(
        EmployeeProductivity.department,
        func.avg(EmployeeProductivity.score).label("avg_score"),
        func.count(EmployeeProductivity.id).label("headcount"),
        func.avg(EmployeeProductivity.avg_hours).label("avg_hours"),
        func.avg(
            (EmployeeProductivity.tasks_completed * 100.0) / 
            func.nullif(EmployeeProductivity.tasks_assigned, 0)
        ).label("task_rate"),
    ).group_by(EmployeeProductivity.department).all()
    return [
        {
            "department": r.department,
            "avg_score": round(r.avg_score or 0, 1),
            "headcount": r.headcount,
            "avg_hours": round(r.avg_hours or 0, 1),
            "task_rate": round(r.task_rate or 0, 1),
        }
        for r in rows
    ]


@router.get("/overview-stats")
def overview_stats(db: Session = Depends(get_db)):
    """Company-wide stats — used by Productivity Dashboard stat cards."""
    total    = db.query(func.count(EmployeeProductivity.id)).scalar() or 0
    avg_score = db.query(func.avg(EmployeeProductivity.score)).scalar() or 0
    avg_hours = db.query(func.avg(EmployeeProductivity.avg_hours)).scalar() or 0
    total_tasks     = db.query(func.sum(EmployeeProductivity.tasks_assigned)).scalar() or 0
    completed_tasks = db.query(func.sum(EmployeeProductivity.tasks_completed)).scalar() or 0
    excellent = db.query(func.count(EmployeeProductivity.id)).filter(EmployeeProductivity.status == "excellent").scalar() or 0
    needs_imp = db.query(func.count(EmployeeProductivity.id)).filter(EmployeeProductivity.status == "needs-improvement").scalar() or 0

    return {
        "total_employees": total,
        "avg_productivity_score": round(avg_score, 1),
        "avg_daily_hours": round(avg_hours, 1),
        "total_tasks_assigned": total_tasks,
        "total_tasks_completed": completed_tasks,
        "task_completion_rate": round((completed_tasks / total_tasks * 100) if total_tasks else 0, 1),
        "excellent_count": excellent,
        "needs_improvement_count": needs_imp,
    }


@router.get("/{score_id}", response_model=EmployeeProductivityResponse)
def get_score(score_id: int, db: Session = Depends(get_db)):
    score = db.query(EmployeeProductivity).filter(EmployeeProductivity.id == score_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Record not found")
    return score


@router.patch("/{score_id}", response_model=EmployeeProductivityResponse)
def update_score(score_id: int, payload: EmployeeProductivityUpdate, db: Session = Depends(get_db)):
    score = db.query(EmployeeProductivity).filter(EmployeeProductivity.id == score_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Record not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(score, key, value)
    db.commit()
    db.refresh(score)
    return score


@router.delete("/{score_id}")
def delete_score(score_id: int, db: Session = Depends(get_db)):
    score = db.query(EmployeeProductivity).filter(EmployeeProductivity.id == score_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(score)
    db.commit()
    return {"message": "Record deleted successfully"}
