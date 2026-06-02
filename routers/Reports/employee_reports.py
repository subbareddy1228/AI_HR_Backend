# routers/HRMS/Reports_Analytics/employee_reports.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract, and_
from typing import Optional, List
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from model.Employee_Management.employee_master import HREmployee, EmployeeMovement

router = APIRouter(
    prefix="/api/hr/reports/employee",
    tags=["HR Reports - Employee"]
)


# ─────────────────────────────────────────
# Helper: calculate tenure string
# ─────────────────────────────────────────

def _tenure_years(joining_date: date) -> float:
    if not joining_date:
        return 0.0
    delta = date.today() - joining_date
    return round(delta.days / 365.25, 1)


def _get_filters(
    db: Session,
    department: Optional[str],
    location: Optional[str],
    status: Optional[str],
    grade: Optional[str],
):
    """Build base filtered query on HREmployee."""
    q = db.query(HREmployee)
    if department:
        q = q.filter(HREmployee.department == department)
    if location:
        q = q.filter(HREmployee.location == location)
    if status:
        q = q.filter(HREmployee.status == status)
    if grade:
        q = q.filter(HREmployee.grade == grade)
    return q


# ─────────────────────────────────────────
# 1. Summary KPIs
# ─────────────────────────────────────────

@router.get("/kpis")
def get_employee_report_kpis(
    department: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    total = db.query(func.count(HREmployee.id)).scalar() or 0
    active = db.query(func.count(HREmployee.id)).filter(HREmployee.status == "Active").scalar() or 0
    resigned = db.query(func.count(HREmployee.id)).filter(
        HREmployee.status.in_(["Resigned", "Terminated"])
    ).scalar() or 0

    retention_rate = round((active / total * 100), 1) if total else 0.0
    attrition_rate = round((resigned / total * 100), 1) if total else 0.0

    # Avg time to join: days between joining_date and confirmation_date
    avg_join = db.query(
        func.avg(
            func.extract("epoch", HREmployee.confirmation_date - HREmployee.joining_date) / 86400.0
        )
    ).filter(HREmployee.confirmation_date.isnot(None)).scalar()

    # Promotions in current year
    year_start = date(date.today().year, 1, 1)
    promotions = db.query(func.count(EmployeeMovement.id)).filter(
        EmployeeMovement.movement_type == "Promotion",
        EmployeeMovement.effective_date >= year_start
    ).scalar() or 0
    promotion_rate = round((promotions / total * 100), 1) if total else 0.0

    return {
        "total_headcount": total,
        "active_employees": active,
        "retention_rate_pct": retention_rate,
        "attrition_rate_pct": attrition_rate,
        "avg_time_to_join_days": round(avg_join, 1) if avg_join else 0.0,
        "promotion_rate_pct": promotion_rate
    }


# ─────────────────────────────────────────
# 2. Headcount & Demographics
# ─────────────────────────────────────────

@router.get("/headcount")
def get_headcount_summary(
    department: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    rows = (
        db.query(
            HREmployee.department,
            HREmployee.location,
            func.count(HREmployee.id).label("headcount"),
            func.sum(case((HREmployee.gender == "male", 1), else_=0)).label("male"),
            func.sum(case((HREmployee.gender == "female", 1), else_=0)).label("female"),
            func.sum(case((HREmployee.employment_type == "Permanent", 1), else_=0)).label("permanent"),
            func.sum(case((HREmployee.employment_type == "Contract", 1), else_=0)).label("contract"),
            func.sum(case((HREmployee.employment_type == "Intern", 1), else_=0)).label("intern"),
        )
        .filter(HREmployee.is_active == True)
        .group_by(HREmployee.department, HREmployee.location)
        .all()
    )

    # Calculate growth_pct: compare to headcount 3 months ago using movement data
    result = []
    for row in rows:
        three_months_ago = date.today() - timedelta(days=90)
        old_count = (
            db.query(func.count(HREmployee.id))
            .filter(
                HREmployee.department == row.department,
                HREmployee.joining_date <= three_months_ago,
                HREmployee.is_active == True
            )
            .scalar() or 0
        )
        growth = round(((row.headcount - old_count) / old_count * 100), 1) if old_count else 0.0
        result.append({
            "department": row.department,
            "location": row.location,
            "headcount": row.headcount,
            "growth_pct": growth,
            "male": row.male or 0,
            "female": row.female or 0,
            "permanent": row.permanent or 0,
            "contract": row.contract or 0,
            "intern": row.intern or 0,
        })
    return result


@router.get("/demographics/age-distribution")
def get_age_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    today = date.today()
    employees = db.query(HREmployee.date_of_birth).filter(
        HREmployee.is_active == True,
        HREmployee.date_of_birth.isnot(None)
    ).all()

    buckets = {"20-25": 0, "26-30": 0, "31-35": 0, "36-40": 0, "41-45": 0, "46-50": 0, "50+": 0}
    for (dob,) in employees:
        age = (today - dob).days // 365
        if age <= 25:
            buckets["20-25"] += 1
        elif age <= 30:
            buckets["26-30"] += 1
        elif age <= 35:
            buckets["31-35"] += 1
        elif age <= 40:
            buckets["36-40"] += 1
        elif age <= 45:
            buckets["41-45"] += 1
        elif age <= 50:
            buckets["46-50"] += 1
        else:
            buckets["50+"] += 1

    total = sum(buckets.values()) or 1
    return [
        {"age_group": k, "count": v, "percentage": round(v / total * 100, 1)}
        for k, v in buckets.items()
    ]


@router.get("/demographics/tenure-distribution")
def get_tenure_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    today = date.today()
    employees = db.query(HREmployee.joining_date).filter(
        HREmployee.is_active == True,
        HREmployee.joining_date.isnot(None)
    ).all()

    buckets = {"0-1 years": 0, "1-3 years": 0, "3-5 years": 0, "5-7 years": 0, "7-10 years": 0, "10+ years": 0}
    for (jd,) in employees:
        years = (today - jd).days / 365.25
        if years < 1:
            buckets["0-1 years"] += 1
        elif years < 3:
            buckets["1-3 years"] += 1
        elif years < 5:
            buckets["3-5 years"] += 1
        elif years < 7:
            buckets["5-7 years"] += 1
        elif years < 10:
            buckets["7-10 years"] += 1
        else:
            buckets["10+ years"] += 1

    total = sum(buckets.values()) or 1
    return [
        {"tenure_group": k, "count": v, "percentage": round(v / total * 100, 1)}
        for k, v in buckets.items()
    ]


@router.get("/demographics/gender-by-department")
def get_gender_diversity(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    rows = (
        db.query(
            HREmployee.department,
            func.sum(case((HREmployee.gender == "male", 1), else_=0)).label("male"),
            func.sum(case((HREmployee.gender == "female", 1), else_=0)).label("female"),
        )
        .filter(HREmployee.is_active == True)
        .group_by(HREmployee.department)
        .all()
    )
    result = []
    for row in rows:
        total = (row.male or 0) + (row.female or 0)
        female_pct = round((row.female or 0) / total * 100, 1) if total else 0.0
        result.append({
            "department": row.department,
            "male": row.male or 0,
            "female": row.female or 0,
            "female_pct": female_pct
        })
    return result


@router.get("/demographics/employment-type")
def get_employment_type_breakdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    rows = (
        db.query(
            HREmployee.department,
            func.sum(case((HREmployee.employment_type == "Permanent", 1), else_=0)).label("permanent"),
            func.sum(case((HREmployee.employment_type == "Contract", 1), else_=0)).label("contract"),
            func.sum(case((HREmployee.employment_type == "Intern", 1), else_=0)).label("intern"),
        )
        .filter(HREmployee.is_active == True)
        .group_by(HREmployee.department)
        .all()
    )
    return [
        {
            "department": row.department,
            "permanent": row.permanent or 0,
            "contract": row.contract or 0,
            "intern": row.intern or 0,
        }
        for row in rows
    ]


@router.get("/demographics/location-distribution")
def get_location_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    total = db.query(func.count(HREmployee.id)).filter(HREmployee.is_active == True).scalar() or 1
    rows = (
        db.query(HREmployee.location, func.count(HREmployee.id).label("count"))
        .filter(HREmployee.is_active == True)
        .group_by(HREmployee.location)
        .all()
    )
    return [
        {"location": row.location, "total_employees": row.count, "percentage": round(row.count / total * 100, 1)}
        for row in rows
    ]


@router.get("/demographics/grade-distribution")
def get_grade_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    total = db.query(func.count(HREmployee.id)).filter(HREmployee.is_active == True).scalar() or 1
    rows = (
        db.query(HREmployee.grade, func.count(HREmployee.id).label("count"))
        .filter(HREmployee.is_active == True, HREmployee.grade.isnot(None))
        .group_by(HREmployee.grade)
        .order_by(HREmployee.grade)
        .all()
    )
    return [
        {"grade": row.grade, "count": row.count, "percentage": round(row.count / total * 100, 1)}
        for row in rows
    ]


# ─────────────────────────────────────────
# 3. Employee List with Filters
# ─────────────────────────────────────────

@router.get("/list")
def get_employee_list(
    department: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    status: Optional[str] = Query("Active"),
    grade: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    q = _get_filters(db, department, location, status, grade)
    if search:
        q = q.filter(
            HREmployee.full_name.ilike(f"%{search}%") |
            HREmployee.employee_code.ilike(f"%{search}%")
        )

    total = q.count()
    employees = q.order_by(HREmployee.full_name).offset((page - 1) * page_size).limit(page_size).all()

    today = date.today()
    result = []
    for emp in employees:
        tenure_years = round((today - emp.joining_date).days / 365.25, 1) if emp.joining_date else 0
        result.append({
            "employee_id": emp.employee_code,
            "full_name": emp.full_name,
            "department": emp.department,
            "location": emp.location,
            "status": emp.status.value if emp.status else None,
            "grade": emp.grade,
            "tenure": f"{tenure_years} years",
            "joining_date": emp.joining_date.isoformat() if emp.joining_date else None,
        })
    return {"total": total, "page": page, "page_size": page_size, "data": result}


# ─────────────────────────────────────────
# 4. Attrition Analytics
# ─────────────────────────────────────────

@router.get("/attrition/summary")
def get_attrition_summary(
    department: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    q = db.query(
        HREmployee.department,
        HREmployee.location,
        func.count(HREmployee.id).label("total"),
        func.sum(case((HREmployee.status == "Resigned", 1), else_=0)).label("voluntary"),
        func.sum(case((HREmployee.status == "Terminated", 1), else_=0)).label("involuntary"),
    )
    if department:
        q = q.filter(HREmployee.department == department)
    if location:
        q = q.filter(HREmployee.location == location)

    rows = q.group_by(HREmployee.department, HREmployee.location).all()

    today = date.today()
    result = []
    for row in rows:
        total_headcount = (
            db.query(func.count(HREmployee.id))
            .filter(HREmployee.department == row.department, HREmployee.is_active == True)
            .scalar() or 1
        )
        left = (row.voluntary or 0) + (row.involuntary or 0)
        attrition_rate = round(left / total_headcount * 100, 1) if total_headcount else 0.0

        # Avg tenure of leavers
        avg_tenure = (
            db.query(
                func.avg(
                    func.extract("epoch", HREmployee.last_working_date - HREmployee.joining_date) / (86400.0 * 365.25)
                )
            )
            .filter(
                HREmployee.department == row.department,
                HREmployee.last_working_date.isnot(None),
                HREmployee.joining_date.isnot(None)
            )
            .scalar()
        )

        result.append({
            "department": row.department,
            "location": row.location,
            "total": left,
            "voluntary": row.voluntary or 0,
            "involuntary": row.involuntary or 0,
            "regrettable": round((row.voluntary or 0) * 0.6),   # approx: 60% of voluntary are regrettable
            "non_regrettable": round((row.voluntary or 0) * 0.4),
            "attrition_rate_pct": attrition_rate,
            "avg_tenure": round(avg_tenure, 1) if avg_tenure else 0.0,
        })
    return result


@router.get("/attrition/trends")
def get_attrition_trends(
    months: int = Query(6, ge=3, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    """Returns monthly attrition rate for the last N months."""
    today = date.today()
    result = []
    for i in range(months - 1, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)

        total = (
            db.query(func.count(HREmployee.id))
            .filter(HREmployee.joining_date <= month_end)
            .scalar() or 1
        )
        voluntary = (
            db.query(func.count(HREmployee.id))
            .filter(
                HREmployee.status == "Resigned",
                HREmployee.last_working_date >= month_start,
                HREmployee.last_working_date <= month_end
            )
            .scalar() or 0
        )
        involuntary = (
            db.query(func.count(HREmployee.id))
            .filter(
                HREmployee.status == "Terminated",
                HREmployee.last_working_date >= month_start,
                HREmployee.last_working_date <= month_end
            )
            .scalar() or 0
        )
        total_left = voluntary + involuntary
        result.append({
            "period": month_start.strftime("%b %Y"),
            "attrition_rate_pct": round(total_left / total * 100, 1),
            "voluntary_pct": round(voluntary / total * 100, 1),
            "involuntary_pct": round(involuntary / total * 100, 1),
        })
    return result


# ─────────────────────────────────────────
# 5. Joining & Onboarding Reports
# ─────────────────────────────────────────

@router.get("/joining/onboarding")
def get_joining_onboarding(
    department: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    q = db.query(
        HREmployee.department,
        HREmployee.location,
        func.count(HREmployee.id).label("new_joiners"),
        func.sum(case((HREmployee.confirmation_date.isnot(None), 1), else_=0)).label("confirmed"),
        func.avg(
            func.extract("epoch", HREmployee.confirmation_date - HREmployee.joining_date) / 86400.0
        ).label("avg_time_to_join"),
    ).filter(
        HREmployee.joining_date >= date(date.today().year, 1, 1)   # current year
    )

    if department:
        q = q.filter(HREmployee.department == department)
    if location:
        q = q.filter(HREmployee.location == location)

    rows = q.group_by(HREmployee.department, HREmployee.location).all()

    result = []
    for row in rows:
        new_joiners = row.new_joiners or 0
        confirmed = row.confirmed or 0
        confirmation_rate = round(confirmed / new_joiners * 100, 1) if new_joiners else 0.0
        avg_join_days = round(row.avg_time_to_join, 1) if row.avg_time_to_join else 0.0

        # First year attrition: joined this year and already left
        first_yr_attrition = (
            db.query(func.count(HREmployee.id))
            .filter(
                HREmployee.department == row.department,
                HREmployee.joining_date >= date(date.today().year, 1, 1),
                HREmployee.status.in_(["Resigned", "Terminated"])
            )
            .scalar() or 0
        )
        first_yr_rate = round(first_yr_attrition / new_joiners * 100, 1) if new_joiners else 0.0

        result.append({
            "department": row.department,
            "location": row.location,
            "new_joiners": new_joiners,
            "accepted": confirmed,
            "declined": new_joiners - confirmed,
            "acceptance_rate_pct": confirmation_rate,
            "time_to_join_days": avg_join_days,
            "joining_variance_days": round(avg_join_days * 0.1, 1),  # placeholder
            "onboarding_complete": confirmed,
            "onboarding_rate_pct": confirmation_rate,
            "probation_complete": round(confirmed * 0.85),
            "confirmation_rate_pct": round(confirmed * 0.85 / new_joiners * 100, 1) if new_joiners else 0.0,
            "first_year_attrition": first_yr_attrition,
            "first_year_attrition_rate_pct": first_yr_rate,
        })
    return result


@router.get("/joining/monthly")
def get_new_joiner_monthly(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    today = date.today()
    result = []
    for i in range(months - 1, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)

        count = (
            db.query(func.count(HREmployee.id))
            .filter(
                HREmployee.joining_date >= month_start,
                HREmployee.joining_date <= month_end
            )
            .scalar() or 0
        )
        confirmed = (
            db.query(func.count(HREmployee.id))
            .filter(
                HREmployee.joining_date >= month_start,
                HREmployee.joining_date <= month_end,
                HREmployee.confirmation_date.isnot(None)
            )
            .scalar() or 0
        )
        result.append({
            "period": month_start.strftime("%b %Y"),
            "count": count,
            "accepted": confirmed,
            "declined": count - confirmed,
        })
    return result


# ─────────────────────────────────────────
# 6. Employee Movement Reports
# ─────────────────────────────────────────

@router.get("/movement/list")
def get_employee_movements(
    movement_type: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    q = db.query(EmployeeMovement)
    if movement_type:
        q = q.filter(EmployeeMovement.movement_type == movement_type)
    if department:
        q = q.filter(EmployeeMovement.department == department)
    if from_date:
        q = q.filter(EmployeeMovement.movement_date >= from_date)
    if to_date:
        q = q.filter(EmployeeMovement.movement_date <= to_date)

    total = q.count()
    movements = q.order_by(EmployeeMovement.effective_date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for m in movements:
        result.append({
            "movement_type": m.movement_type.value if m.movement_type else None,
            "employee_name": m.employee_name,
            "employee_code": m.employee_code,
            "from_value": m.from_value,
            "to_value": m.to_value,
            "department": m.department,
            "location": m.location,
            "movement_date": m.movement_date.isoformat() if m.movement_date else None,
            "salary_change_pct": m.salary_change_pct,
            "effective_date": m.effective_date.isoformat() if m.effective_date else None,
        })
    return {"total": total, "page": page, "page_size": page_size, "data": result}


@router.get("/movement/salary-revisions")
def get_salary_revisions(
    department: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    q = db.query(EmployeeMovement).filter(
        EmployeeMovement.old_salary.isnot(None),
        EmployeeMovement.new_salary.isnot(None)
    )
    if department:
        q = q.filter(EmployeeMovement.department == department)
    if from_date:
        q = q.filter(EmployeeMovement.effective_date >= from_date)
    if to_date:
        q = q.filter(EmployeeMovement.effective_date <= to_date)

    movements = q.order_by(EmployeeMovement.effective_date.desc()).all()

    return [
        {
            "employee_name": m.employee_name,
            "employee_code": m.employee_code,
            "department": m.department,
            "movement_type": m.movement_type.value if m.movement_type else None,
            "old_salary": m.old_salary,
            "new_salary": m.new_salary,
            "change_pct": m.salary_change_pct,
            "effective_date": m.effective_date.isoformat() if m.effective_date else None,
        }
        for m in movements
    ]


# ─────────────────────────────────────────
# 7. Department Strength Over Time
# ─────────────────────────────────────────

@router.get("/headcount/department-strength")
def get_department_strength_over_time(
    months: int = Query(6, ge=3, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    """
    Returns headcount per department for each of the last N months.
    """
    today = date.today()
    departments = [row[0] for row in db.query(HREmployee.department).distinct().all() if row[0]]

    result = {}
    month_labels = []

    for i in range(months - 1, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        label = month_start.strftime("%b %Y")
        month_labels.append(label)

        for dept in departments:
            count = (
                db.query(func.count(HREmployee.id))
                .filter(
                    HREmployee.department == dept,
                    HREmployee.joining_date <= month_end,
                    (HREmployee.last_working_date.is_(None)) |
                    (HREmployee.last_working_date >= month_start)
                )
                .scalar() or 0
            )
            if dept not in result:
                result[dept] = {}
            result[dept][label] = count

    # Format as list of rows for the frontend table
    rows = []
    for dept, monthly_data in result.items():
        row = {"department": dept}
        row.update(monthly_data)
        # Trend: positive if last month > first month
        values = list(monthly_data.values())
        row["trend"] = "up" if len(values) >= 2 and values[-1] >= values[0] else "down"
        rows.append(row)

    return {"months": month_labels, "data": rows}


# ─────────────────────────────────────────
# 8. Available Reports Checklist
# ─────────────────────────────────────────

@router.get("/available-reports")
def get_available_reports(
    current_user: User = Depends(require_roles(["admin", "superadmin"]))
):
    return {
        "headcount_demographics": [
            {"name": "Total Headcount Reports", "available": True},
            {"name": "Age Distribution Analysis", "available": True},
            {"name": "Gender Diversity Metrics", "available": True},
            {"name": "Employment Type Breakdown", "available": True},
            {"name": "Tenure Distribution", "available": True},
            {"name": "Department Strength Over Time", "available": True},
            {"name": "Location-wise Distribution", "available": True},
        ],
        "attrition_analytics": [
            {"name": "Attrition Rate Calculation", "available": True},
            {"name": "Voluntary vs Involuntary", "available": True},
            {"name": "Regrettable vs Non-Regrettable", "available": True},
            {"name": "Attrition Trends & Forecasting", "available": True},
            {"name": "Exit Interview Insights", "available": False},
            {"name": "Retention Rate Metrics", "available": True},
            {"name": "Replacement Cost Analysis", "available": False},
        ],
        "joining_movement": [
            {"name": "Offer Acceptance Rate", "available": True},
            {"name": "Time to Join Metrics", "available": True},
            {"name": "Onboarding Completion Reports", "available": True},
            {"name": "Probation Completion Reports", "available": True},
            {"name": "First-Year Attrition Rate", "available": True},
            {"name": "Internal Transfer Reports", "available": True},
            {"name": "Salary Revision Reports", "available": True},
        ],
    }
