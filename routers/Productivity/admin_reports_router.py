# app/routers/admin_reports_router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from services.Productivity.admin_reports_service import generate_productivity_report
from core.dependencies import require_roles
from schema.Productivity.admin_schemas import ReportRequest

router = APIRouter(prefix="/admin/reports", tags=["Admin Reports"])

@router.post("/productivity/export")
def export_productivity(req: ReportRequest, db: Session = Depends(get_db), _=Depends(require_roles("Admin"))):
    # Optionally use req fields to filter
    scope = {}
    if req.employee_id: scope["employee_id"] = req.employee_id
    if req.team_id: scope["team_id"] = req.team_id
    if req.department_id: scope["department_id"] = req.department_id

    try:
        # generated_by: could be current user id, but we allow None here
        path = generate_productivity_report(db, generated_by=None, scope=scope)
        return FileResponse(path, filename=path.split("/")[-1])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
