from fastapi import APIRouter, Query, Depends, HTTPException, status
from datetime import datetime, timezone
from typing import List, Optional
from datetime import date, datetime, time
from sqlalchemy.orm import Session, joinedload
from core.database import get_db
from model.Productivity.activity import ProductivityActivity, AppSession
from model.onboarding.employee import Employee
from schema.Productivity.activity import (
    AppOpen,
    AppClose,
    ActivityOpen,
    ActivityClose,
    ActivityUpdate,
    ActivityResponse,
)
from core.dependencies import get_current_user, require_roles

router = APIRouter(tags=["ProductivityActivity & App Sessions"])



# APP SESSIONS


@router.post("/sessions/open", status_code=status.HTTP_201_CREATED)
def open_app_session(
    data: AppOpen,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    session = AppSession(
        employee_id=current_user.id,
        app_name=data.app_name,
        category=data.category,
        priority=data.priority,
        path=data.path,
        cpu_usage=data.cpu_usage,
        memory_usage=data.memory_usage,
        threads=data.threads,
        opened_at=datetime.now(timezone.utc),
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {"status": "opened", "session_id": session.id}


@router.post("/sessions/close")
def close_app_session(
    data: AppClose,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    session = (
        db.query(AppSession)
        .filter(
            AppSession.app_name == data.app_name,
            AppSession.employee_id == current_user.id,
            AppSession.closed_at.is_(None)
        )
        .order_by(AppSession.opened_at.desc())
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Open session not found")

    session.closed_at = datetime.now(timezone.utc)
    session.duration_seconds = int(
        (session.closed_at - session.opened_at).total_seconds()
    )

    db.commit()

    return {
        "status": "closed",
        "duration_seconds": session.duration_seconds
    }

@router.get("/admin/monitoring")
def admin_grouped_monitoring(
    page: int = Query(1, ge=1),
    limit: int = Query(15, le=50),
    employee_id: int | None = None,
    target_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _: object = Depends(require_roles("Admin")),
):
    offset = (page - 1) * limit

    # 🔹 Default to today
    if target_date is None:
        target_date = date.today()

    #  UTC-AWARE date range (FIX)
    start_of_day = datetime.combine(
        target_date, time.min, tzinfo=timezone.utc
    )
    end_of_day = datetime.combine(
        target_date, time.max, tzinfo=timezone.utc
    )

    query = (
        db.query(Employee)
        .options(
            joinedload(Employee.app_sessions),
            joinedload(Employee.activities),
        )
        .filter(Employee.is_active == True)
    )

    if employee_id:
        query = query.filter(Employee.id == employee_id)

    employees = (
        query
        .order_by(Employee.id.desc())
        .offset(offset)
        .limit(limit + 1)
        .all()
    )

    has_more = len(employees) > limit
    employees = employees[:limit]

    items = []

    for emp in employees:
        apps = [
            {
                "id": s.id,
                "app_name": s.app_name,
                "category": s.category,
                "priority": s.priority,
                "cpu_usage": s.cpu_usage,
                "memory_usage": s.memory_usage,
                "threads": s.threads,
                "opened_at": s.opened_at,
                "closed_at": s.closed_at,
                "duration_seconds": s.duration_seconds,
                "is_running": s.closed_at is None,
            }
            for s in sorted(emp.app_sessions, key=lambda x: x.opened_at, reverse=True)
            if (
                s.opened_at <= end_of_day
                and (s.closed_at is None or s.closed_at >= start_of_day)
            )
        ][:10]

        activities = [
            {
                "id": a.id,
                "activity_type": a.activity_type,
                "description": a.description,
                "productive": a.productive,
                "start_at": a.start_at,
                "end_at": a.end_at,
                "duration_seconds": a.duration_seconds,
                "is_active": a.end_at is None,
            }
            for a in sorted(emp.activities, key=lambda x: x.start_at, reverse=True)
            if (
                a.start_at <= end_of_day
                and (a.end_at is None or a.end_at >= start_of_day)
            )
        ][:10]

        items.append({
            "employee_id": emp.id,
            "name": f"{emp.first_name} {emp.last_name or ''}".strip(),
            "email": emp.email,
            "profile_picture": emp.profile_picture,
            "apps": apps,
            "activities": activities,
        })

    if not items:
        has_more = False

    return {
        "items": items,
        "hasMore": has_more,
        "page": page,
        "limit": limit,
        "date": target_date.isoformat(),
    }

# ACTIVITIES


@router.post("/activities/open", response_model=ActivityResponse)
def open_activity(
    data: ActivityOpen,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    ProductivityActivity = ProductivityActivity(
        employee_id=current_user.id,
        department_id=current_user.department_id,
        team_id=current_user.team_id,
        activity_type=data.activity_type,
        description=data.description,
        activity_metadata=data.activity_metadata,
        productive=data.productive,
        start_at=datetime.now(timezone.utc),
    )

    db.add(ProductivityActivity)
    db.commit()
    db.refresh(ProductivityActivity)
    return ProductivityActivity


@router.post("/activities/close", response_model=ActivityResponse)
def close_activity(
    data: ActivityClose,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    ProductivityActivity = (
        db.query(ProductivityActivity)
        .filter(
            ProductivityActivity.id == data.activity_id,
            ProductivityActivity.employee_id == current_user.id,
            ProductivityActivity.end_at.is_(None)
        )
        .first()
    )

    if not ProductivityActivity:
        raise HTTPException(status_code=404, detail="Open ProductivityActivity not found")

    ProductivityActivity.end_at = datetime.now(timezone.utc)
    ProductivityActivity.duration_seconds = int(
        (ProductivityActivity.end_at - ProductivityActivity.start_at).total_seconds()
    )

    db.commit()
    db.refresh(ProductivityActivity)
    return ProductivityActivity


@router.put("/activities/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: int,
    data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    ProductivityActivity = (
        db.query(ProductivityActivity)
        .filter(
            ProductivityActivity.id == activity_id,
            ProductivityActivity.employee_id == current_user.id
        )
        .first()
    )

    if not ProductivityActivity:
        raise HTTPException(status_code=404, detail="ProductivityActivity not found")

    if ProductivityActivity.end_at is None:
        raise HTTPException(
            status_code=400,
            detail="Cannot update an active ProductivityActivity"
        )

    if data.activity_type is not None:
        ProductivityActivity.activity_type = data.activity_type
    if data.description is not None:
        ProductivityActivity.description = data.description
    if data.productive is not None:
        ProductivityActivity.productive = data.productive

    ProductivityActivity.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(ProductivityActivity)
    return ProductivityActivity
