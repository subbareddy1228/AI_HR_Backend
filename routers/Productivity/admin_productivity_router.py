from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict

from core.database import get_db
from services.Productivity.admin_productivity_service import get_org_summary, get_team_summary, get_department_summary
from schema.Productivity.admin_schemas import OrgSummary
from core.dependencies import require_roles

router = APIRouter(prefix="/admin/productivity")

@router.get("/overview", response_model=OrgSummary)
def overview(db: Session = Depends(get_db), _=Depends(require_roles(["superadmin", "admin"]))):
    return get_org_summary(db)

@router.get("/team/{team_id}")
def team_summary(team_id: int, db: Session = Depends(get_db), _=Depends(require_roles(["superadmin", "admin"]))):
    return get_team_summary(db, team_id)

@router.get("/department/{department_id}")
def department_summary(department_id: int, db: Session = Depends(get_db), _=Depends(require_roles(["superadmin", "admin"]))):
    return get_department_summary(db, department_id)