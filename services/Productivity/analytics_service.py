from sqlalchemy.orm import Session
from model.Productivity.ProductivityActivity import ProductivityActivity
from model.onboarding.employee import Employee
from model.Employee_Management.org_hierarchy import Department
from datetime import datetime
from collections import defaultdict

def calculate_employee_productivity(db: Session, employee_id: int):
    activities = db.query(ProductivityActivity).filter(ProductivityActivity.employee_id == employee_id).all()
    total = len(activities)
    productive_count = sum(1 for a in activities if a.productive == "Yes")
    score = round((productive_count / total) * 100, 2) if total else 0
    # Bottleneck detection
    bottlenecks = defaultdict(int)
    for a in activities:
        if a.productive == "No":
            key = a.app_name or a.website_url
            bottlenecks[key] += 1
    return {"score": score, "bottlenecks": dict(bottlenecks)}

def calculate_team_productivity(db: Session, team_id: int):
    employees = db.query(Employee).filter(Employee.team_id == team_id).all()
    team_scores = []
    bottlenecks = defaultdict(int)
    for emp in employees:
        result = calculate_employee_productivity(db, emp.id)
        team_scores.append(result["score"])
        for k, v in result["bottlenecks"].items():
            bottlenecks[k] += v
    avg_score = round(sum(team_scores) / len(team_scores), 2) if team_scores else 0
    return {"team_score": avg_score, "bottlenecks": dict(bottlenecks)}

def calculate_department_productivity(db: Session, department_id: int):
    teams = db.query(Team).filter(Team.department_id == department_id).all()
    dept_scores = []
    bottlenecks = defaultdict(int)
    for team in teams:
        result = calculate_team_productivity(db, team.id)
        dept_scores.append(result["team_score"])
        for k, v in result["bottlenecks"].items():
            bottlenecks[k] += v
    avg_score = round(sum(dept_scores) / len(dept_scores), 2) if dept_scores else 0
    return {"department_score": avg_score, "bottlenecks": dict(bottlenecks)}
