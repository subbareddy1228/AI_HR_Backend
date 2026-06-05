from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
from core.database import get_db

from model.Productivity.okr import Objective, KeyResult
from schema.Productivity.okr import (
    ObjectiveCreate, ObjectiveUpdate, ObjectiveResponse,
    KeyResultCreate, KeyResultUpdate, KeyResultResponse,
)

router = APIRouter(prefix="/okrs", tags=["Productivity"])


# ── Objectives ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=ObjectiveResponse, status_code=status.HTTP_201_CREATED)
def create_objective(payload: ObjectiveCreate, db: Session = Depends(get_db)):
    obj = Objective(
        objective=payload.objective,
        owner=payload.owner,
        quarter=payload.quarter,
        status=payload.status,
        progress=payload.progress,
    )
    db.add(obj)
    db.flush()
    for kr in payload.key_results:
        db.add(KeyResult(objective_id=obj.id, **kr.model_dump()))
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/", response_model=list[ObjectiveResponse])
def list_objectives(
    status: Optional[str] = Query(None),
    owner:  Optional[str] = Query(None),
    quarter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = select(Objective)
    if status:
        q = q.where(Objective.status == status)
    if owner:
        q = q.where(Objective.owner == owner)
    if quarter:
        q = q.where(Objective.quarter == quarter)
    return db.execute(q).scalars().all()


@router.get("/{objective_id}", response_model=ObjectiveResponse)
def get_objective(objective_id: int, db: Session = Depends(get_db)):
    obj = db.query(Objective).filter(Objective.id == objective_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    return obj


@router.patch("/{objective_id}", response_model=ObjectiveResponse)
def update_objective(objective_id: int, payload: ObjectiveUpdate, db: Session = Depends(get_db)):
    obj = db.query(Objective).filter(Objective.id == objective_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{objective_id}")
def delete_objective(objective_id: int, db: Session = Depends(get_db)):
    obj = db.query(Objective).filter(Objective.id == objective_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    db.delete(obj)
    db.commit()
    return {"message": "Objective deleted successfully"}


# ── Key Results ────────────────────────────────────────────────────────────────

@router.post("/{objective_id}/key-results", response_model=KeyResultResponse, status_code=status.HTTP_201_CREATED)
def add_key_result(objective_id: int, payload: KeyResultCreate, db: Session = Depends(get_db)):
    obj = db.query(Objective).filter(Objective.id == objective_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    kr = KeyResult(objective_id=objective_id, **payload.model_dump())
    db.add(kr)
    db.commit()
    db.refresh(kr)
    return kr


@router.patch("/{objective_id}/key-results/{kr_id}", response_model=KeyResultResponse)
def update_key_result(objective_id: int, kr_id: int, payload: KeyResultUpdate, db: Session = Depends(get_db)):
    kr = db.query(KeyResult).filter(KeyResult.id == kr_id, KeyResult.objective_id == objective_id).first()
    if not kr:
        raise HTTPException(status_code=404, detail="Key result not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(kr, key, value)
    db.commit()
    db.refresh(kr)
    return kr


@router.delete("/{objective_id}/key-results/{kr_id}")
def delete_key_result(objective_id: int, kr_id: int, db: Session = Depends(get_db)):
    kr = db.query(KeyResult).filter(KeyResult.id == kr_id, KeyResult.objective_id == objective_id).first()
    if not kr:
        raise HTTPException(status_code=404, detail="Key result not found")
    db.delete(kr)
    db.commit()
    return {"message": "Key result deleted successfully"}
