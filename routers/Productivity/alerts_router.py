from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from schema.Productivity.alert import AlertCreate, AlertRead, AlertUpdate
from core.database import get_db
from services.Productivity.alert_service import (
    create_alert,
    list_alerts,
    get_alert,
    update_alert,
    dismiss_alert,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
def create(a: AlertCreate, db: Session = Depends(get_db)):
    alert = create_alert(db, a)

    employee_name = (
        f"{alert.employee.first_name} {alert.employee.last_name or ''}".strip()
        if alert.employee
        else None
    )

    return {**alert.__dict__, "employee_name": employee_name}


@router.get("/", response_model=List[AlertRead])
def read_all(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = 50,
    db: Session = Depends(get_db),
):
    alerts = list_alerts(db, status=status, priority=priority, limit=limit)

    result = []
    for a in alerts:
        result.append({
            "id": a.id,
            "employee_id": a.employee_id,
            "title": a.title,
            "description": a.description,
            "priority": a.priority.value,
            "status": a.status.value,
            "occurred_at": a.occurred_at,
            "created_at": a.created_at,
            "employee_name": getattr(a, "employee_name", None)
        })

    return result


@router.get("/{alert_id}", response_model=AlertRead)
def read_one(alert_id: int, db: Session = Depends(get_db)):
    a = get_alert(db, alert_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    employee_name = (
        f"{a.employee.first_name} {a.employee.last_name or ''}".strip()
        if a.employee
        else None
    )

    return {**a.__dict__, "employee_name": employee_name}


@router.patch("/{alert_id}", response_model=AlertRead)
def patch_alert(alert_id: int, payload: AlertUpdate, db: Session = Depends(get_db)):
    a = update_alert(db, alert_id, payload)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.commit()
    db.refresh(a)

    employee_name = (
        f"{a.employee.first_name} {a.employee.last_name or ''}".strip()
        if a.employee
        else None
    )

    return {**a.__dict__, "employee_name": employee_name}


@router.post("/{alert_id}/dismiss", status_code=status.HTTP_200_OK)
def post_dismiss(alert_id: int, db: Session = Depends(get_db)):
    ok = dismiss_alert(db, alert_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.commit()

    return {"status": "dismissed"}
