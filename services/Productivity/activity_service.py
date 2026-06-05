# app/services/activity_service.py

from typing import List, Optional
from datetime import datetime

# Async imports
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Sync imports
from sqlalchemy.orm import Session

from utils.productivity.logger import get_logger
logger = get_logger(__name__)

from model.Productivity.activity import Activity
from schema.Productivity.activity import ActivityCreate



async def create_activity(db: AsyncSession, act_in: ActivityCreate) -> Activity:
    """Create a new activity record (async)."""
    logger.info(f"Creating activity for employee_id={act_in.employee_id}, type={act_in.activity_type}, duration={act_in.duration_seconds}")
    act = Activity(
        employee_id=act_in.employee_id,
        activity_type=act_in.activity_type,
        name=act_in.name,
        start_at=act_in.start_at,
        end_at=act_in.end_at,
        duration_seconds=act_in.duration_seconds,
        metadata=act_in.metadata,
    )
    db.add(act)
    await db.flush()
    logger.info(f"Created activity id={act.id} successfully")
    return act

async def list_activities(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Activity]:
    """List all activities with pagination (async)."""
    q = await db.execute(select(Activity).offset(skip).limit(limit))
    return q.scalars().all()

async def list_activities_by_employee(
    db: AsyncSession,
    employee_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None
) -> List[Activity]:
    """Get activities for a specific employee within an optional date range (async)."""
    logger.info(f"Fetching activities for employee_id={employee_id}, start={start}, end={end}")
    stmt = select(Activity).where(Activity.employee_id == employee_id)

    if start:
        start_dt = datetime.fromisoformat(start)
        stmt = stmt.where(Activity.start_at >= start_dt)
    if end:
        end_dt = datetime.fromisoformat(end)
        stmt = stmt.where(Activity.end_at <= end_dt)

    q = await db.execute(stmt.order_by(Activity.start_at.desc()))
    activities = q.scalars().all()
    logger.info(f"Retrieved {len(activities)} activities for employee_id={employee_id}")
    return activities


def log_activity(db: Session, activity: ActivityCreate) -> Activity:
    """Record employee activity (sync)."""
    logger.info(f"Logging activity type={activity.activity_type} for employee_id={activity.employee_id}")
    db_activity = Activity(**activity.dict())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    logger.info(f"Logged activity id={db_activity.id}")
    return db_activity
