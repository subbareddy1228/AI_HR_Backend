from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime

from model.Productivity.alert import Alert, AlertPriority, AlertStatus
from schema.Productivity.alert import AlertCreate, AlertUpdate


def create_alert(db: Session, payload: AlertCreate) -> Alert:
    alert = Alert(
        employee_id=payload.employee_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=AlertStatus.active,
        occurred_at=payload.occurred_at or datetime.utcnow()
    )
    db.add(alert)
    db.flush()
    db.commit()
    db.refresh(alert)
    return alert


def list_alerts(
    db: Session,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
) -> List[Alert]:

    query = db.query(Alert)

    #  filters FIRST
    if status:
        query = query.filter(Alert.status == status)

    if priority:
        query = query.filter(Alert.priority == priority)

    #  ordering
    query = query.order_by(Alert.created_at.desc())

    #  pagination LAST
    query = query.limit(limit)

    alerts = query.all()

    # enrich response (safe)
    for a in alerts:
        if a.employee:
            a.employee_name = (
                f"{a.employee.first_name} {a.employee.last_name or ''}".strip()
            )
        else:
            a.employee_name = None

    return alerts

def get_alert(db: Session, alert_id: int) -> Optional[Alert]:
    return db.query(Alert).filter(Alert.id == alert_id).first()


def update_alert(db: Session, alert_id: int, payload: AlertUpdate) -> Optional[Alert]:
    alert = get_alert(db, alert_id)
    if not alert:
        return None

    for key, value in payload.dict(exclude_unset=True).items():
        setattr(alert, key, value)

    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def dismiss_alert(db: Session, alert_id: int) -> bool:
    alert = get_alert(db, alert_id)
    if not alert:
        return False

    alert.status = AlertStatus.dismissed
    db.add(alert)
    db.commit()
    return True


def stats_summary(db: Session) -> dict:
    total_active = db.query(func.count()).filter(Alert.status == AlertStatus.active).scalar() or 0
    critical = db.query(func.count()).filter(Alert.priority == AlertPriority.critical).scalar() or 0
    warnings = db.query(func.count()).filter(Alert.priority == AlertPriority.warning).scalar() or 0
    info = db.query(func.count()).filter(Alert.priority == AlertPriority.info).scalar() or 0
    success = db.query(func.count()).filter(Alert.priority == AlertPriority.success).scalar() or 0

    return {
        "total_active": total_active,
        "critical": critical,
        "warning": warnings,
        "info": info,
        "success": success,
    }
