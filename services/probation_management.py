from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from fastapi import HTTPException
from typing import Optional, List
from datetime import date, timedelta

from model.onboarding.employee               import Employee
from model.Employee_Management.employee_master import EmployeeMaster
from model.HR_Operations.employee_confirmation import EmployeeConfirmation
from model.Employee_Management.employee_lifecycle import ProbationReview

from schema.onboarding.probation_management import (
    ProbationAddEmployeeSchema,
    ProbationStatusUpdateSchema,
    ProbationBulkActionSchema,
    ProbationMilestoneSchema,
)



PROBATION_STATUSES = ["In Progress", "Under Review", "Extended", "At Risk", "Completed", "Terminated"]


RISK_LEVELS = ["Low", "Medium", "High"]


RATINGS = ["Exceeds Expectations", "Meets Expectations", "Needs Improvement", "Unsatisfactory"]



def _calc_progress(start: date, end: date) -> int:
   
    today      = date.today()
    total_days = (end - start).days
    if total_days <= 0:
        return 100
    elapsed = (today - start).days
    return min(100, max(0, int((elapsed / total_days) * 100)))


def _calc_risk(days_remaining: int, rating: Optional[str], status: str) -> str:
    
    if status in ["Extended", "At Risk"] or \
       rating in ["Needs Improvement", "Unsatisfactory"] or \
       days_remaining <= 15:
        return "High"
    elif days_remaining <= 30 or not rating:
        return "Medium"
    return "Low"


def _calc_probation_status(conf: EmployeeConfirmation, days_remaining: int) -> str:
    
    if conf.status == "CONFIRMED":
        return "Completed"
    if conf.status == "TERMINATED":
        return "Terminated"
    if conf.status == "EXTENDED":
        return "Extended"
    if days_remaining <= 0:
        return "Under Review"
    if conf.performance_rating in ["Needs Improvement", "Unsatisfactory"]:
        return "At Risk"
    return "In Progress"


def _milestone_status(reviews: list, milestone_day: int) -> bool:
    
    return any(
        r.status == "completed" and
        getattr(r, "milestone_day", None) == milestone_day
        for r in reviews
    )


def _conf_to_probation_dict(
    emp: Employee,
    conf: EmployeeConfirmation,
    reviews: list,
    master: Optional[EmployeeMaster],
) -> dict:
    today           = date.today()
    end_date        = conf.extended_till or conf.probation_end_date
    days_remaining  = (end_date - today).days
    progress        = _calc_progress(conf.probation_start_date, end_date)
    display_status  = _calc_probation_status(conf, days_remaining)
    risk_level      = _calc_risk(days_remaining, conf.performance_rating, display_status)

    # Next review date — next pending review
    next_review = next(
        (r.review_date for r in reviews if r.status != "completed"), None
    )

    # Extension count
    ext_count = len([r for r in reviews if r.status == "completed"
                     and hasattr(r, "is_extension") and r.is_extension])

    return {
        "id":               conf.id,
        "employeeId":       emp.employee_code,
        "name":             f"{emp.first_name} {emp.last_name or ''}".strip(),
        "designation":      emp.designation,
        "department":       emp.department,
        "location":         emp.location,
        "probationStatus":  display_status,
        "extensionCount":   ext_count,
        "progressPercent":  progress,
        "riskLevel":        risk_level,
        
        "milestone30Done":  _milestone_status(reviews, 30),
        "milestone60Done":  _milestone_status(reviews, 60),
        "milestone90Done":  _milestone_status(reviews, 90),
        "finalDone":        conf.status == "CONFIRMED",
        "nextReviewDate":   str(next_review) if next_review else None,
        "daysRemaining":    max(0, days_remaining),
        "probationEndDate": str(end_date),
        "currentRating":    conf.performance_rating,
        "probationStartDate":str(conf.probation_start_date),
        "joiningDate":      str(emp.joining_date) if emp.joining_date else None,
        "confirmationId":   conf.id,
    }



