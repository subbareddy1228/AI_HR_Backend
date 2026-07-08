from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional  
import model.models
from core.database import get_db
from .utils import parse_date_str

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/kpis")
def get_kpis(
    role: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),   
    expiryDate: Optional[str] = Query(None),   
    db: Session = Depends(get_db)
):
    
    start = parse_date_str(start_date)
    end = parse_date_str(expiryDate)

    
    job_query = db.query(model.models.Job).filter(model.models.Job.status.in_(["active", "Draft"]))

    if role:
        role_clean = role.strip().lower()
        job_query = job_query.filter(func.lower(func.trim(model.models.Job.role)) == role_clean)
    
    if end:
        job_query = job_query.filter(model.models.Job.expiry_date <= end)

    active_jobs = job_query.count()

    
    app_query = db.query(model.models.Application).join(model.models.Job)\
        .filter(model.models.Job.status.in_(["active", "Draft"]))

    if role:
        app_query = app_query.filter(func.lower(func.trim(model.models.Job.role)) == role_clean)
    if start:
        app_query = app_query.filter(model.models.Application.applied_at >= start)
    if end:
        app_query = app_query.filter(model.models.Application.applied_at <= end)

    total_applications = app_query.count()

    
    week_start = datetime.utcnow() - timedelta(days=7)
    month_start = datetime(datetime.utcnow().year, datetime.utcnow().month, 1)

    applications_this_week = app_query.filter(model.models.Application.applied_at >= week_start).count()
    applications_this_month = app_query.filter(model.models.Application.applied_at >= month_start).count()

   
    time_to_hire = db.query(
        func.avg(
            func.extract("epoch", model.models.Application.hired_at - model.models.Application.applied_at) / 86400.0
        )
    ).filter(model.models.Application.hired_at.isnot(None)).scalar()

    
    stage_counts = db.query(model.models.Application.stage, func.count(model.models.Application.id))\
        .group_by(model.models.Application.stage).all()
    stage_data = {s: c for s, c in stage_counts}

    return {
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "applications_this_week": applications_this_week,
        "applications_this_month": applications_this_month,
        "avg_time_to_hire_days": round(time_to_hire, 2) if time_to_hire else None,
        "applications_by_stage": stage_data
    }


@router.get("/time-to-hire-detail")
def get_time_to_hire_detail(
    job_role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    recruiter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Real time-to-hire breakdown from Application.applied_at / hired_at.

    NOTE: there is no per-stage timestamp history in the schema (Application
    only has applied_at / hired_at / a single current `stage` field), so a
    genuine "days spent in each stage" breakdown isn't computable — that
    would need a stage-transition audit table. What IS returned instead:
    overall avg/fastest/slowest hire time, a monthly trend, per-role
    averages, and the CURRENT distribution of applications across stages
    (a different but real and useful metric).
    """
    query = (
        db.query(model.models.Application, model.models.Job)
        .join(model.models.Job, model.models.Application.job_id == model.models.Job.id)
        .filter(model.models.Application.hired_at.isnot(None))
    )

    if job_role:
        query = query.filter(func.lower(func.trim(model.models.Job.title)) == job_role.strip().lower())
    if department:
        query = query.filter(func.lower(func.trim(model.models.Job.department)) == department.strip().lower())
    if recruiter:
        query = (
            query.join(model.models.User, model.models.Job.recruiter_id == model.models.User.id)
            .filter(func.lower(model.models.User.name) == recruiter.strip().lower())
        )

    rows = query.all()

    hires = []
    for app, job in rows:
        days = (app.hired_at - app.applied_at).days
        hires.append({
            "candidateName": app.candidate_name,
            "jobRole": job.title,
            "department": job.department,
            "totalDays": days,
            "hiredAt": app.hired_at.isoformat(),
        })

    if not hires:
        return {
            "avgTime": 0,
            "fastest": None,
            "slowest": None,
            "trend": [],
            "byRole": [],
            "jobRoles": [],
            "departments": [],
            "recruiters": [],
            "currentStageDistribution": [],
        }

    avg_time = round(sum(h["totalDays"] for h in hires) / len(hires))
    fastest = min(hires, key=lambda h: h["totalDays"])
    slowest = max(hires, key=lambda h: h["totalDays"])

    # Monthly trend (avg days for hires in each of the last 6 months)
    from collections import defaultdict
    monthly = defaultdict(list)
    for h in hires:
        month_key = h["hiredAt"][:7]  # YYYY-MM
        monthly[month_key].append(h["totalDays"])
    trend = [
        {"month": month, "avgTime": round(sum(days) / len(days))}
        for month, days in sorted(monthly.items())
    ][-6:]

    # Per-role averages
    role_days = defaultdict(list)
    for h in hires:
        role_days[h["jobRole"]].append(h["totalDays"])
    by_role = [
        {"role": role, "avgTime": round(sum(days) / len(days))}
        for role, days in role_days.items()
    ]

    # Filter option lists (drawn from the full unfiltered dataset)
    all_jobs = db.query(model.models.Job.title, model.models.Job.department).distinct().all()
    all_recruiters = db.query(model.models.User.name).join(
        model.models.Job, model.models.Job.recruiter_id == model.models.User.id
    ).distinct().all()

    # Current pipeline stage distribution (real, current — not historical duration)
    stage_counts = (
        db.query(model.models.Application.stage, func.count(model.models.Application.id))
        .group_by(model.models.Application.stage)
        .all()
    )

    return {
        "avgTime": avg_time,
        "fastest": fastest,
        "slowest": slowest,
        "trend": trend,
        "byRole": by_role,
        "jobRoles": sorted({j.title for j in all_jobs}),
        "departments": sorted({j.department for j in all_jobs}),
        "recruiters": sorted({r.name for r in all_recruiters}),
        "currentStageDistribution": [{"stage": s, "count": c} for s, c in stage_counts],
    }