from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sqlalchemy.orm import Session

from utils.productivity.logger import get_logger
logger = get_logger(__name__)

from model.Productivity.activity import ProductivityActivity
from schema.Productivity.activity import ActivityCreate



async def create_activity(db: AsyncSession, act_in: ActivityCreate) -> ProductivityActivity:
   
    logger.info(f"Creating ProductivityActivity for employee_id={act_in.employee_id}, type={act_in.activity_type}, duration={act_in.duration_seconds}")
    act = ProductivityActivity(
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
    logger.info(f"Created ProductivityActivity id={act.id} successfully")
    return act

async def list_activities(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ProductivityActivity]:
    
    q = await db.execute(select(ProductivityActivity).offset(skip).limit(limit))
    return q.scalars().all()

async def list_activities_by_employee(
    db: AsyncSession,
    employee_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None
) -> List[ProductivityActivity]:
  
    logger.info(f"Fetching activities for employee_id={employee_id}, start={start}, end={end}")
    stmt = select(ProductivityActivity).where(ProductivityActivity.employee_id == employee_id)

    if start:
        start_dt = datetime.fromisoformat(start)
        stmt = stmt.where(ProductivityActivity.start_at >= start_dt)
    if end:
        end_dt = datetime.fromisoformat(end)
        stmt = stmt.where(ProductivityActivity.end_at <= end_dt)

    q = await db.execute(stmt.order_by(ProductivityActivity.start_at.desc()))
    activities = q.scalars().all()
    logger.info(f"Retrieved {len(activities)} activities for employee_id={employee_id}")
    return activities


def log_activity(db: Session, activity_data: ActivityCreate) -> ProductivityActivity:
    
    logger.info(f"Logging ProductivityActivity type={ProductivityActivity.activity_type} for employee_id={ProductivityActivity.employee_id}")
    db_activity = ProductivityActivity(**activity_data.model_dump())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    logger.info(f"Logged ProductivityActivity id={db_activity.id}")
    return db_activity