def get_probation_kpi(db: Session) -> dict:
    today        = date.today()
    week_end     = today + timedelta(days=7)

    confs = db.execute(select(EmployeeConfirmation)).scalars().all()

    total        = len(confs)
    in_progress  = 0
    at_risk      = 0
    ending_week  = 0
    completed    = 0
    high_risk    = 0

    for conf in confs:
        end_date       = conf.extended_till or conf.probation_end_date
        days_remaining = (end_date - today).days
        display_status = _calc_probation_status(conf, days_remaining)
        risk           = _calc_risk(days_remaining, conf.performance_rating, display_status)

        if display_status == "In Progress":
            in_progress += 1
        if display_status == "At Risk":
            at_risk += 1
        if today <= end_date <= week_end:
            ending_week += 1
        if display_status == "Completed":
            completed += 1
        if risk == "High":
            high_risk += 1

    return {
        "totalEmployees": total,
        "inProgress":     in_progress,
        "atRisk":         at_risk,
        "endingThisWeek": ending_week,
        "completed":      completed,
        "highRisk":       high_risk,
    }



def list_probation_employees(
    db:         Session,
    search:     Optional[str] = None,
    status:     Optional[str] = None,      # In Progress | Under Review | Extended | At Risk | Completed | Terminated
    department: Optional[str] = None,      # Engineering | HR | Sales | Marketing
    risk_level: Optional[str] = None,      # Low | Medium | High
    sort_by:    Optional[str] = "name",    # name | days_remaining | progress | joining_date
    skip:       int = 0,
    limit:      int = 50,
) -> List[dict]:
   
    
    q = (
        db.execute(
            select(EmployeeConfirmation, Employee)
            .join(Employee, Employee.id == EmployeeConfirmation.employee_id)
        ).all()
    )

    result = []
    for conf, emp in q:
        
        if search:
            search_lower = search.lower()
            if not any([
                search_lower in (emp.first_name or "").lower(),
                search_lower in (emp.last_name  or "").lower(),
                search_lower in (emp.employee_code or "").lower(),
                search_lower in (emp.official_email or "").lower(),
            ]):
                continue

        
        if department and department != "All Departments":
            if emp.department != department:
                continue

        
        reviews = db.execute(
            select(ProbationReview)
            .where(ProbationReview.employee_id == emp.id,
                   ProbationReview.is_active   == True)
            .order_by(ProbationReview.review_date)
        ).scalars().all()

        master = db.execute(
            select(EmployeeMaster).where(EmployeeMaster.employee_id == emp.id)
        ).scalars().first()

        row = _conf_to_probation_dict(emp, conf, reviews, master)

       
        if status and status != "All Status":
            if row["probationStatus"] != status:
                continue

        
        if risk_level and risk_level != "All Risk Levels":
            if row["riskLevel"] != risk_level:
                continue

        result.append(row)

    
    if sort_by == "days_remaining":
        result.sort(key=lambda x: x["daysRemaining"])
    elif sort_by == "progress":
        result.sort(key=lambda x: x["progressPercent"], reverse=True)
    elif sort_by == "joining_date":
        result.sort(key=lambda x: x["joiningDate"] or "")
    else:  
        result.sort(key=lambda x: x["name"])

    return result[skip: skip + limit]



def get_probation_employee(db: Session, confirmation_id: int) -> dict:
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(status_code=404, detail="Probation record not found")

    emp = db.execute(
        select(Employee).where(Employee.id == conf.employee_id)
    ).scalars().first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    reviews = db.execute(
        select(ProbationReview)
        .where(ProbationReview.employee_id == emp.id, ProbationReview.is_active == True)
        .order_by(ProbationReview.review_date)
    ).scalars().all()

    master = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == emp.id)
    ).scalars().first()

    return _conf_to_probation_dict(emp, conf, reviews, master)



