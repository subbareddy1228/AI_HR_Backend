from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from schema import schemas
import model.models

router = APIRouter(prefix="/notifications", tags=["Notifications"])



@router.post("/", response_model=schemas.Notifications)
async def create_notification(
    notification: schemas.NotificationsCreate,
    db: AsyncSession = Depends(get_db),
):
    notif = Notifications(
        message=notification.message,
        is_read=notification.is_read,
    )

    db.add(notif)
    await db.commit()
    await db.refresh(notif)

    return notif



@router.get("/", response_model=list[schemas.Notifications])
async def read_notifications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notifications))
    return result.scalars().all()



@router.put("/{notif_id}", response_model=schemas.Notifications)
async def mark_as_read(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notifications).where(Notifications.id == notif_id)
    )
    notif = result.scalars().first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = 1
    await db.commit()
    await db.refresh(notif)

    return notif
