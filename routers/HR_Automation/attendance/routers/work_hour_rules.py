from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from core.database import get_db
from schema.HR_Automation.work_hour_rule import (
    WorkHourRuleCreate,
    WorkHourRuleUpdate,
    WorkHourRuleResponse,
    AttendanceStatsResponse,
    OvertimeStatsResponse,
    StorageUsageResponse,
)
from services.HR_Automation import work_hour_rule_service as service

router = APIRouter(prefix="/work-hour-rules", tags=["Work Hour Rules"])


@router.post("/", response_model=WorkHourRuleResponse, status_code=201)
def create_rule(payload: WorkHourRuleCreate, db: Session = Depends(get_db)):
    return service.create_rule(db, payload)


@router.get("/", response_model=List[WorkHourRuleResponse])
def list_rules(active_only: bool = True, db: Session = Depends(get_db)):
    return service.list_rules(db, active_only=active_only)


@router.get("/active", response_model=WorkHourRuleResponse)
def get_active_policy(db: Session = Depends(get_db)):

    return service.get_active_policy(db)


@router.get("/{rule_id}", response_model=WorkHourRuleResponse)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    return service.get_rule(db, rule_id)


@router.patch("/{rule_id}", response_model=WorkHourRuleResponse)
def update_rule(rule_id: int, payload: WorkHourRuleUpdate, db: Session = Depends(get_db)):
    return service.update_rule(db, rule_id, payload)


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    return service.delete_rule(db, rule_id)


@router.patch("/{rule_id}/attendance", response_model=WorkHourRuleResponse)
def update_attendance_tab(
    rule_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
   
    return service.update_attendance_tab(db, rule_id, payload)


@router.patch("/{rule_id}/overtime", response_model=WorkHourRuleResponse)
def update_overtime_tab(
    rule_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
   
    return service.update_overtime_tab(db, rule_id, payload)


@router.patch("/{rule_id}/breaks", response_model=WorkHourRuleResponse)
def update_breaks_tab(
    rule_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):

    return service.update_breaks_tab(db, rule_id, payload)


@router.patch("/{rule_id}/settings", response_model=WorkHourRuleResponse)
def update_settings_tab(
    rule_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
   
    return service.update_settings_tab(db, rule_id, payload)


@router.get("/stats/attendance", response_model=AttendanceStatsResponse)
def get_attendance_stats(rule_id: Optional[int] = None, db: Session = Depends(get_db)):
  
    return service.get_attendance_stats(db, rule_id)


@router.get("/stats/overtime", response_model=OvertimeStatsResponse)
def get_overtime_stats(rule_id: Optional[int] = None, db: Session = Depends(get_db)):

    return service.get_overtime_stats(db, rule_id)


@router.get("/stats/storage", response_model=StorageUsageResponse)
def get_storage_usage(db: Session = Depends(get_db)):

    return service.get_storage_usage(db)
