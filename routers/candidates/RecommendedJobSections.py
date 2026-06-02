from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from schema import schemas
import model.models

router = APIRouter(
    prefix="/recommended-jobs",
    tags=["RecommendedJobSections"],
)


# =====================================================
# CREATE RECOMMENDED JOB
# =====================================================
@router.post("/", response_model=schemas.RecommendedJobSections)
async def create_recommended_job(
    job: schemas.RecommendedJobSectionsCreate,
    db: AsyncSession = Depends(get_db),
):
    db_job = RecommendedJobSections(
        title=job.title,
        company=job.company,
        location=job.location,
    )

    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)

    return db_job


# =====================================================
# READ RECOMMENDED JOBS
# =====================================================
@router.get("/", response_model=list[schemas.RecommendedJobSections])
async def read_recommended_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RecommendedJobSections))
    return result.scalars().all()


# =====================================================
# DELETE RECOMMENDED JOB
# =====================================================
@router.delete("/{job_id}", status_code=204)
async def delete_recommended_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RecommendedJobSections).where(RecommendedJobSections.id == job_id)
    )
    job = result.scalars().first()

    if not job:
        raise HTTPException(status_code=404, detail="Recommended job not found")

    await db.delete(job)
    await db.commit()
