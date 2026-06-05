# app/services/admin_productivity_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict

from model.Productivity.productivity import Productivity
from model.Productivity.employee import Employee

def get_org_summary(db: Session) -> Dict:
    avg_score = db.query(func.avg(Productivity.score)).scalar() or 0.0
    total_tasks = db.query(func.sum(Productivity.tasks_completed)).scalar() or 0
    avg_hours = db.query(func.avg(Productivity.hours_logged)).scalar() or 0.0
    return {
        "average_productivity_score": round(float(avg_score), 2),
        "total_tasks_completed": int(total_tasks),
        "average_hours_logged": round(float(avg_hours), 2),
    }

def get_team_summary(db: Session, team_id: int) -> Dict:
    avg_score = db.query(func.avg(Productivity.score)).filter(Productivity.team_id == team_id).scalar() or 0.0
    total_tasks = db.query(func.sum(Productivity.tasks_completed)).filter(Productivity.team_id == team_id).scalar() or 0
    avg_hours = db.query(func.avg(Productivity.hours_logged)).filter(Productivity.team_id == team_id).scalar() or 0.0
    return {
        "team_id": team_id,
        "average_productivity_score": round(float(avg_score), 2),
        "total_tasks_completed": int(total_tasks),
        "average_hours_logged": round(float(avg_hours), 2),
    }

def get_department_summary(db: Session, department_id: int) -> Dict:
    avg_score = db.query(func.avg(Productivity.score)).filter(Productivity.department_id == department_id).scalar() or 0.0
    total_tasks = db.query(func.sum(Productivity.tasks_completed)).filter(Productivity.department_id == department_id).scalar() or 0
    avg_hours = db.query(func.avg(Productivity.hours_logged)).filter(Productivity.department_id == department_id).scalar() or 0.0
    return {
        "department_id": department_id,
        "average_productivity_score": round(float(avg_score), 2),
        "total_tasks_completed": int(total_tasks),
        "average_hours_logged": round(float(avg_hours), 2),
    }
