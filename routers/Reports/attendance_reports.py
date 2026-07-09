from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, extract
from typing import List, Optional
from datetime import date, datetime, timedelta

from core.database import get_db
from core.dependencies import get_current_user
from model.models import User, AttendanceRecord as Attendance, LeaveRequest
from model.onboarding.employee import Employee
from model.HR_Automation.shift import Shift
from model.HR_Automation.work_hour_rule import WorkHourRule

from schema.Reports.attendance_reports import (
    AttendanceReportStats,
    ReportTypeSummary,
    AttendanceReportItem,
    ReportGenerationHistoryItem,
    DailyAttendanceSummaryItem,
    LateArrivalItem,
    EarlyDepartureItem,
    MissingPunchItem,
    MonthlyAttendanceItem,
    DeptAttendanceSummaryItem,
    LossOfPayItem,
    OvertimeSummaryItem,
    WFHTrackingItem,
    ExceptionReportItem,
    ComplianceMusterRollItem,
    AttendanceRegisterItem,
)

router = APIRouter(prefix="/attendance", tags=["Attendance Reports"])

SHIFT_START     = 9     
SHIFT_END       = 18       
LATE_THRESHOLD  = 15       
DAILY_WAGE      = 1500     



@router.get("/stats", response_model=AttendanceReportStats)
def get_attendance_report_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_attendance = db.execute(
        select(func.count()).select_from(Attendance)
    ).scalar_one()

    today_attendance = db.execute(
        select(func.count()).select_from(Attendance)
        .where(Attendance.date == date.today())
    ).scalar_one()

    return AttendanceReportStats(
        generated_reports=25,
        pending_reports=0,
        todays_reports=today_attendance,
        compliance_ready=4,
    )


@router.get("/type-summary", response_model=ReportTypeSummary)
def get_report_type_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ReportTypeSummary(
        daily_reports_total=6,
        daily_reports_generated=6,
        monthly_reports_total=7,
        monthly_reports_generated=7,
        exception_reports_total=8,
        exception_reports_generated=8,
        compliance_reports_total=4,
        compliance_reports_generated=4,
    )


@router.get("/list", response_model=List[AttendanceReportItem])
def get_all_attendance_reports(
    category: Optional[str] = Query(None, description="Daily | Monthly | Exception | Compliance"),
    department: Optional[str] = Query(None),
    report_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reports = [
       
        {"name": "Daily Attendance Summary",               "category": "Daily",      "dept": "All",         "details": None},
        {"name": "Late Arrivals List",                     "category": "Daily",      "dept": "Engineering", "details": "12 late arrivals"},
        {"name": "Early Departures List",                  "category": "Daily",      "dept": "All",         "details": "8 early departures"},
        {"name": "Missing Punch Report",                   "category": "Daily",      "dept": "All",         "details": "15 missing punches"},
        {"name": "Shift-wise Attendance",                  "category": "Daily",      "dept": "All",         "details": None},
        {"name": "Location-wise Attendance",               "category": "Daily",      "dept": "All",         "details": None},
       
        {"name": "Monthly Attendance Register",            "category": "Monthly",    "dept": "All",         "details": "1400 employees"},
        {"name": "Department-wise Attendance Summary",     "category": "Monthly",    "dept": "All",         "details": None},
        {"name": "Consolidated Monthly Report",            "category": "Monthly",    "dept": "All",         "details": None},
        {"name": "Loss of Pay Calculation",                "category": "Monthly",    "dept": "All",         "details": None},
        {"name": "Overtime Summary",                       "category": "Monthly",    "dept": "All",         "details": "1750.01 hours"},
        {"name": "WFH Tracking Report",                    "category": "Monthly",    "dept": "All",         "details": "420 WFH days"},
        {"name": "Attendance Percentage by Department/Location","category": "Monthly","dept": "All",        "details": None},
       
        {"name": "Exception Report",                       "category": "Exception",  "dept": "All",         "details": "15 exceptions"},
        {"name": "Continuous Absence Report",              "category": "Exception",  "dept": "All",         "details": None},
        {"name": "Frequent Late Arrivals",                 "category": "Exception",  "dept": "All",         "details": None},
        {"name": "Pattern-based Anomalies",                "category": "Exception",  "dept": "All",         "details": None},
        {"name": "Biometric vs Applied Leave Mismatch",    "category": "Exception",  "dept": "All",         "details": None},
        {"name": "Pending Regularization Requests",        "category": "Exception",  "dept": "All",         "details": None},
        {"name": "Unapproved Overtime",                    "category": "Exception",  "dept": "All",         "details": None},
        {"name": "Weekend Working without Approval",       "category": "Exception",  "dept": "All",         "details": None},
       
        {"name": "Compliance Muster Roll",                 "category": "Compliance", "dept": "All",         "details": "Factory Act format"},
        {"name": "Attendance Register for Labor Department","category": "Compliance","dept": "All",         "details": "Labor Department format"},
        {"name": "Factory Attendance Register",            "category": "Compliance", "dept": "Operations",  "details": "Factory Act format"},
        {"name": "Shops & Establishment Act Report",       "category": "Compliance", "dept": "All",         "details": "Shops & Establishment Act format"},
    ]

    result = []
    for r in reports:
        if category and r["category"] != category:
            continue
        if department and r["dept"] != "All" and r["dept"] != department:
            continue
        result.append(AttendanceReportItem(
            report_name=r["name"],
            category=r["category"],
            date=date(2024, 1, 15) if r["category"] == "Daily" else date(2024, 1, 31),
            generated_at="09:30 AM",
            department=r["dept"],
            details=r["details"],
            status="generated",
        ))
    return result


@router.get("/history", response_model=List[ReportGenerationHistoryItem])
def get_report_generation_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [
        ReportGenerationHistoryItem(
            report_type="Daily Attendance Summary",
            from_date=date(2024, 10, 1),
            to_date=date(2024, 10, 1),
            generated_by="System",
            file_size="2.4 MB",
            status="Generated",
        ),
        ReportGenerationHistoryItem(
            report_type="Monthly Consolidated Report",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 1, 31),
            generated_by="Admin User",
            file_size="5.1 MB",
            status="Generating",
        ),
        ReportGenerationHistoryItem(
            report_type="Exception Report",
            from_date=date(2024, 8, 1),
            to_date=date(2024, 8, 1),
            generated_by="System",
            file_size="1.8 MB",
            status="Generated",
        ),
    ]



