import os
from datetime import datetime
import pandas as pd

from sqlalchemy.orm import Session
from model.Productivity.productivity import Productivity
from model.Productivity.report_log import ReportLog

DEFAULT_REPORT_DIR = os.getenv("REPORT_DIR", "reports")
os.makedirs(DEFAULT_REPORT_DIR, exist_ok=True)

def generate_productivity_report(db: Session, generated_by: int | None = None, scope: dict | None = None) -> str:
   
    query = db.query(Productivity)
    if scope:
        
        if scope.get("employee_id"):
            query = query.filter(Productivity.employee_id == scope["employee_id"])
        if scope.get("team_id"):
            query = query.filter(Productivity.team_id == scope["team_id"])
        if scope.get("department_id"):
            query = query.filter(Productivity.department_id == scope["department_id"])

    rows = query.all()

    data = []
    for r in rows:
        data.append({
            "id": r.id,
            "employee_id": r.employee_id,
            "department_id": getattr(r, "department_id", None),
            "team_id": getattr(r, "team_id", None),
            "score": getattr(r, "score", None),
            "average_score": getattr(r, "average_score", None),
            "tasks_completed": getattr(r, "tasks_completed", None),
            "hours_logged": getattr(r, "hours_logged", None),
            "period": getattr(r, "period", None),
            "timestamp": getattr(r, "timestamp", None),
            "created_at": getattr(r, "created_at", None),
        })

    df = pd.DataFrame(data)
    filename = f"productivity_report_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.xlsx"
    file_path = os.path.join(DEFAULT_REPORT_DIR, filename)
    df.to_excel(file_path, index=False)

   
    log = ReportLog(report_type="productivity", generated_by=generated_by, file_path=file_path)
    db.add(log)
    db.commit()
    db.refresh(log)
    return file_path
