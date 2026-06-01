from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from model.HR_Automation.work_hour_rule import WorkHourRule
from schema.HR_Automation.work_hour_rule import (
    WorkHourRuleCreate,
    WorkHourRuleUpdate,
    WorkHourRuleResponse,
)

router = APIRouter(prefix="/work-hour-rules", tags=["Work Hour Rules"])


@router.post("/", response_model=WorkHourRuleResponse, status_code=201)
def create_rule(payload: WorkHourRuleCreate, db: Session = Depends(get_db)):
    existing = db.query(WorkHourRule).filter(WorkHourRule.rule_name == payload.rule_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Rule name already exists")
    rule = WorkHourRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/", response_model=List[WorkHourRuleResponse])
def list_rules(db: Session = Depends(get_db)):
    return db.query(WorkHourRule).filter(WorkHourRule.is_active == True).all()


@router.get("/{rule_id}", response_model=WorkHourRuleResponse)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(WorkHourRule).filter(WorkHourRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Work hour rule not found")
    return rule


@router.patch("/{rule_id}", response_model=WorkHourRuleResponse)
def update_rule(rule_id: int, payload: WorkHourRuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(WorkHourRule).filter(WorkHourRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Work hour rule not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(WorkHourRule).filter(WorkHourRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Work hour rule not found")
    db.delete(rule)
    db.commit()
    return {"message": "Work hour rule deleted successfully"}
