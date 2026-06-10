from typing import List, Optional
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from utils.productivity.logger import get_logger
logger = get_logger(__name__)

from model.onboarding.employee import Employee
from model.Productivity.productivity import Productivity
from model.Productivity.activity import ProductivityActivity
from schema.Productivity.productivity import SummaryMetrics





def get_summary_metrics(db: Session):
    logger.info("Computing summary metrics")
    overall_score = db.execute(
        select(func.avg(Productivity.score))
    ).scalar() or 0

    logger.info(f"Summary computed: score={overall_score:.2f}")
    return {
        "overall_score": float(overall_score),
        "average_hours": 0.0,
        "tasks_completed": 0,
    }


def compute_and_store_productivity(
    db: Session,
    period: Optional[str] = None,
) -> int:
    logger.info(f"Computing productivity for period={period or 'today'}, all employees")
    if not period:
        period = str(date.today())

    result = db.execute(select(Employee))
    employees = result.scalars().all()
    logger.debug(f"Found {len(employees)} employees for productivity computation")

    count = 0
    for e in employees:
        record = Productivity(
            employee_id=e.id,
            department_id=None,
            team_id=None,
            period=period,
            average_score=e.productivity_score or 0.0,
            tasks_completed=e.tasks_completed or 0,
            hours_logged=e.hours_logged or 0.0,
        )
        db.add(record)
        count += 1

    db.flush()   #  sync
    logger.info(f"Stored productivity records for {count} employees")
    return count

def get_productivity_by_employee(
    db: Session,
    employee_id: int,
) -> List[Productivity]:
    result = db.execute(
        select(Productivity)
        .where(Productivity.employee_id == employee_id)
        .order_by(Productivity.created_at.desc())
    )
    return result.scalars().all()





def calculate_employee_productivity(
    db: Session,
    employee_id: int,
) -> Productivity:
    logger.info(f"Calculating productivity for employee_id={employee_id}")
    activities = (
        db.query(ProductivityActivity)
        .filter(ProductivityActivity.employee_id == employee_id)
        .all()
    )

    total = len(activities)
    productive_count = sum(
        1 for a in activities if getattr(a, "productive", "Yes") == "Yes"
    )

    score = round((productive_count / total) * 100, 2) if total else 0.0
    logger.info(f"Productivity score for emp {employee_id}: {score}% from {total} activities ({productive_count} productive)")

    emp = db.query(Employee).get(employee_id)

    record = Productivity(
    employee_id=employee_id,
    department_id=None, 
    team_id=None,
    score=score,
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    logger.debug(f"Saved productivity record id={record.id} for emp {employee_id}")
    return record
