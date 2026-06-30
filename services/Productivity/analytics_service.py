from sqlalchemy.orm import Session
from collections import defaultdict

from model.Productivity.activity import ProductivityActivity

from model.onboarding.employee import Employee


from model.Employee_Management.org_hierarchy import Department, Team


def calculate_employee_productivity(db: Session, employee_id: int):
    activities = db.query(ProductivityActivity).filter(
        ProductivityActivity.employee_id == employee_id
    ).all()

    total = len(activities)
    productive_count = sum(1 for a in activities if a.productive == "Yes")
    score = round((productive_count / total) * 100, 2) if total else 0

    bottlenecks = defaultdict(int)
    for a in activities:
        if a.productive == "No":
            key = a.app_name or "Unknown"
            bottlenecks[key] += 1

    return {"score": score, "bottlenecks": dict(bottlenecks)}


def calculate_team_productivity(db: Session, team_id: int):
    activities = db.query(ProductivityActivity).filter(
        ProductivityActivity.team_id == team_id
    ).distinct(ProductivityActivity.employee_id).all()

    employee_ids = list({a.employee_id for a in activities})

    team_scores = []
    bottlenecks = defaultdict(int)

    for emp_id in employee_ids:
        result = calculate_employee_productivity(db, emp_id)
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