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


@router.get("/candidate-sourcing")
def get_candidate_sourcing(
    job_role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Real sourcing breakdown from Application/Job data.

    NOTE on `source`: the Application table has a `source` column, but
    nothing in the current apply-to-job flow actually sets it yet (that
    flow is broken/missing in this upload — see main.py notes), so every
    existing row will show `source = null` until that's fixed and starts
    populating it. This endpoint is real and will start reflecting real
    channel data the moment applications start carrying a source.

    NOTE on cost-per-hire: there is no cost/spend data anywhere in this
    schema (no recruiting-spend or channel-cost table), so this endpoint
    does NOT return a cost metric — fabricating one would be worse than
    omitting it.
    """
    query = db.query(model.models.Application, model.models.Job).join(
        model.models.Job, model.models.Application.job_id == model.models.Job.id
    )
    if job_role:
        query = query.filter(func.lower(func.trim(model.models.Job.title)) == job_role.strip().lower())
    if department:
        query = query.filter(func.lower(func.trim(model.models.Job.department)) == department.strip().lower())

    rows = query.all()

    from collections import defaultdict
    by_source = defaultdict(int)
    by_recruiter = defaultdict(lambda: {"candidates": 0, "hires": 0})
    total_hires = 0

    for app, job in rows:
        by_source[app.source or "Unknown"] += 1
        if job.recruiter_id:
            recruiter = db.get(model.models.User, job.recruiter_id)
            key = recruiter.name if recruiter else f"Recruiter #{job.recruiter_id}"
            by_recruiter[key]["candidates"] += 1
            if app.hired_at:
                by_recruiter[key]["hires"] += 1
        if app.hired_at:
            total_hires += 1

    return {
        "totalApplications": len(rows),
        "totalHires": total_hires,
        "uniqueSources": len([s for s in by_source if s != "Unknown"]),
        "bySource": [{"source": s, "count": c} for s, c in by_source.items()],
        "byRecruiter": [
            {"recruiter": r, "candidates": v["candidates"], "hires": v["hires"]}
            for r, v in by_recruiter.items()
        ],
    }


@router.get("/job-performance")
def get_job_performance(db: Session = Depends(get_db)):
    """
    Real per-job funnel + fill-rate data from Job/Application.
    """
    jobs = db.query(model.models.Job).all()
    result = []
    for job in jobs:
        apps = db.query(model.models.Application).filter(model.models.Application.job_id == job.id).all()
        hires = [a for a in apps if a.hired_at]
        days_open = (datetime.utcnow() - job.created_at).days if getattr(job, "created_at", None) else None
        result.append({
            "jobId": job.id,
            "title": job.title,
            "department": job.department,
            "status": getattr(job, "status", None),
            "applications": len(apps),
            "hires": len(hires),
            "conversionRate": round((len(hires) / len(apps)) * 100, 1) if apps else 0,
            "daysOpen": days_open,
        })
    return result
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


@router.get("/candidate-sourcing")
def get_candidate_sourcing(db: Session = Depends(get_db)):
    """
    Real sourcing-channel breakdown, built from Candidate.source (added
    specifically for this) and Application.stage/hired_at.

    HONEST LIMITATION: `source` only started being captured going forward —
    candidates created before this field existed will show as "Unknown".
    There is also no cost/spend data anywhere in the schema, so a
    "cost per hire" metric is NOT included here — it would have to be
    fabricated, and it isn't.
    """
    candidates = db.query(model.models.Candidate).all()
    total_candidates = len(candidates)

    by_source = {}
    for c in candidates:
        src = c.source or "Unknown"
        by_source.setdefault(src, {"source": src, "totalCandidates": 0, "hired": 0, "interviewed": 0})
        by_source[src]["totalCandidates"] += 1

    apps = (
        db.query(model.models.Application, model.models.Candidate)
        .join(model.models.Candidate, model.models.Application.candidate_id == model.models.Candidate.id)
        .all()
    )
    for app, cand in apps:
        src = cand.source or "Unknown"
        if src not in by_source:
            by_source[src] = {"source": src, "totalCandidates": 0, "hired": 0, "interviewed": 0}
        if app.hired_at:
            by_source[src]["hired"] += 1
        if app.stage and app.stage.lower() not in ("applied",):
            by_source[src]["interviewed"] += 1

    channel_distribution = []
    for src, d in by_source.items():
        conversion = round((d["hired"] / d["totalCandidates"]) * 100, 1) if d["totalCandidates"] else 0
        channel_distribution.append({
            "name": src,
            "count": d["totalCandidates"],
            "percentage": round((d["totalCandidates"] / total_candidates) * 100) if total_candidates else 0,
            "interviewed": d["interviewed"],
            "hired": d["hired"],
            "conversionRate": conversion,
        })
    channel_distribution.sort(key=lambda x: -x["count"])

    # Candidates processed by recruiter — real, via Job.recruiter_id
    recruiter_rows = (
        db.query(model.models.User.name, model.models.Application.stage, model.models.Application.hired_at)
        .join(model.models.Job, model.models.Job.recruiter_id == model.models.User.id)
        .join(model.models.Application, model.models.Application.job_id == model.models.Job.id)
        .all()
    )
    by_recruiter = {}
    for name, stage, hired_at in recruiter_rows:
        by_recruiter.setdefault(name, {"recruiter": name, "candidates": 0, "interviews": 0, "hires": 0})
        by_recruiter[name]["candidates"] += 1
        if stage and stage.lower() not in ("applied",):
            by_recruiter[name]["interviews"] += 1
        if hired_at:
            by_recruiter[name]["hires"] += 1

    return {
        "totalCandidates": total_candidates,
        "uniqueChannels": len(by_source),
        "bestChannel": channel_distribution[0]["name"] if channel_distribution else None,
        "channelDistribution": channel_distribution,
        "recruiterData": list(by_recruiter.values()),
    }


@router.get("/job-performance")
def get_job_performance(db: Session = Depends(get_db)):
    """
    Real per-job funnel stats. Since stages are admin-configurable (see
    routers/pipeline/stages.py), "shortlisted / interviewed / offered"
    buckets are derived from each stage's stage_type (Screening / Interview
    / Decision / Final) rather than hardcoded stage names.
    """
    stage_type_by_name = {
        s.name: (s.stage_type or "Screening")
        for s in db.query(model.models.Stage).all()
    }

    jobs = db.query(model.models.Job).all()
    apps = db.query(model.models.Application).all()
    apps_by_job = {}
    for a in apps:
        apps_by_job.setdefault(a.job_id, []).append(a)

    recruiter_names = {u.id: u.name for u in db.query(model.models.User).all()}

    job_rows = []
    for job in jobs:
        job_apps = apps_by_job.get(job.id, [])
        applications = len(job_apps)
        shortlisted = sum(1 for a in job_apps if stage_type_by_name.get(a.stage) in ("Interview", "Decision", "Final"))
        interviews = sum(1 for a in job_apps if stage_type_by_name.get(a.stage) in ("Interview", "Decision", "Final"))
        offers = sum(1 for a in job_apps if stage_type_by_name.get(a.stage) in ("Decision", "Final"))
        hired_apps = [a for a in job_apps if a.hired_at]
        hires = len(hired_apps)
        avg_days = round(sum((a.hired_at - a.applied_at).days for a in hired_apps) / hires) if hires else None

        job_rows.append({
            "id": job.id,
            "jobRole": job.title,
            "department": job.department,
            "recruiter": recruiter_names.get(job.recruiter_id, "Unassigned"),
            "applications": applications,
            "shortlisted": shortlisted,
            "interviews": interviews,
            "offers": offers,
            "hires": hires,
            "timeToHire": avg_days,
            "datePosted": job.created_at.date().isoformat() if getattr(job, "created_at", None) else None,
        })

    # Real monthly applications trend (last 6 months with any applications)
    from collections import defaultdict
    monthly = defaultdict(int)
    for a in apps:
        monthly[a.applied_at.strftime("%Y-%m")] += 1
    trend = [{"month": m, "applications": c} for m, c in sorted(monthly.items())][-6:]

    # Applications by department (real)
    dept_counts = defaultdict(int)
    for job in jobs:
        dept_counts[job.department or "Unspecified"] += len(apps_by_job.get(job.id, []))
    department_data = [{"name": d, "value": c} for d, c in dept_counts.items()]

    # A couple of real, dynamically-computed observations instead of fixed text
    insights = []
    if job_rows:
        most_apps = max(job_rows, key=lambda j: j["applications"])
        if most_apps["applications"] > 0:
            insights.append(f'{most_apps["jobRole"]} has the most applications ({most_apps["applications"]}).')
        timed = [j for j in job_rows if j["timeToHire"]]
        if timed:
            slowest = max(timed, key=lambda j: j["timeToHire"])
            insights.append(f'{slowest["jobRole"]} has the longest average time-to-hire ({slowest["timeToHire"]} days).')

    return {
        "jobs": job_rows,
        "trend": trend,
        "departmentData": department_data,
        "insights": insights,
    }