from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from schema import schemas
import model.models

router = APIRouter(prefix="/profile", tags=["Profile"])


# =====================================================
# READ PROFILE
# =====================================================
@router.get("/", response_model=schemas.Profile)
async def read_profile(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Profile))
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile


# =====================================================
# CREATE PROFILE
# =====================================================
@router.post("/", response_model=schemas.Profile)
async def create_profile(
    profile: schemas.Profile,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile))
    existing = result.scalars().first()

    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists")

    db_profile = Profile(
        name=profile.name,
        role=profile.role,
        profile_image_url=profile.profile_image_url,
    )

    db.add(db_profile)
    await db.commit()
    await db.refresh(db_profile)

    return db_profile
