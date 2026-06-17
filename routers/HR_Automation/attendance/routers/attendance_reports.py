"""
routers/attendance_reports.py
FastAPI router — Attendance Reports & Analytics (all 5 tabs).
Prefix : /api/attendance/reports
Auth   : JWT via get_current_user / require_hr_admin
"""

import io
from datetime import date
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    Query, Path,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user

from model.HR_Automation.attendance_reports import ReportTypeEnum, ExceptionTypeEnum
from schema.HR_Automation.attendance_reports import (
    GlobalFilterIn, DashboardOut,
    ReportDefinitionOut, GenerateReportIn, GeneratedReportOut,
    AnalyticsOut,
    ExceptionListOut, ExceptionOut,
    AlertsPageOut, AlertOut, AcknowledgeIn, ConfigureAlertIn,
    MessageResponse,
)
from services.HR_Automation.attendance_reports_service import (
    DashboardService, ReportsService,
    AnalyticsService, ExceptionsService, AlertsService,
    seed_reports_defaults,
)

router = APIRouter(
    prefix="/api/attendance/reports",
    tags=["Attendance Reports & Analytics"],
)


# ══════════════════════════════════════════════════════════
# GLOBAL FILTER OPTIONS  (header dropdowns)
# ══════════════════════════════════════════════════════════

