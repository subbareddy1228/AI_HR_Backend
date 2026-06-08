from fastapi import APIRouter, Depends
from typing import Optional, List
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from utils.productivity.logger import get_logger
logger = get_logger(__name__)

from schema.Productivity.productivity import SummaryMetrics, ProductivityOut
from services.Productivity.productivity_service import (
    calculate_employee_productivity,
    get_summary_metrics,
    compute_and_store_productivity,
    get_productivity_by_employee,
)

router = APIRouter(prefix="/productivity")



# Logged-in user's productivity (SYNC)

@router.get("/", response_model=ProductivityOut)
def my_productivity(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    logger.info(f"GET /productivity/ for user_id={user.id}")
    result = calculate_employee_productivity(db, user.id)
    logger.info(f"Productivity calculated for user_id={user.id}, score={result.score}")
    return result



# Summary metrics (ASYNC)

@router.get("/summary", response_model=SummaryMetrics)
def summary(db: Session = Depends(get_db)):
    logger.info("GET /productivity/summary")
    result = get_summary_metrics(db)
    logger.info("Summary metrics retrieved")
    return result



# Recompute productivity (ASYNC)

@router.post("/compute")
def compute(
    period: Optional[str] = None,
    db: Session = Depends(get_db),
):
    logger.info(f"POST /productivity/compute period={period}")
    count = compute_and_store_productivity(db, period)
    db.commit()
    logger.info(f"Computed productivity for {count} employees")
    return {"status": "ok", "computed": count}



# Productivity by employee (ASYNC)

@router.get(
    "/employee/{employee_id}",
    response_model=List[ProductivityOut],
)
def employee_productivity(
    employee_id: int,
    db: Session = Depends(get_db),
):
    logger.info(f"GET /productivity/employee/{employee_id}")
    result = get_productivity_by_employee(db, employee_id)
    logger.info(f"Retrieved {len(result)} productivity records for employee {employee_id}")
    return result
