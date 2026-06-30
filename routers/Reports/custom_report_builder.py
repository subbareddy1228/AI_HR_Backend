from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime

from core.database import get_db
from model.Reports.saved_report import (
    ReportFeature, SavedReport,
    FeatureStatus, FeatureCategory,
)
from schema.Reports.saved_report import (
    ReportFeatureCreate, ReportFeatureUpdate, ReportFeatureResponse,
    SavedReportCreate,   SavedReportUpdate,   SavedReportResponse,
)

router = APIRouter(prefix="/custom", tags=["Custom Report Builder"])

@router.get("/features/kpi")
def get_feature_kpi(db: Session = Depends(get_db)):
    total = (
        db.execute(select(func.count(ReportFeature.id))
                   .where(ReportFeature.is_active == True))
        .scalar() or 0
    )
    published = (
        db.execute(select(func.count(ReportFeature.id))
                   .where(ReportFeature.is_active == True,
                          ReportFeature.status == FeatureStatus.published))
        .scalar() or 0
    )
    in_progress = (
        db.execute(select(func.count(ReportFeature.id))
                   .where(ReportFeature.is_active == True,
                          ReportFeature.status == FeatureStatus.in_progress))
        .scalar() or 0
    )
    scheduled = (
        db.execute(select(func.count(ReportFeature.id))
                   .where(ReportFeature.is_active == True,
                          ReportFeature.status == FeatureStatus.scheduled))
        .scalar() or 0
    )
    return {
        "totalFeatures": total,
        "published":     published,
        "inProgress":    in_progress,
        "scheduled":     scheduled,
    }

@router.get("/features")
def list_features(
    db:       Session = Depends(get_db),
    search:   Optional[str]            = Query(None),
    category: Optional[FeatureCategory]= Query(None),
    status:   Optional[FeatureStatus]  = Query(None),
    page:     int = Query(1, ge=1),
    per_page: int = Query(8, ge=1, le=100),
):
    q = select(ReportFeature).where(ReportFeature.is_active == True)

    if search:
        q = q.where(ReportFeature.feature_name.ilike(f"%{search}%"))
    if category:
        q = q.where(ReportFeature.category == category)
    if status:
        q = q.where(ReportFeature.status == status)

    q = q.order_by(ReportFeature.updated_at.desc())

    total   = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    offset  = (page - 1) * per_page
    records = db.execute(q.offset(offset).limit(per_page)).scalars().all()

    return {
        "total":    total,
        "page":     page,
        "perPage":  per_page,
        "totalPages": (total + per_page - 1) // per_page,
        "showing":  f"{offset + 1}-{min(offset + per_page, total)} of {total}",
        "data": [
            {
                "id":          r.id,
                "featureName": r.feature_name,
                "description": r.description,
                "icon":        r.icon,
                "category":    r.category.value,
                "status":      r.status.value,
                "lastUpdated": r.updated_at.strftime("%Y-%m-%d") if r.updated_at else None,
                "createdBy":   r.created_by,
            }
            for r in records
        ],
    }


@router.get("/features/{feature_id}", response_model=ReportFeatureResponse)
def get_feature(feature_id: int, db: Session = Depends(get_db)):
    feature = db.execute(
        select(ReportFeature).where(ReportFeature.id == feature_id)
    ).scalars().first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature


@router.post("/features", response_model=ReportFeatureResponse, status_code=201)
def create_feature(payload: ReportFeatureCreate, db: Session = Depends(get_db)):
    feature = ReportFeature(**payload.model_dump())
    db.add(feature)
    db.commit()
    db.refresh(feature)
    return feature


@router.put("/features/{feature_id}", response_model=ReportFeatureResponse)
def update_feature(
    feature_id: int,
    payload:    ReportFeatureUpdate,
    db:         Session = Depends(get_db),
):
    feature = db.execute(
        select(ReportFeature).where(ReportFeature.id == feature_id,
                                    ReportFeature.is_active == True)
    ).scalars().first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(feature, field, value)
    feature.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(feature)
    return feature


@router.patch("/features/{feature_id}/status")
def update_feature_status(
    feature_id: int,
    status:     FeatureStatus,
    db:         Session = Depends(get_db),
):
    feature = db.execute(
        select(ReportFeature).where(ReportFeature.id == feature_id,
                                    ReportFeature.is_active == True)
    ).scalars().first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    feature.status     = status
    feature.updated_at = datetime.utcnow()
    db.commit()
    return {
        "id":     feature_id,
        "status": status.value,
        "message": f"Status updated to '{status.value}'",
    }

@router.delete("/features/{feature_id}")
def delete_feature(feature_id: int, db: Session = Depends(get_db)):
    feature = db.execute(
        select(ReportFeature).where(ReportFeature.id == feature_id)
    ).scalars().first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    feature.is_active  = False
    feature.updated_at = datetime.utcnow()
    db.commit()
    return {
        "message": f"Feature '{feature.feature_name}' deleted",
        "id":      feature_id,
    }


@router.get("/saved")
def list_saved_reports(db: Session = Depends(get_db)):
    reports = db.execute(
        select(SavedReport).where(SavedReport.is_active == True)
                           .order_by(SavedReport.updated_at.desc())
    ).scalars().all()
    return {
        "count": len(reports),
        "data": [
            {
                "id":          r.id,
                "reportName":  r.report_name,
                "reportType":  r.report_type,
                "createdBy":   r.created_by,
                "createdAt":   str(r.created_at),
                "updatedAt":   str(r.updated_at),
            }
            for r in reports
        ],
    }


@router.get("/saved/{report_id}", response_model=SavedReportResponse)
def get_saved_report(report_id: int, db: Session = Depends(get_db)):
    report = db.execute(
        select(SavedReport).where(SavedReport.id == report_id)
    ).scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/saved", response_model=SavedReportResponse, status_code=201)
def create_saved_report(payload: SavedReportCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(SavedReport).where(SavedReport.report_name == payload.report_name)
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Report name already exists")

    report = SavedReport(**payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.put("/saved/{report_id}", response_model=SavedReportResponse)
def update_saved_report(
    report_id: int,
    payload:   SavedReportUpdate,
    db:        Session = Depends(get_db),
):
    report = db.execute(
        select(SavedReport).where(SavedReport.id == report_id,
                                  SavedReport.is_active == True)
    ).scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(report, field, value)
    report.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(report)
    return report


@router.delete("/saved/{report_id}")
def delete_saved_report(report_id: int, db: Session = Depends(get_db)):
    report = db.execute(
        select(SavedReport).where(SavedReport.id == report_id)
    ).scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.is_active  = False
    report.updated_at = datetime.utcnow()
    db.commit()
    return {"message": f"Report '{report.report_name}' deleted", "id": report_id}


@router.post("/saved/{report_id}/run")
def run_saved_report(report_id: int, db: Session = Depends(get_db)):
    report = db.execute(
        select(SavedReport).where(SavedReport.id == report_id,
                                  SavedReport.is_active == True)
    ).scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    route_map = {
        "employee":   "/api/reports/employee/list",
        "attendance": "/api/reports/attendance/monthly-summary",
        "payroll":    "/api/reports/payroll/register",
        "leave":      "/api/reports/leave/monthly-trend",
    }
    rt = (report.report_type or "").lower()

    return {
        "reportId":       report_id,
        "reportName":     report.report_name,
        "reportType":     report.report_type,
        "status":         "queued",
        "dataEndpoint":   route_map.get(rt, "/api/reports/employee/list"),
        "filters":        report.filters          or {},
        "columnsSelected":report.columns_selected or [],
    }
