from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from schema import schemas
import model.models

router = APIRouter(prefix="/recent-applications", tags=["RecentApplications"])


# =====================================================
# CREATE RECENT APPLICATION
# =====================================================
@router.post("/", response_model=schemas.RecentApplications)
async def create_recent_application(
    application: schemas.RecentApplicationsCreate,
    db: AsyncSession = Depends(get_db),
):
    db_app = RecentApplications(
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
# READ RECENT APPLICATIONS
# =====================================================
@router.get("/", response_model=list[schemas.RecentApplications])
async def read_recent_applications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RecentApplications))
    return result.scalars().all()


# =====================================================
# DELETE RECENT APPLICATION
# =====================================================
@router.delete("/{app_id}", status_code=204)
async def delete_recent_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RecentApplications).where(RecentApplications.id == app_id)
    )
    app = result.scalars().first()

    if not app:
        raise HTTPException(status_code=404, detail="Recent application not found")

    await db.delete(app)
    await db.commit()
