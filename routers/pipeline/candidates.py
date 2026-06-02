from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import model.models
from core.database import get_db
from schema import schemas
from core.dependencies import get_current_user
from model.models import User, Job, Application
from sqlmodel import select


router = APIRouter(prefix="/api/pipeline/candidates", tags=["Pipeline"])


@router.get("/", response_model=List[schemas.CandidateOut])
def list_candidates(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Get all job IDs for the current recruiter (unless admin)
    if user.role.lower() == "admin":
        job_ids = list(db.exec(select(Job.id)).all())
    else:
        job_ids = list(db.exec(select(Job.id).where(Job.recruiter_id == user.id)).all())
    
    if not job_ids:
        return []
    
    # Get all applications for these jobs
    applications = db.exec(select(Application).where(Application.job_id.in_(job_ids))).all()
    candidate_ids = list(set([app.candidate_id for app in applications if app.candidate_id]))
    
    if not candidate_ids:
        return []
    
    # Get candidates for these IDs
    return db.query(model.models.Candidate).filter(model.models.Candidate.id.in_(candidate_ids)).all()


@router.post("/", response_model=schemas.CandidateOut, status_code=201)
def create_candidate(payload: schemas.CandidateCreate, db: Session = Depends(get_db)):
    stage = db.get(model.models.Stage, payload.stage_id)
    if not stage:
        raise HTTPException(status_code=400, detail="Invalid stage_id")
    candidate = model.models.Candidate(
        name=payload.name,
        role=payload.role,
        status=payload.status,
        stage_id=payload.stage_id,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.patch("/{candidate_id}", response_model=schemas.CandidateOut)
def update_candidate(candidate_id: int, payload: schemas.CandidateUpdate, db: Session = Depends(get_db)):
    candidate = db.get(model.models.Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if payload.stage_id is not None:
        stage = db.get(model.models.Stage, payload.stage_id)
        if not stage:
            raise HTTPException(status_code=400, detail="Invalid stage_id")
        candidate.stage_id = payload.stage_id
    if payload.name is not None:
        candidate.name = payload.name
    if payload.role is not None:
        candidate.role = payload.role
    if payload.status is not None:
        candidate.status = payload.status
    db.commit()
    db.refresh(candidate)
    return candidate


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.get(model.models.Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.delete(candidate)
    db.commit()
    return None


