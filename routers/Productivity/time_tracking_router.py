from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from utils.productivity.logger import get_logger

from core.database import get_db
from core.dependencies import get_current_user
from services.Productivity.time_tracking_services import (
    get_time_tracking_overview,
    get_time_entries,
   
)

logger = get_logger(__name__)

router = APIRouter(prefix="/time-tracking")


@router.get("/overview")
def overview(
    period: str = Query("today"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    logger.info(f"Time tracking overview request for user_id={user.id}, period={period}")
    result = get_time_tracking_overview(db, user, period)
    logger.info(f"Time tracking overview returned for user_id={user.id}")
    return result


@router.get("/entries")
def entries(
    period: str = Query("today"),
    project_id: int | None = None,
    db: Session = Depends(get_db),
):
    logger.info(f"Time tracking entries request: period={period}, project_id={project_id}")
    result = get_time_entries(db, period, project_id)
    logger.info(f"Returned {len(result)} time entries")
    return result



