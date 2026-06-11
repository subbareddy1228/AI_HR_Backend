from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from typing import Optional
from datetime import date, datetime

from core.database import get_db
from model.onboarding.employee import Employee
from model.models import AttendanceRecord as Attendance, LeaveRequest, LeaveStatus
from model.Payroll.payroll_run import PayrollRun
from model.Reports.dashboard_metric import DashboardMetric, MetricStatus, MetricCategory
from schema.Reports.dashboard_metric import (
    DashboardMetricCreate,
    DashboardMetricUpdate,
    DashboardMetricResponse,
)

router = APIRouter(prefix="/api/reports/executive dashboard", tags=["Executive Dashboard Reports"])


@router.get("/dashboard/hr-leadership")
def get_hr_leadership_dashboard(
    db:    Session = Depends(get_db),
    year:  int     = Query(default=None),
    month: int     = Query(default=None),
):
    today  = date.today()
    year   = year  or today.year
    month  = month or today.month
    m_start = date(year, month, 1)
    m_end   = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)

    
    total_emp  = db.query(func.count(Employee.id)).scalar() or 0
    active_emp = db.query(func.count(Employee.id)).filter(Employee.is_active == True).scalar() or 0
    prev_total = (
        db.query(func.count(Employee.id))
        .filter(Employee.joining_date < m_start)
        .scalar() or 0
    )
    headcount_change = round(((total_emp - prev_total) / prev_total * 100), 1) if prev_total else 0

  
    inactive_emp   = total_emp - active_emp
    attrition_rate = round((inactive_emp / total_emp * 100), 1) if total_emp else 0

    
    new_joiners = (
        db.query(func.count(Employee.id))
        .filter(Employee.joining_date >= m_start, Employee.joining_date < m_end)
        .scalar() or 0
    )
    open_positions = max(0, 100 - new_joiners)

    
    run = (
        db.query(PayrollRun)
        .filter(PayrollRun.run_year == year, PayrollRun.run_month == month)
        .order_by(PayrollRun.id.desc())
        .first()
    )
    payroll_cost     = float(run.total_gross) if run else 0.0
    payroll_cost_fmt = (
        f"${payroll_cost/1_000_000:.1f}M" if payroll_cost >= 1_000_000
        else f"${payroll_cost/1_000:.1f}K" if payroll_cost >= 1_000
        else f"${payroll_cost:.0f}"
    )
    prev_month = month - 1 if month > 1 else 12
    prev_year  = year      if month > 1 else year - 1
    prev_run   = (
        db.query(PayrollRun)
        .filter(PayrollRun.run_year == prev_year, PayrollRun.run_month == prev_month)
        .order_by(PayrollRun.id.desc())
        .first()
    )
    prev_payroll   = float(prev_run.total_gross) if prev_run else 0.0
    payroll_change = round(((payroll_cost - prev_payroll) / prev_payroll * 100), 1) if prev_payroll else 0.0

    
    total_att = (
        db.query(func.count(Attendance.id))
        .filter(Attendance.date >= m_start, Attendance.date < m_end)
        .scalar() or 0
    )
    present_att = (
        db.query(func.count(Attendance.id))
        .filter(Attendance.date >= m_start, Attendance.date < m_end,
                Attendance.status == "Present")
        .scalar() or 0
    )
    avg_attendance = round((present_att / total_att * 100), 1) if total_att else 0.0

    pending_approvals = (
        db.query(func.count(LeaveRequest.id))
        .filter(LeaveRequest.status == LeaveStatus.pending)
        .scalar() or 0
    )

    return {
        "totalHeadcount":      total_emp,
        "headcountChange":     f"+{headcount_change}%" if headcount_change >= 0 else f"{headcount_change}%",
        "headcountChangeDir":  "up" if headcount_change >= 0 else "down",
        "monthlyAttrition":    attrition_rate,
        "attritionChange":     "-0.8%",
        "attritionChangeDir":  "down",
        "openPositions":       open_positions,
        "openPositionsChange": "+12 from last month",
        "payrollCost":         payroll_cost,
        "payrollCostFmt":      payroll_cost_fmt,
        "payrollChange":       f"+{payroll_change}%" if payroll_change >= 0 else f"{payroll_change}%",
        "payrollChangeDir":    "up" if payroll_change >= 0 else "down",
        "avgAttendance":       avg_attendance,
        "attendanceChange":    "+1.2% from last month",
        "pendingApprovals":    pending_approvals,
        "pendingChange":       f"+{pending_approvals} from last month",
    }




@router.get("/dashboard/metrics/kpi")
def get_metrics_kpi(db: Session = Depends(get_db)):
    total = db.execute(
        select(func.count(DashboardMetric.id))
        .where(DashboardMetric.is_active == True)
    ).scalar() or 0

    by_status = db.execute(
        select(DashboardMetric.status, func.count(DashboardMetric.id).label("cnt"))
        .where(DashboardMetric.is_active == True)
        .group_by(DashboardMetric.status)
    ).all()

    status_map = {r.status: r.cnt for r in by_status}
    return {
        "total":     total,
        "stable":    status_map.get(MetricStatus.stable,    0),
        "alert":     status_map.get(MetricStatus.alert,     0),
        "onTrack":   status_map.get(MetricStatus.on_track,  0),
        "review":    status_map.get(MetricStatus.review,    0),
        "normal":    status_map.get(MetricStatus.normal,    0),
        "compliant": status_map.get(MetricStatus.compliant, 0),
    }


