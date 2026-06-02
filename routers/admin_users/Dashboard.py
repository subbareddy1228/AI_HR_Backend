from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from core.database import get_db
import core.database as database
from model.models import Job, Candidate, User, Application
from schema.schemas import JobCreate, JobRead, CandidateRead
from auth import get_current_user
from datetime import datetime, timedelta

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

#  Role check dependency 
def recruiter_or_admin(user: User = Depends(get_current_user)):
    if user.role.lower() not in ["recruiter", "admin"]:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return user

#  Dashboard Widgets 
@router.get("/widgets")
def dashboard_widgets(user: User = Depends(recruiter_or_admin), db: Session = Depends(get_db)):
    # Count active jobs (status contains "Open" or "Published")
    active_jobs = db.exec(
        select(Job).where(Job.recruiter_id == user.id, Job.status.ilike("%Open%"))
    ).all()

    job_ids = list(db.exec(select(Job.id).where(Job.recruiter_id == user.id)).all())

    if not job_ids:
        return {
            "active_jobs": len(active_jobs),
            "applications_received": 0,
            "candidates_in_pipeline": 0
        }

    # Get all applications for user's jobs
    applications = db.exec(select(Application).where(Application.job_id.in_(job_ids))).all()
    candidate_ids = list(set([app.candidate_id for app in applications if app.candidate_id]))
    
    # Count all applications for user's jobs
    applications_received = len(applications)

    # Count candidates in pipeline (stage not "Hired")
    if candidate_ids:
        candidates_in_pipeline = db.exec(
            select(Candidate).where(Candidate.id.in_(candidate_ids), Candidate.stage != "Hired")
        ).all()
    else:
        candidates_in_pipeline = []

    return {
        "active_jobs": len(active_jobs),
        "applications_received": len(applications_received),
        "candidates_in_pipeline": len(candidates_in_pipeline)
    }

#  Create Job 
@router.post("/jobs", response_model=JobRead)
def create_job(payload: JobCreate, user: User = Depends(recruiter_or_admin), db: Session = Depends(get_db)):
    job = Job(**payload.dict(), recruiter_id=user.id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

#  List Jobs with filters 
@router.get("/jobs", response_model=List[JobRead])
def list_jobs(
    status: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_or_admin)
):
    query = select(Job).where(Job.recruiter_id == user.id)

    if status:
        query = query.where(Job.status.ilike(f"%{status.strip()}%"))
    if title:
        query = query.where(Job.title.ilike(f"%{title.strip()}%"))
    if location:
        query = query.where(Job.location.ilike(f"%{location.strip()}%"))
    if start_date:
        query = query.where(Job.created_at >= start_date)
    if end_date:
        query = query.where(Job.created_at <= end_date)

    return db.exec(query).all()

#  Job Detail 
@router.get("/jobs/{job_id}", response_model=JobRead)
def job_detail(job_id: int, user: User = Depends(recruiter_or_admin), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.recruiter_id != user.id and user.role.lower() != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden")
    return job

#  Bulk Delete Jobs 
@router.delete("/jobs/bulk")
def bulk_delete_jobs(job_ids: List[int], user: User = Depends(recruiter_or_admin), db: Session = Depends(get_db)):
    for job_id in job_ids:
        job = db.get(Job, job_id)
        if job and (job.recruiter_id == user.id or user.role.lower() == "admin"):
            db.delete(job)
    db.commit()
    return {"msg": "Jobs deleted successfully"}

#  Candidates Endpoints 
@router.get("/candidates", response_model=List[CandidateRead])
def list_candidates(
    skills: Optional[str] = Query(None),
    job_id: Optional[int] = None,
    stage: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_or_admin)
):
    # Get all job IDs for the current recruiter (unless admin)
    if user.role.lower() == "admin":
        job_ids = list(db.exec(select(Job.id)).all())
    else:
        job_ids = list(db.exec(select(Job.id).where(Job.recruiter_id == user.id)).all())
    
    if not job_ids:
        return []
    
    # Filter by job_id if provided
    if job_id:
        if job_id not in job_ids and user.role.lower() != "admin":
            raise HTTPException(status_code=403, detail="Access forbidden")
        job_ids = [job_id]
    
    # Get all applications for these jobs
    application_statement = select(Application).where(Application.job_id.in_(job_ids))
    applications = db.exec(application_statement).all()
    candidate_ids = list(set([app.candidate_id for app in applications if app.candidate_id]))
    
    if not candidate_ids:
        return []
    
    # Get candidates for these IDs
    query = select(Candidate).where(Candidate.id.in_(candidate_ids))
    if stage:
        query = query.where(Candidate.stage == stage)
    if skills:
        skill_list = [s.strip() for s in skills.split(",")]
        for skill in skill_list:
            query = query.where(Candidate.skills.contains(skill))
    return db.exec(query).all()

@router.post("/candidates/bulk-assign")
def bulk_assign_candidates(candidate_ids: List[int], job_id: int, user: User = Depends(recruiter_or_admin), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job or (job.recruiter_id != user.id and user.role.lower() != "admin"):
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    # Create or update applications for candidates
    for cid in candidate_ids:
        candidate = db.get(Candidate, cid)
        if candidate:
            # Check if application already exists
            existing_app = db.exec(
                select(Application).where(
                    Application.candidate_id == cid,
                    Application.job_id == job_id
                )
            ).first()
            
            if not existing_app:
                # Create new application
                application = Application(
                    job_id=job_id,
                    candidate_id=cid,
                    candidate_name=candidate.name,
                    candidate_email=candidate.email,
                    stage=candidate.stage or "Applied"
                )
                db.add(application)
    
    db.commit()
    return {"msg": "Candidates assigned to job"}

@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
def candidate_detail(candidate_id: int, user: User = Depends(recruiter_or_admin), db: Session = Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Check if user has access to this candidate through their jobs
    if user.role.lower() != "admin":
        # Get all applications for this candidate
        applications = db.exec(select(Application).where(Application.candidate_id == candidate_id)).all()
        if not applications:
            raise HTTPException(status_code=403, detail="Access forbidden")
        
        # Check if any of the jobs belong to this recruiter
        job_ids = [app.job_id for app in applications]
        recruiter_jobs = db.exec(select(Job.id).where(Job.id.in_(job_ids), Job.recruiter_id == user.id)).all()
        if not recruiter_jobs:
            raise HTTPException(status_code=403, detail="Access forbidden")
    
    return candidate

#  Analytics 
@router.get("/analytics/applications-over-time")
def applications_over_time(days: int = 30, user: User = Depends(recruiter_or_admin), db: Session = Depends(get_db)):
    start_date = datetime.utcnow() - timedelta(days=days)
    job_ids = list(db.exec(select(Job.id).where(Job.recruiter_id == user.id)).all())

    if not job_ids:
        return []

    # Get applications for these jobs
    applications = db.exec(select(Application).where(Application.job_id.in_(job_ids))).all()
    candidate_ids = list(set([app.candidate_id for app in applications if app.candidate_id]))

    if not candidate_ids:
        return []

    query = select(func.date(Candidate.created_at), func.count(Candidate.id)).where(
        Candidate.id.in_(candidate_ids),
        Candidate.created_at >= start_date
    ).group_by(func.date(Candidate.created_at))

    return [{"date": d[0], "count": d[1]} for d in db.exec(query).all()]
