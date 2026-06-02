from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database import get_db
from schema import schemas
from model.models import (
    Application,
    Candidate,
    CandidateRecord,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


# =====================================================
# CREATE APPLICATION
# =====================================================
@router.post("/", response_model=schemas.Applications)
async def create_application(
    application: schemas.ApplicationsCreate,
    db: AsyncSession = Depends(get_db),
):
    db_app = Applications(
        job_title=application.job_title,
        company=application.company,
        status=application.status,
        applied_days_ago=application.applied_days_ago,
    )

    db.add(db_app)
    await db.commit()
    await db.refresh(db_app)
    return db_app


# =====================================================
# READ APPLICATIONS (PIPELINE VIEW)
# =====================================================
@router.get("/")
async def read_applications(db: AsyncSession = Depends(get_db)):
    email_to_record: dict[str, dict] = {}

    try:
        # ---------------------------------------------
        # Applications + Candidate
        # ---------------------------------------------
        stmt = (
            select(Application)
            .options(selectinload(Application.candidate))
        )
        result = await db.execute(stmt)
        applications = result.scalars().all()

        for app in applications:
            email = app.candidate_email.lower() if app.candidate_email else None
            if not email:
                continue

            candidate_stage = app.candidate.stage if app.candidate else "Applied"

            email_to_record[email] = {
                "id": app.id,
                "applicationId": app.id,
                "candidate_id": app.candidate_id,
                "candidate_name": app.candidate_name,
                "candidate_email": app.candidate_email,
                "job_id": app.job_id,
                "status": app.stage or "Applied",
                "candidate_stage": candidate_stage,
                "stage": app.stage or "Applied",
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                "role": app.candidate.role if app.candidate else "Not specified",
                "skills": app.candidate.skills if app.candidate else "",
                "resume_url": app.candidate.resume_url if app.candidate else None,
                "source": "application",
            }

        # ---------------------------------------------
        # Candidate table (fallback)
        # ---------------------------------------------
        result = await db.execute(select(Candidate))
        candidates = result.scalars().all()

        for candidate in candidates:
            email = candidate.email.lower() if candidate.email else None
            if email and email not in email_to_record:
                stage = candidate.stage or "Applied"
                email_to_record[email] = {
                    "id": f"candidate_{candidate.id}",
                    "applicationId": None,
                    "candidate_id": candidate.id,
                    "candidate_name": candidate.name,
                    "candidate_email": candidate.email,
                    "job_id": None,
                    "status": stage,
                    "candidate_stage": stage,
                    "stage": stage,
                    "applied_at": None,
                    "role": candidate.role or "Not specified",
                    "skills": candidate.skills or "",
                    "resume_url": candidate.resume_url,
                    "source": "candidate",
                }

        # ---------------------------------------------
        # CandidateRecord (HIGHEST PRIORITY)
        # ---------------------------------------------
        result = await db.execute(select(CandidateRecord))
        records = result.scalars().all()

        for record in records:
            email = record.candidate_email.lower() if record.candidate_email else None
            if email:
                stage = record.stage or "Applied"
                email_to_record[email] = {
                    "id": f"candidate_record_{record.id}",
                    "applicationId": None,
                    "candidate_id": None,
                    "candidate_name": record.candidate_name,
                    "candidate_email": record.candidate_email,
                    "job_id": None,
                    "status": stage,
                    "candidate_stage": stage,
                    "stage": stage,
                    "applied_at": record.created_at.isoformat() if record.created_at else None,
                    "role": record.role or "Not specified",
                    "skills": record.candidate_skills or "",
                    "resume_url": None,
                    "source": "candidate_record",
                }

        return list(email_to_record.values())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# DELETE APPLICATION
# =====================================================
@router.delete("/{app_id}", status_code=204)
async def delete_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Applications).where(Applications.id == app_id)
    )
    app = result.scalars().first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    await db.delete(app)
    await db.commit()
