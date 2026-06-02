from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import model.models
from core.database import get_db
from schema import schemas



router = APIRouter(prefix="/api/pipeline/stages", tags=["Pipeline"])


@router.get("/", response_model=List[schemas.StageOut])
def list_stages(db: Session = Depends(get_db)):
    return db.query(model.models.Stage).order_by(model.models.Stage.order.asc()).all()


@router.post("/", response_model=schemas.StageOut, status_code=201)
def create_stage(payload: schemas.StageCreate, db: Session = Depends(get_db)):
    exists = (
        db.query(model.models.Stage)
        .filter(model.models.Stage.name.ilike(payload.name))
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Stage with this name already exists")

    stage = model.models.Stage(name=payload.name, order=payload.order)
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


@router.patch("/{stage_id}", response_model=schemas.StageOut)
def update_stage(stage_id: int, payload: schemas.StageUpdate, db: Session = Depends(get_db)):
    stage = db.get(model.models.Stage, stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    if payload.name is not None:
        stage.name = payload.name
    if payload.order is not None:
        stage.order = payload.order
    db.commit()
    db.refresh(stage)
    return stage


@router.delete("/{stage_id}", status_code=204)
def delete_stage(stage_id: int, db: Session = Depends(get_db)):
    stage = db.get(model.models.Stage, stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    db.delete(stage)
    db.commit()
    return None