@router.get("/filter-options")
def get_filter_options(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Populates the 4 header dropdowns:
      Period          → This Month | Last Month | Last 3M | Last 6M | This Year | Custom
      All Departments → distinct department values
      All Locations   → distinct location values
      All Employees   → list of {id, name}
    Also returns Manager roles for the top-right role dropdown.
    """
    from sqlalchemy import distinct
    depts, locs, emps = [], [], []
    try:
        from models.employee import Employee
        depts = sorted({
            v for (v,) in db.query(distinct(Employee.department)).all() if v
        })
        locs  = sorted({
            v for (v,) in db.query(distinct(Employee.location)).all() if v
        })
        emps  = [
            {"id": e.employee_id, "name": e.name}
            for e in db.query(Employee).filter_by(status="Active")
                       .order_by(Employee.name).all()
        ]
    except ImportError:
        pass

    return {
        "periods":     ["This Month","Last Month","Last 3M","Last 6M","This Year","Custom"],
        "departments": ["All Departments"] + depts,
        "locations":   ["All Locations"]   + locs,
        "employees":   [{"id": None, "name": "All Employees"}] + emps,
        "roles":       ["Manager","HR","Admin"],
    }


# ══════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(
    # ── Header filters ──
    period:      str           = Query("this_month",
                                       description="this_month|last_month|last_3m|last_6m|this_year|custom"),
    date_from:   Optional[date]= Query(None, description="Required when period=custom"),
    date_to:     Optional[date]= Query(None),
    department:  Optional[str] = Query(None),
    location:    Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    role:        str           = Query("Manager"),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """
    Dashboard tab — full page data.

    Returns:
      kpiCards (8)     : Present Rate · Absent Rate · Late Arrivals · Total Overtime
                         Punctuality Score · Consistency Score · Alerts · Leave Utilization
      dailyTrends      : Last 30-day Present/Absent/Late line chart data
      deptPerformance  : Per-dept Present% · Absent% · Late% · OT hours bar chart
      topPerformers    : Top 5 employees by attendance % with avatar letter
      calendarData     : Current month calendar with coloured dots (Present/Absent/Leave/Late)
    """
    class _F:
        pass
    f = _F()
    f.period     = period
    f.date_from  = date_from
    f.date_to    = date_to
    f.department = department if department != "All Departments" else None
    f.location   = location   if location   != "All Locations"   else None
    f.employee_id= employee_id if employee_id != "All Employees"  else None
    f.role       = role
    return DashboardService.get_dashboard(db, f)


# ══════════════════════════════════════════════════════════
# TAB 2 — REPORTS
# ══════════════════════════════════════════════════════════

@router.get("/library", response_model=List[ReportDefinitionOut])
def list_report_definitions(
    report_type: Optional[str] = Query(None,
                                        description="standard | exception | analytics"),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """
    Reports tab — Standard Reports Library.
    Filter tabs: All Reports (12) · Standard (5) · Exception (2) · Analytics (5)
    Each card: Name · Type badge · Description · Frequency · Last Generated · ↓ download icon
    """
    return ReportsService.list_definitions(db, report_type)


@router.post("/library/{report_def_id}/generate")
def generate_report(
    report_def_id: int             = Path(...),
    payload:       GenerateReportIn = ...,
    db:            Session          = Depends(get_db),
    current_user                    = Depends(get_current_user),
):
    """
    ↓ Download icon on each report card → generates and downloads the report.
    Accepts optional filters: date_from · date_to · department · location · employee_id
    Returns CSV (extend with reportlab/openpyxl for true PDF/XLSX).
    Also saves a GeneratedReport audit record and updates lastGenerated date.
    """
    payload.reportDefId = report_def_id
    try:
        report, csv_bytes = ReportsService.generate(
            db=db, payload=payload,
            generated_by=current_user.id,
            generated_by_name=getattr(current_user, "name", "HR Admin"),
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))

    media_types = {"pdf": "text/csv", "excel": "text/csv", "csv": "text/csv"}
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type=media_types.get(payload.format.value, "text/csv"),
        headers={
            "Content-Disposition": f"attachment; filename={report.file_name}",
            "X-Report-ID":         str(report.id),
            "X-Total-Records":     str(report.total_records),
        },
    )


@router.get("/library/export-all")
def export_all_reports(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Export All (12) button — downloads the full report definitions catalogue as CSV.
    """
    csv_bytes = ReportsService.export_all(db)
    return StreamingResponse(
        io.BytesIO(csv_bytes), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=report_catalogue.csv"},
    )


# ══════════════════════════════════════════════════════════
# TAB 3 — ANALYTICS
# ══════════════════════════════════════════════════════════

@router.get("/analytics", response_model=AnalyticsOut)
def get_analytics(
    period:      str           = Query("this_month"),
    date_from:   Optional[date]= Query(None),
    date_to:     Optional[date]= Query(None),
    department:  Optional[str] = Query(None),
    location:    Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """
    Analytics & Insights tab — full page data.

    Returns:
      kpiCards (6)        : Absenteeism Rate · Punctuality Score · Overtime Rate
                            Leave Utilization · Attendance Consistency · Predictive Alerts
      leavePattern        : Leave by Day of Week + Leave by Month bar charts
      overtimeAnalytics   : Total OT hrs · Avg per employee · Employees with OT
                            Department-wise Overtime Distribution horizontal bars
      peakAbsence         : Peak Absence Days + High Absence Periods
      anomalyDetection    : Total · High Severity · Medium · Affected Employees
                            Anomalies by Type bar + Detected Anomalies table
                            (Employee · Anomaly Type · Metric · Severity badge)
      deptComparison      : Department-wise table
                            (DEPARTMENT · PRESENT% · ABSENT% · LATE% · OVERTIME · SCORE)
    """
    class _F:
        pass
    f = _F()
    f.period      = period
    f.date_from   = date_from
    f.date_to     = date_to
    f.department  = department  if department  != "All Departments" else None
    f.location    = location    if location    != "All Locations"   else None
    f.employee_id = employee_id if employee_id != "All Employees"   else None
    return AnalyticsService.get_analytics(db, f)


# ══════════════════════════════════════════════════════════
# TAB 4 — EXCEPTIONS
# ══════════════════════════════════════════════════════════

@router.get("/exceptions", response_model=ExceptionListOut)
def list_exceptions(
    # ── All Exception Types dropdown ──
    exception_type: Optional[str] = Query(None, alias="type",
                                           description="late_arrival|absent_without_leave|excessive_overtime"),
    date_from:      Optional[date]= Query(None),
    date_to:        Optional[date]= Query(None),
    employee_id:    Optional[str] = Query(None),
    db:             Session       = Depends(get_db),
    current_user                  = Depends(get_current_user),
):
    """
    Exceptions tab — Attendance Exception Reports table.

    Summary cards (4 coloured):
      Total Exceptions · Late Arrivals · Absent Records · Overtime Violations

    Table columns:
      Employee (avatar + name + code) · Department badge · Exception Type
      Date & Time · Duration · Status badge (In Review / Pending Review) · View Details button
    """
    et = None
    if exception_type and exception_type not in ("All Exception Types", "all"):
        try:
            et = ExceptionTypeEnum(exception_type)
        except ValueError:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"Invalid exception type '{exception_type}'.")
    return ExceptionsService.list(db, et, date_from, date_to, employee_id)


@router.get("/exceptions/export")
def export_exceptions(
    exception_type: Optional[str] = Query(None, alias="type"),
    db:             Session       = Depends(get_db),
    current_user                  = Depends(get_current_user),
):
    """
    Export button (top right) → downloads exceptions as CSV.
    Applies the same exception_type filter as the table.
    """
    et = None
    if exception_type and exception_type not in ("All Exception Types", "all"):
        try:
            et = ExceptionTypeEnum(exception_type)
        except ValueError:
            pass
    csv_bytes = ExceptionsService.export_csv(db, et)
    return StreamingResponse(
        io.BytesIO(csv_bytes), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=exceptions.csv"},
    )


@router.get("/exceptions/{exception_id}", response_model=ExceptionOut)
def get_exception_detail(
    exception_id: int     = Path(...),
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    """
    View Details button on each exception row → opens a detail modal.
    Returns full exception record with employee info.
    """
    from models.attendance_reports import AttendanceException
    exc = db.query(AttendanceException).filter_by(id=exception_id).first()
    if not exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Exception {exception_id} not found.")
    from services.attendance_reports_service import _resolve_employee, ExceptionTypeEnum as ET
    emp = _resolve_employee(db, exc.employee_id)
    td  = (
        f"Late by {exc.duration_minutes} mins"
        if exc.exception_type == ET.late_arrival
        else "Absent" if exc.exception_type == ET.absent_without_leave
        else "Overtime Violation"
    )
    dur = (
        f"{exc.duration_minutes} mins"
        if exc.exception_type == ET.late_arrival
        else "Full Day" if exc.exception_type == ET.absent_without_leave
        else f"{round(exc.duration_minutes/60,1)}h"
    )
    dt_parts = [str(exc.exception_date)]
    if exc.in_time and exc.out_time:
        dt_parts.append(f"{exc.in_time} - {exc.out_time}")
    return {
        "id": exc.id, "employee_id": exc.employee_id,
        "employeeName": emp["name"], "department": exc.department or emp["department"],
        "exception_type": exc.exception_type, "typeDisplay": td,
        "exception_date": exc.exception_date,
        "in_time": exc.in_time, "out_time": exc.out_time,
        "dateTimeDisplay": "  ".join(dt_parts),
        "duration": dur, "status": exc.status,
        "notes": exc.notes, "created_at": exc.created_at,
    }


# ══════════════════════════════════════════════════════════
# TAB 5 — ALERTS
# ══════════════════════════════════════════════════════════

@router.get("/alerts", response_model=AlertsPageOut)
def get_alerts(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Alerts tab — Predictive Alerts & Anomaly Detection.

    Summary cards (4):
      High Priority · Medium Priority · Unacknowledged · Acknowledged

    Alert cards (5 types):
      ANOMALY ALERT · PATTERN ALERT · THRESHOLD ALERT
      PREDICTIVE ALERT · OVERTIME ALERT
    Each card: employee name · message · date · Acknowledge btn · View Pattern btn

    Anomaly Detection Rules table (bottom):
      Consecutive Late Arrivals · Frequent Absence Pattern
      Excessive Overtime · Department Threshold
    Each row: Name · Trigger · Count this month
    """
    return AlertsService.get_alerts_page(db)


@router.post("/alerts/acknowledge", response_model=MessageResponse)
def acknowledge_alerts(
    payload:     AcknowledgeIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Acknowledge button on each alert card.
    Pass alert_ids=None to acknowledge ALL unacknowledged alerts at once.
    Pass specific IDs to acknowledge individual alerts.
    """
    count = AlertsService.acknowledge(db, payload.alert_ids, current_user.id)
    return {"message": f"{count} alert(s) acknowledged."}


@router.patch("/alerts/rules/{rule_id}", response_model=MessageResponse)
def configure_alert_rule(
    rule_id:     int             = Path(...),
    payload:     ConfigureAlertIn = ...,
    db:          Session         = Depends(get_db),
    current_user                 = Depends(get_current_user),
):
    """
    Configure Alerts button → update threshold or toggle rule on/off.
    Anomaly Detection Rules:
      Consecutive Late Arrivals  → threshold = N consecutive days
      Frequent Absence Pattern   → threshold = N out of last 6
      Excessive Overtime         → threshold = N hours/week
      Department Threshold       → threshold = N% absenteeism
    """
    try:
        AlertsService.configure_rule(
            db=db,
            rule_id=payload.rule_id,
            threshold=payload.threshold,
            is_active=payload.is_active,
            updated_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return {"message": f"Alert rule {rule_id} updated."}
