from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict

from core.database import get_db
from model.Productivity.activity import ProductivityActivity

router = APIRouter(prefix="/analytics")




@router.get("/employee/{employee_id}")
def employee_analytics(
    employee_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict:
    query = db.query(ProductivityActivity).filter(ProductivityActivity.employee_id == employee_id)
    
    if start:
        start_dt = datetime.fromisoformat(start)
        query = query.filter(ProductivityActivity.timestamp >= start_dt)
    if end:
        end_dt = datetime.fromisoformat(end)
        query = query.filter(ProductivityActivity.timestamp <= end_dt)
    
    activities = query.all()
    
    activities_by_type = {}
    for act in activities:
        activities_by_type[act.activity_type] = activities_by_type.get(act.activity_type, 0) + 1
    
    return {
        "employee_id": employee_id,
        "total_activities": len(activities),
        "activities_by_type": activities_by_type
    }




@router.get("/team/{team_id}")
def team_analytics(
    team_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict:
    query = db.query(ProductivityActivity).filter(ProductivityActivity.team_id == team_id)
    
    if start:
        start_dt = datetime.fromisoformat(start)
        query = query.filter(ProductivityActivity.timestamp >= start_dt)
    if end:
        end_dt = datetime.fromisoformat(end)
        query = query.filter(ProductivityActivity.timestamp <= end_dt)
    
    activities = query.all()
    
    activities_by_type = {}
    for act in activities:
        activities_by_type[act.activity_type] = activities_by_type.get(act.activity_type, 0) + 1
    
    return {
        "team_id": team_id,
        "total_activities": len(activities),
        "activities_by_type": activities_by_type
    }



@router.get("/department/{department_id}")
def department_analytics(
    department_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict:
    query = db.query(ProductivityActivity).filter(ProductivityActivity.department_id == department_id)
    
    if start:
        start_dt = datetime.fromisoformat(start)
        query = query.filter(ProductivityActivity.timestamp >= start_dt)
    if end:
        end_dt = datetime.fromisoformat(end)
        query = query.filter(ProductivityActivity.timestamp <= end_dt)
    
    activities = query.all()
    
    activities_by_type = {}
    for act in activities:
        activities_by_type[act.activity_type] = activities_by_type.get(act.activity_type, 0) + 1
    
    return {
        "department_id": department_id,
        "total_activities": len(activities),
        "activities_by_type": activities_by_type
    }