@router.get("/daily-summary", response_model=List[DailyAttendanceSummaryItem])
def get_daily_attendance_summary(
    attendance_date: Optional[date] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_date = attendance_date or date.today()

    records = db.execute(
        select(Attendance).where(Attendance.date == target_date)
    ).scalars().all()

    emp_stmt = select(Employee).where(Employee.is_active == True)
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    employees = db.execute(emp_stmt).scalars().all()
    emp_map = {emp.id: emp for emp in employees}

    result = []
    for rec in records:
        emp = emp_map.get(rec.id)
        if not emp:
            continue
        result.append(DailyAttendanceSummaryItem(
            employee_id=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            date=rec.date,
            status=rec.status,
            check_in=None,
            check_out=None,
            remarks=None,
        ))
    return result


@router.get("/late-arrivals", response_model=List[LateArrivalItem])
def get_late_arrivals(
    attendance_date: Optional[date] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_date = attendance_date or date.today()

    emp_stmt = select(Employee).where(Employee.is_active == True)
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    employees = db.execute(emp_stmt).scalars().all()

    records = db.execute(
        select(Attendance).where(
            Attendance.date == target_date,
            Attendance.status == "LATE",
        )
    ).scalars().all()

    emp_map = {emp.id: emp for emp in employees}
    result = []
    for rec in records:
        emp = emp_map.get(rec.id)
        if not emp:
            continue
        result.append(LateArrivalItem(
            employee_id=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            date=rec.date,
            check_in=None,
            late_by_minutes=LATE_THRESHOLD + 10,
        ))
    return result


@router.get("/early-departures", response_model=List[EarlyDepartureItem])
def get_early_departures(
    attendance_date: Optional[date] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_date = attendance_date or date.today()

    emp_stmt = select(Employee).where(Employee.is_active == True)
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    employees = db.execute(emp_stmt).scalars().all()
    emp_map = {emp.id: emp for emp in employees}

    records = db.execute(
        select(Attendance).where(Attendance.date == target_date)
    ).scalars().all()

    result = []
    for rec in records:
        emp = emp_map.get(rec.id)
        if not emp:
            continue
        result.append(EarlyDepartureItem(
            employee_id=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            date=rec.date,
            check_out=None,
            early_by_minutes=30,
        ))
    return result


@router.get("/missing-punch", response_model=List[MissingPunchItem])
def get_missing_punch(
    attendance_date: Optional[date] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_date = attendance_date or date.today()

    emp_stmt = select(Employee).where(Employee.is_active == True)
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    employees = db.execute(emp_stmt).scalars().all()
    emp_map = {emp.id: emp for emp in employees}

    records = db.execute(
        select(Attendance).where(Attendance.date == target_date)
    ).scalars().all()

    result = []
    for rec in records:
        emp = emp_map.get(rec.id)
        if not emp:
            continue
        result.append(MissingPunchItem(
            employee_id=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            date=rec.date,
            punch_type="CHECK_OUT",
        ))
    return result



@router.get("/monthly-register", response_model=List[MonthlyAttendanceItem])
def get_monthly_attendance_register(
    month: int = Query(...),
    year: int = Query(...),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp_stmt = select(Employee).where(Employee.is_active == True)
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    employees = db.execute(emp_stmt).scalars().all()

    records = db.execute(
        select(Attendance).where(
            extract("month", Attendance.date) == month,
            extract("year", Attendance.date) == year,
        )
    ).scalars().all()

    emp_record_map = {}
    for rec in records:
        emp_record_map.setdefault(rec.id, []).append(rec)

    result = []
    for emp in employees:
        recs = emp_record_map.get(emp.id, [])
        present  = sum(1 for r in recs if r.status in ("Present", "PRESENT"))
        absent   = sum(1 for r in recs if r.status in ("Absent",  "ABSENT"))
        late     = sum(1 for r in recs if r.status in ("Late",    "LATE"))
        half_day = sum(1 for r in recs if r.status in ("Half_Day","HALF_DAY"))
        on_leave = sum(1 for r in recs if r.status in ("On_Leave","ON_LEAVE"))

        result.append(MonthlyAttendanceItem(
            employee_id=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            month=month,
            year=year,
            present_days=present,
            absent_days=absent,
            late_days=late,
            half_days=half_day,
            leave_days=on_leave,
            holidays=2,
            total_working_days=present + absent + late + half_day,
        ))
    return result


@router.get("/dept-summary", response_model=List[DeptAttendanceSummaryItem])
def get_dept_attendance_summary(
    attendance_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_date = attendance_date or date.today()

    results = db.execute(
        select(
            Employee.department,
            func.count(Employee.id).label("total"),
        )
        .where(Employee.is_active == True)
        .group_by(Employee.department)
    ).all()

    records = db.execute(
        select(Attendance).where(Attendance.date == target_date)
    ).scalars().all()

    present_by_dept = {}
    for rec in records:
        emp = db.get(Employee, rec.id)
        if emp:
            dept = emp.department or "Unknown"
            present_by_dept[dept] = present_by_dept.get(dept, 0) + (1 if rec.status in ("Present","PRESENT") else 0)

    items = []
    for r in results:
        dept = r.department or "Unknown"
        total = r.total
        present = present_by_dept.get(dept, 0)
        absent = total - present
        items.append(DeptAttendanceSummaryItem(
            department=dept,
            total_employees=total,
            present=present,
            absent=absent,
            on_leave=0,
            attendance_pct=round((present / total) * 100, 1) if total > 0 else 0.0,
        ))
    return items


@router.get("/loss-of-pay", response_model=List[LossOfPayItem])
def get_loss_of_pay(
    month: int = Query(...),
    year: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employees = db.execute(
        select(Employee).where(Employee.is_active == True)
    ).scalars().all()

    records = db.execute(
        select(Attendance).where(
            extract("month", Attendance.date) == month,
            extract("year", Attendance.date) == year,
            Attendance.status.in_(["Absent", "ABSENT"]),
        )
    ).scalars().all()

    absent_map = {}
    for rec in records:
        absent_map[rec.id] = absent_map.get(rec.id, 0) + 1

    result = []
    for emp in employees:
        absent_days = absent_map.get(emp.id, 0)
        if absent_days > 0:
            result.append(LossOfPayItem(
                employee_id=emp.employee_code,
                employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
                department=emp.department,
                absent_days=absent_days,
                lop_days=absent_days,
                lop_amount=absent_days * DAILY_WAGE,
            ))
    return result


@router.get("/overtime-summary", response_model=List[OvertimeSummaryItem])
def get_overtime_summary(
    month: int = Query(...),
    year: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employees = db.execute(
        select(Employee).where(Employee.is_active == True)
    ).scalars().all()

    result = []
    for emp in employees:
        result.append(OvertimeSummaryItem(
            employee_id=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            month=month,
            year=year,
            total_overtime_hours=0.0,
        ))
    return result


@router.get("/wfh-tracking", response_model=List[WFHTrackingItem])
def get_wfh_tracking(
    month: int = Query(...),
    year: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employees = db.execute(
        select(Employee).where(Employee.is_active == True)
    ).scalars().all()

    records = db.execute(
        select(Attendance).where(
            extract("month", Attendance.date) == month,
            extract("year", Attendance.date) == year,
            Attendance.status.in_(["WFH", "WORK_FROM_HOME"]),
        )
    ).scalars().all()

    wfh_map = {}
    for rec in records:
        wfh_map[rec.id] = wfh_map.get(rec.id, 0) + 1

    return [
        WFHTrackingItem(
            employee_id=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            month=month,
            year=year,
            wfh_days=wfh_map.get(emp.id, 0),
        )
        for emp in employees
    ]



@router.get("/exceptions", response_model=List[ExceptionReportItem])
def get_exception_report(
    exception_type: Optional[str] = Query(None, description="LATE | EARLY_DEPARTURE | MISSING_PUNCH | CONTINUOUS_ABSENCE | UNAPPROVED_OT"),
    attendance_date: Optional[date] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_date = attendance_date or date.today()

    emp_stmt = select(Employee).where(Employee.is_active == True)
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    employees = db.execute(emp_stmt).scalars().all()
    emp_map = {emp.id: emp for emp in employees}

    records = db.execute(
        select(Attendance).where(Attendance.date == target_date)
    ).scalars().all()

    status_to_exception = {
        "LATE":    "LATE",
        "Late":    "LATE",
        "ABSENT":  "CONTINUOUS_ABSENCE",
        "Absent":  "CONTINUOUS_ABSENCE",
    }

    result = []
    for rec in records:
        exc = status_to_exception.get(rec.status)
        if not exc:
            continue
        if exception_type and exc != exception_type:
            continue
        emp = emp_map.get(rec.id)
        if not emp:
            continue
        result.append(ExceptionReportItem(
            employee_id=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            date=rec.date,
            exception_type=exc,
        ))
    return result


@router.get("/muster-roll", response_model=List[ComplianceMusterRollItem])
def get_muster_roll(
    month: int = Query(...),
    year: int = Query(...),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp_stmt = select(Employee).where(Employee.is_active == True)
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    employees = db.execute(emp_stmt).scalars().all()
    emp_map = {emp.id: emp for emp in employees}

    records = db.execute(
        select(Attendance).where(
            extract("month", Attendance.date) == month,
            extract("year", Attendance.date) == year,
        )
    ).scalars().all()

    result = []
    for rec in records:
        emp = emp_map.get(rec.id)
        if not emp:
            continue
        result.append(ComplianceMusterRollItem(
            employee_id=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            date=rec.date,
            status=rec.status,
            format="Factory Act format",
        ))
    return result


@router.get("/attendance-register", response_model=List[AttendanceRegisterItem])
def get_attendance_register(
    month: int = Query(...),
    year: int = Query(...),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp_stmt = select(Employee).where(Employee.is_active == True)
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    employees = db.execute(emp_stmt).scalars().all()

    records = db.execute(
        select(Attendance).where(
            extract("month", Attendance.date) == month,
            extract("year", Attendance.date) == year,
        )
    ).scalars().all()

    emp_record_map = {}
    for rec in records:
        emp_record_map.setdefault(rec.id, []).append(rec)

    result = []
    for emp in employees:
        recs = sorted(emp_record_map.get(emp.id, []), key=lambda x: x.date)
        attendance_str = ",".join(
            "P" if r.status in ("Present", "PRESENT") else
            "A" if r.status in ("Absent",  "ABSENT")  else
            "H" if r.status in ("Holiday", "HOLIDAY") else
            "L"
            for r in recs
        )
        result.append(AttendanceRegisterItem(
            employee_id=emp.employee_code,
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            month=month,
            year=year,
            attendance_record=attendance_str,
        ))
    return result
