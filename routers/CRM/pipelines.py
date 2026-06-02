# app/routers/pipelines.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from schema.pipeline import PipelineCreate, PipelineResponse, PipelineUpdate
import model
from core.database import get_db
import crud_ops

router = APIRouter()


@router.post("/", response_model=PipelineResponse)
def create_pipeline(pipeline: PipelineCreate, db: Session = Depends(get_db)):
    db_pipeline = crud_ops.create_pipeline(db=db, pipeline=pipeline)
    return db_pipeline


@router.get("/", response_model=List[PipelineResponse])
def read_pipelines(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Note: get_pipelines doesn't support pagination, so we get all and paginate manually
    all_pipelines = crud_ops.get_pipelines(db)
    return all_pipelines[skip:skip + limit]


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def read_pipeline(pipeline_id: int, db: Session = Depends(get_db)):
    pipeline = crud_ops.get_pipeline(db, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


@router.put("/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(pipeline_id: int, pipeline: PipelineUpdate, db: Session = Depends(get_db)):
    updated = crud_ops.update_pipeline(db, pipeline_id, pipeline)
    if not updated:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return updated


@router.delete("/{pipeline_id}")
def delete_pipeline(pipeline_id: int, db: Session = Depends(get_db)):
    success = crud_ops.delete_pipeline(db, pipeline_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"ok": True}
