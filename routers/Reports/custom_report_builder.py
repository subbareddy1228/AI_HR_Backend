from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.database import get_db

from model.Reports.saved_report import SavedReport
from schema.Reports.saved_report import SavedReportCreate, SavedReportResponse

router = APIRouter(prefix="/custom", tags=["Reports"])


@router.post("/", response_model=SavedReportResponse, status_code=201)
def create_report(payload: SavedReportCreate, db: Session = Depends(get_db)):
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


@router.get("/")
def list_reports(db: Session = Depends(get_db)):
    reports = db.execute(
        select(SavedReport).where(SavedReport.is_active == True)
    ).scalars().all()
    return {
        "count": len(reports),
        "data": [
            {
                "id": r.id,
                "report_name": r.report_name,
                "report_type": r.report_type,
                "created_by": r.created_by,
                "created_at": str(r.created_at),
            }
            for r in reports
        ],
    }


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.execute(
        select(SavedReport).where(SavedReport.id == report_id)
    ).scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": report.id,
        "report_name": report.report_name,
        "report_type": report.report_type,
        "filters": report.filters,
        "columns_selected": report.columns_selected,
        "created_by": report.created_by,
        "is_active": report.is_active,
        "created_at": str(report.created_at),
    }


@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.execute(
        select(SavedReport).where(SavedReport.id == report_id)
    ).scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.is_active = False
    db.commit()
    return {"message": f"Report '{report.report_name}' deleted successfully", "id": report_id}


@router.post("/{report_id}/run")
def run_report(report_id: int, db: Session = Depends(get_db)):
    report = db.execute(
        select(SavedReport).where(SavedReport.id == report_id, SavedReport.is_active == True)
    ).scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report_type = (report.report_type or "").lower()
    filters = report.filters or {}

    if report_type == "employee":
        message = "Employee report queued — query employees table with applied filters."
    elif report_type == "attendance":
        message = "Attendance report queued — query attendance_records with applied filters."
    elif report_type == "payroll":
        message = "Payroll report queued — query payroll_runs / payroll_run_details with applied filters."
    elif report_type == "leave":
        message = "Leave report queued — query leave_requests with applied filters."
    else:
        message = f"Report of type '{report.report_type}' queued with applied filters."

    return {
        "report_id": report_id,
        "report_name": report.report_name,
        "report_type": report.report_type,
        "status": "queued",
        "message": message,
        "filters": filters,
        "columns_selected": report.columns_selected,
    }