def add_employee_probation(db: Session, payload: ProbationAddEmployeeSchema) -> dict:
    
    emp = db.execute(
        select(Employee).where(Employee.id == payload.employee_id)
    ).scalars().first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    
    existing = db.execute(
        select(EmployeeConfirmation)
        .where(EmployeeConfirmation.employee_id == payload.employee_id)
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee already has a probation record")

    conf = EmployeeConfirmation(
        employee_id=payload.employee_id,
        probation_start_date=payload.probation_start_date,
        probation_end_date=payload.probation_end_date,
        reviewed_by=payload.reviewed_by,
        remarks=payload.remarks,
        status="PENDING",
    )
    db.add(conf)
    db.commit()
    db.refresh(conf)
    return get_probation_employee(db, conf.id)


def update_probation_status(
    db:              Session,
    confirmation_id: int,
    payload:         ProbationStatusUpdateSchema,
) -> dict:
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(status_code=404, detail="Probation record not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(conf, field, value)

    
    if payload.status == "CONFIRMED":
        master = db.execute(
            select(EmployeeMaster).where(EmployeeMaster.employee_id == conf.employee_id)
        ).scalars().first()
        if master and payload.confirmation_date:
            master.confirmed_date    = payload.confirmation_date
            master.probation_end_date = None

    db.commit()
    db.refresh(conf)
    return get_probation_employee(db, conf.id)



def bulk_action_probation(db: Session, payload: ProbationBulkActionSchema) -> dict:
    
    results = {"success": [], "failed": []}

    for conf_id in payload.confirmation_ids:
        try:
            conf = db.execute(
                select(EmployeeConfirmation).where(EmployeeConfirmation.id == conf_id)
            ).scalars().first()
            if not conf:
                results["failed"].append({"id": conf_id, "reason": "Not found"})
                continue

            if payload.action == "confirm":
                conf.status           = "CONFIRMED"
                conf.confirmation_date = date.today()
            elif payload.action == "extend":
                conf.status       = "EXTENDED"
                conf.extended_till = conf.probation_end_date + timedelta(days=90)
            elif payload.action == "terminate":
                conf.status = "TERMINATED"
            elif payload.action == "send_reminder":
                pass   # email logic handled separately

            results["success"].append(conf_id)

        except Exception as e:
            results["failed"].append({"id": conf_id, "reason": str(e)})

    db.commit()
    return {
        "action":  payload.action,
        "total":   len(payload.confirmation_ids),
        "success": len(results["success"]),
        "failed":  results["failed"],
    }




def complete_milestone(db: Session, payload: ProbationMilestoneSchema) -> dict:
    
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == payload.confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(status_code=404, detail="Probation record not found")

    
    review = ProbationReview(
        employee_id=conf.employee_id,
        review_date=date.today(),
        status="completed",
        rating=payload.rating,
        remarks=payload.remarks,
    )
    db.add(review)

    
    if payload.milestone == "final":
        conf.performance_rating = payload.rating
        conf.status = "CONFIRMED" if payload.rating in ["Meets Expectations", "Exceeds Expectations"] else "PENDING"

    db.commit()
    return get_probation_employee(db, conf.id)




def get_probation_report(db: Session) -> dict:
    today = date.today()
    confs = db.execute(select(EmployeeConfirmation)).scalars().all()

    total        = len(confs)
    confirmed    = sum(1 for c in confs if c.status == "CONFIRMED")
    extended     = sum(1 for c in confs if c.status == "EXTENDED")
    terminated   = sum(1 for c in confs if c.status == "TERMINATED")

    confirmation_rate = round((confirmed / total * 100), 1) if total else 0

    
    durations = [
        (c.probation_end_date - c.probation_start_date).days
        for c in confs if c.probation_start_date and c.probation_end_date
    ]
    avg_days = round(sum(durations) / len(durations), 1) if durations else 0

    dept_map: dict = {}
    for conf in confs:
        emp = db.execute(
            select(Employee).where(Employee.id == conf.employee_id)
        ).scalars().first()
        dept = emp.department if emp else "Unknown"
        dept_map[dept] = dept_map.get(dept, 0) + 1

    
    risk_map: dict = {"High": 0, "Medium": 0, "Low": 0}
    for conf in confs:
        end_date       = conf.extended_till or conf.probation_end_date
        days_remaining = (end_date - today).days
        display_status = _calc_probation_status(conf, days_remaining)
        risk           = _calc_risk(days_remaining, conf.performance_rating, display_status)
        risk_map[risk] += 1

   
    rating_map: dict = {}
    for conf in confs:
        rating = conf.performance_rating or "Not Rated"
        rating_map[rating] = rating_map.get(rating, 0) + 1

    return {
        "period":             str(today),
        "totalOnProbation":   total,
        "confirmed":          confirmed,
        "extended":           extended,
        "terminated":         terminated,
        "confirmationRate":   confirmation_rate,
        "avgProbationDays":   avg_days,
        "byDepartment":       [{"department": k, "count": v} for k, v in dept_map.items()],
        "byRiskLevel":        risk_map,
        "byRating":           rating_map,
    }




def get_probation_departments(db: Session) -> List[str]:
    
    rows = db.execute(
        select(Employee.department)
        .join(EmployeeConfirmation, EmployeeConfirmation.employee_id == Employee.id)
        .where(Employee.department != None)
        .distinct()
    ).scalars().all()
    return sorted(rows)