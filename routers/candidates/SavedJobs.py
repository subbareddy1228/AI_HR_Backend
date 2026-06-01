from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from schema import schemas
from model.models import SavedJob

router = APIRouter(prefix="/saved-jobs", tags=["SavedJobs"])


# =====================================================
# CREATE SAVED JOB
# =====================================================
@router.post("/", response_model=schemas.SavedJobs)
async def create_saved_job(
    job: schemas.SavedJobsCreate,
    db: AsyncSession = Depends(get_db),
):
    db_job = SavedJob(
        title=job.title,
        company=job.company,
        location=job.location,
    )

    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)

    return db_job


# =====================================================
# READ SAVED JOBS
# =====================================================
@router.get("/", response_model=list[schemas.SavedJobs])
async def read_saved_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SavedJob))
    return result.scalars().all()


# =====================================================
# DELETE SAVED JOB
# =====================================================
@router.delete("/{job_id}", status_code=204)
async def delete_saved_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedJob).where(SavedJob.id == job_id)
    )
    job = result.scalars().first()

    if not job:
        raise HTTPException(status_code=404, detail="Saved job not found")

    await db.delete(job)
    await db.commit()
