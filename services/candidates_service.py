from sqlmodel import Session, select
from model.models import Candidate
from typing import List

def get_candidates(db: Session, job_id: int = None, skills: str = None, stage: str = None) -> List[Candidate]:
    query = select(Candidate)
    if job_id:
        query = query.where(Candidate.job_id == job_id)
    if skills:
        query = query.where(Candidate.skills.contains(skills))
    if stage:
        query = query.where(Candidate.stage == stage)
    return db.exec(query).all()

def update_candidate_stage(db: Session, candidate_id: int, new_stage: str):
    candidate = db.get(Candidate, candidate_id)
    if candidate:
        candidate.stage = new_stage
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
    return candidate

def bulk_assign_candidates(db: Session, candidate_ids: List[int], job_id: int):
    for cid in candidate_ids:
        candidate = db.get(Candidate, cid)
        if candidate:
            candidate.job_id = job_id
            db.add(candidate)
    db.commit()
