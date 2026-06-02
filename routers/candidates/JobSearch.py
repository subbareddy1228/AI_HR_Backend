from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from schema import schemas
import model.models

router = APIRouter(prefix="/job-search", tags=["JobSearch"])


# =====================================================
# CREATE JOB SEARCH
# =====================================================
@router.post("/", response_model=schemas.JobSearch)
async def create_jobsearch(
    job: schemas.JobSearchCreate,
    db: AsyncSession = Depends(get_db),
):
    db_job = JobSearch(
        title=job.title,
        company=job.company,
        location=job.location,
    )

    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)

    return db_job


# =====================================================
# READ JOB SEARCH LIST
# =====================================================
@router.get("/", response_model=list[schemas.JobSearch])
async def read_jobsearch(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobSearch))
    return result.scalars().all()


# =====================================================
# DELETE JOB SEARCH
# =====================================================
@router.delete("/{job_id}", status_code=204)
async def delete_jobsearch(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobSearch).where(JobSearch.id == job_id)
    )
    job = result.scalars().first()

    if not job:
        raise HTTPException(status_code=404, detail="JobSearch item not found")

    await db.delete(job)
    await db.commit()
