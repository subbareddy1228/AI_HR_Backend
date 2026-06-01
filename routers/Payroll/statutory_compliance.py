# FILE 15 of 18 | routers/Payroll/statutory_compliance.py
# Router: Statutory Compliance — prefix: /statutory  (mounted under /api/payroll in main.py)
# Endpoints:
#   GET  /statutory/     — get current config (first record or 404)
#   POST /statutory/     — create config
#   PUT  /statutory/{id} — update config

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

from core.database import get_db
from model.Payroll.statutory_compliance import StatutoryConfig
from schema.Payroll.statutory_compliance import (
    StatutoryConfigCreate,
    StatutoryConfigUpdate,
    StatutoryConfigResponse,
)

router = APIRouter(prefix="/statutory", tags=["Payroll"])


@router.get("/", response_model=StatutoryConfigResponse)
def get_statutory_config(db: Session = Depends(get_db)):
    obj = db.execute(select(StatutoryConfig)).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="No statutory configuration found. Please create one.")
    return obj


@router.post("/", response_model=StatutoryConfigResponse, status_code=status.HTTP_201_CREATED)
def create_statutory_config(payload: StatutoryConfigCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(StatutoryConfig).where(StatutoryConfig.config_name == (payload.config_name or "default"))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Statutory config '{payload.config_name}' already exists. Use PUT to update.",
        )
    obj = StatutoryConfig(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{config_id}", response_model=StatutoryConfigResponse)
def update_statutory_config(
    config_id: int, payload: StatutoryConfigUpdate, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(StatutoryConfig).where(StatutoryConfig.id == config_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Statutory config not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj
