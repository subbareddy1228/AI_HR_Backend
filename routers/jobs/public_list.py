from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from typing import Optional
from model.models import Job
from core.database import get_db

router = APIRouter()


@router.get("/public")
def list_public_jobs(
    search: Optional[str] = Query(None, description="Matches title or department"),
    db: Session = Depends(get_db),
):
    """
    Candidate-facing job listing — no auth required.

    Unlike GET /api/jobs/list (which requires a company/recruiter token and
    only returns that recruiter's own jobs), this returns every job across
    all recruiters that has actually been published, so a logged-in
    candidate can browse and apply.
    """
    statement = select(Job).where(Job.status != "Draft")
    jobs = db.exec(statement).all()

    if search:
        term = search.lower()
        jobs = [
            j for j in jobs
            if term in (j.title or "").lower() or term in (j.department or "").lower()
        ]

    return [
        {
            "id": job.id,
            "title": job.title,
            "department": job.department or "General",
            "employment_type": job.employment_type or "Full-time",
            "location": job.location or "N/A",
            "is_remote": job.is_remote if job.is_remote is not None else False,
            "description": job.description,
            "responsibilities": job.responsibilities or "N/A",
            "requirements": job.requirements or "N/A",
            "salary_min": job.salary_min or 0,
            "salary_max": job.salary_max or 0,
            "currency": job.currency or "USD",
            "benefits": job.benefits or [],
            "skills": job.skills or [],
            "expiry_date": job.expiry_date.isoformat() if job.expiry_date else None,
            "reference_id": job.reference_id or "N/A",
            "status": job.status or "Draft",
            "created_at": job.created_at.isoformat(),
        }
        for job in jobs
    ]
