
from sqlmodel import Session, select
from model.models import Job, Candidate
from typing import List

def create_job(db: Session, job_data: dict, recruiter_id: int) -> Job:
    job = Job(**job_data, recruiter_id=recruiter_id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def get_jobs(db: Session, recruiter_id: int = None, status: str = None, title: str = None, location: str = None) -> List[Job]:
    query = select(Job)
    if recruiter_id:
        query = query.where(Job.recruiter_id == recruiter_id)
    if status:
        query = query.where(Job.status == status)
    if title:
        query = query.where(Job.title.contains(title))
    if location:
        query = query.where(Job.location.contains(location))
    return db.exec(query).all()

def update_job_status(db: Session, job_id: int, status: str) -> Job:
    job = db.get(Job, job_id)
    if job:
        job.status = status
        db.add(job)
        db.commit()
        db.refresh(job)
    return job

def bulk_delete_jobs(db: Session, job_ids: List[int]):
    for job_id in job_ids:
        job = db.get(Job, job_id)
        if job:
            db.delete(job)
    db.commit()