@router.get("/dashboard/metrics")
def list_metrics(
    db:       Session = Depends(get_db),
    search:   Optional[str]            = Query(None),
    category: Optional[MetricCategory] = Query(None),
    status:   Optional[MetricStatus]   = Query(None),
    page:     int = Query(1, ge=1),
    per_page: int = Query(8, ge=1, le=100),
):
    q = select(DashboardMetric).where(DashboardMetric.is_active == True)

    if search:
        q = q.where(DashboardMetric.metric_name.ilike(f"%{search}%"))
    if category:
        q = q.where(DashboardMetric.category == category)
    if status:
        q = q.where(DashboardMetric.status == status)

    q       = q.order_by(DashboardMetric.last_updated.desc())
    total   = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    offset  = (page - 1) * per_page
    records = db.execute(q.offset(offset).limit(per_page)).scalars().all()

    return {
        "total":      total,
        "page":       page,
        "perPage":    per_page,
        "totalPages": (total + per_page - 1) // per_page,
        "showing":    f"{offset + 1} – {min(offset + per_page, total)} of {total} metrics",
        "data": [
            {
                "id":          r.id,
                "metricName":  r.metric_name,
                "category":    r.category.value,
                "status":      r.status.value,
                "value":       r.value,
                "lastUpdated": r.last_updated.strftime("%Y-%m-%d") if r.last_updated else None,
                "createdBy":   r.created_by,
                "notes":       r.notes,
            }
            for r in records
        ],
    }


@router.get("/dashboard/metrics/{metric_id}", response_model=DashboardMetricResponse)
def get_metric(metric_id: int, db: Session = Depends(get_db)):
    m = db.execute(
        select(DashboardMetric).where(DashboardMetric.id == metric_id)
    ).scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Metric not found")
    return m


@router.post("/dashboard/metrics", response_model=DashboardMetricResponse, status_code=201)
def create_metric(payload: DashboardMetricCreate, db: Session = Depends(get_db)):
    m = DashboardMetric(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put("/dashboard/metrics/{metric_id}", response_model=DashboardMetricResponse)
def update_metric(
    metric_id: int,
    payload:   DashboardMetricUpdate,
    db:        Session = Depends(get_db),
):
    m = db.execute(
        select(DashboardMetric).where(DashboardMetric.id == metric_id,
                                      DashboardMetric.is_active == True)
    ).scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Metric not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(m, field, value)
    m.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(m)
    return m


@router.patch("/dashboard/metrics/{metric_id}/status")
def update_metric_status(
    metric_id: int,
    status:    MetricStatus,
    db:        Session = Depends(get_db),
):
    m = db.execute(
        select(DashboardMetric).where(DashboardMetric.id == metric_id,
                                      DashboardMetric.is_active == True)
    ).scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Metric not found")

    m.status       = status
    m.last_updated = datetime.utcnow()
    db.commit()
    return {"id": metric_id, "status": status.value, "message": f"Status updated to '{status.value}'"}


@router.delete("/dashboard/metrics/{metric_id}")
def delete_metric(metric_id: int, db: Session = Depends(get_db)):
    m = db.execute(
        select(DashboardMetric).where(DashboardMetric.id == metric_id)
    ).scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Metric not found")

    m.is_active    = False
    m.last_updated = datetime.utcnow()
    db.commit()
    return {"message": f"Metric '{m.metric_name}' deleted", "id": metric_id}



@router.get("/dashboard/manager")
def get_manager_dashboard(department: str = Query(...), db: Session = Depends(get_db)):
    today   = date.today()
    m_start = today.replace(day=1)

    return {
        "department":            department,
        "teamSize":              db.query(func.count(Employee.id)).filter(Employee.department == department, Employee.is_active == True).scalar() or 0,
        "presentToday":          db.query(func.count(Attendance.id)).filter(Attendance.date == today, Attendance.status == "Present").scalar() or 0,
        "pendingLeaveApprovals": db.query(func.count(LeaveRequest.id)).filter(LeaveRequest.status == LeaveStatus.pending).scalar() or 0,
        "newJoinersThisMonth":   db.query(func.count(Employee.id)).filter(Employee.department == department, Employee.joining_date >= m_start).scalar() or 0,
    }


@router.get("/dashboard/employee/{employee_id}")
def get_employee_dashboard(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    today       = date.today()
    month_start = today.replace(day=1)

    return {
        "employeeId":                 emp.employee_code,
        "name":                       f"{emp.first_name} {emp.last_name or ''}".strip(),
        "department":                 emp.department,
        "designation":                emp.designation,
        "location":                   emp.location,
        "joiningDate":                str(emp.joining_date),
        "presentDaysThisMonth":       db.query(func.count(Attendance.id)).filter(Attendance.date >= month_start, Attendance.status == "Present").scalar() or 0,
        "leaveApplicationsThisMonth": db.query(func.count(LeaveRequest.id)).filter(LeaveRequest.start_date >= month_start).scalar() or 0,
    }


@router.get("/dashboard/summary-cards")
def get_summary_cards(db: Session = Depends(get_db)):
    today       = date.today()
    month_start = today.replace(day=1)
    total       = db.query(func.count(Employee.id)).scalar() or 0
    active      = db.query(func.count(Employee.id)).filter(Employee.is_active == True).scalar() or 0

    return {
        "headcount":             total,
        "activeEmployees":       active,
        "newJoinersThisMonth":   db.query(func.count(Employee.id)).filter(Employee.joining_date >= month_start).scalar() or 0,
        "pendingLeaveApprovals": db.query(func.count(LeaveRequest.id)).filter(LeaveRequest.status == LeaveStatus.pending).scalar() or 0,
        "attritionRate":         round(((total - active) / total * 100), 1) if total else 0,
    }
