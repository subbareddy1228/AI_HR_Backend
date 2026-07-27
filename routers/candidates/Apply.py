from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from core.database import get_db
from model.models import Job, Application, Candidate
from .auth import get_current_candidate

router = APIRouter(tags=["Candidate Apply"])


@router.post("/{job_id}", status_code=201)
def apply_to_job(
    job_id: int,
    db: Session = Depends(get_db),
    candidate: Candidate = Depends(get_current_candidate),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == "Draft":
        raise HTTPException(status_code=404, detail="Job not found")

    existing = db.exec(
        select(Application).where(
            Application.job_id == job_id,
            Application.candidate_id == candidate.id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="You have already applied to this job")

    application = Application(
        job_id=job_id,
        candidate_id=candidate.id,
        candidate_name=candidate.name,
        candidate_email=candidate.email,
        stage="Applied",
        source="Career Page",
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return {
        "message": "Application submitted successfully",
        "application_id": application.id,
        "job_id": job_id,
        "candidate_id": candidate.id,
        "stage": application.stage,
    }
