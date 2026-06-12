from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from model.HR_Operations.employee_confirmation import EmployeeConfirmation
from model.HR_Operations.promotion import Promotion
from model.Employee_Management.employee_lifecycle import ProbationReview
from model.Employee_Management.employee_master import EmployeeMaster
from model.onboarding.employee import Employee




def _emp(db: Session, employee_id: int) -> Employee:
    e = db.execute(select(Employee).where(Employee.id == employee_id)).scalars().first()
    if not e:
        raise HTTPException(404, f"Employee {employee_id} not found")
    return e


def _master(db: Session, employee_id: int) -> Optional[EmployeeMaster]:
    return db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalars().first()


def _full_name(e: Employee) -> str:
    return f"{e.first_name} {e.last_name or ''}".strip()


def _effective_end(conf: EmployeeConfirmation) -> date:
    return conf.extended_till or conf.probation_end_date


def _days_left(conf: EmployeeConfirmation) -> int:
    return (_effective_end(conf) - date.today()).days




def get_page_summary(db: Session) -> dict:
    
    probation_pending = db.execute(
        select(func.count()).select_from(EmployeeConfirmation)
        .where(EmployeeConfirmation.status == "PENDING")
    ).scalar()

    confirmation_pending = db.execute(
        select(func.count()).select_from(EmployeeConfirmation)
        .where(EmployeeConfirmation.status.in_(["PENDING", "UNDER_REVIEW"]))
    ).scalar()

    promotions_pending = db.execute(
        select(func.count()).select_from(Promotion)
        .where(Promotion.status == "PENDING")
    ).scalar()

   
    buddy_active = db.execute(
        select(func.count()).select_from(EmployeeMaster)
        .where(EmployeeMaster.employment_status == "Active")
    ).scalar() or 0
    
    buddy_active = min(buddy_active, 99)

    return {
        "probation_pending": probation_pending or 0,
        "confirmation_pending": confirmation_pending or 0,
        "promotions_pending": promotions_pending or 0,
        "buddy_active": buddy_active,
    }




def _probation_status(conf: EmployeeConfirmation, days: int) -> str:
    if conf.status == "CONFIRMED":    return "Completed"
    if conf.status == "TERMINATED":   return "Terminated"
    if conf.status == "EXTENDED":     return "Extended"
    if days < 0:                      return "At Risk"
    if conf.performance_rating in ("POOR", "Needs Improvement", "Unsatisfactory"):
        return "At Risk"
    return "In Progress"


def _risk_level(conf: EmployeeConfirmation, days: int, status: str) -> str:
    if status in ("At Risk", "Terminated") or days < 0:  return "High"
    if days <= 30 or not conf.performance_rating:         return "Medium"
    return "Low"


def _milestones(reviews: list) -> list:
    result = []
    for day in (30, 60, 90):
        match = next((r for r in reviews if getattr(r, "milestone_day", None) == day), None)
        if match:
            status = "approved" if match.status == "completed" else "pending"
            rating_raw = getattr(match, "rating", "") or ""
            if "Exceeds" in rating_raw:   rating_short = "Exceeds"
            elif "Meets" in rating_raw:   rating_short = "Meets"
            elif "Needs" in rating_raw:   rating_short = "Needs"
            else:                          rating_short = rating_raw[:6] if rating_raw else None
        else:
            status       = "pending"
            rating_short = None
        result.append({"day": day, "status": status, "rating": rating_short})
    return result


def _build_probation_row(conf: EmployeeConfirmation, e: Employee, reviews: list) -> dict:
    days   = _days_left(conf)
    status = _probation_status(conf, days)
    risk   = _risk_level(conf, days, status)
    return {
        "id":               conf.id,
        "employee_id":      e.id,
        "employee_code":    e.employee_code,
        "name":             _full_name(e),
        "designation":      e.designation,
        "department":       e.department,
        "location":         e.location,
        "email":            e.official_email,
        "probation_status": status,
        "milestones":       _milestones(reviews),
        "progress_percent": min(100, max(0, int(
            (date.today() - conf.probation_start_date).days /
            max(1, (_effective_end(conf) - conf.probation_start_date).days) * 100
        ))),
        "days_remaining":   max(0, days),
        "end_date":         _effective_end(conf),
        "risk_level":       risk,
    }


def get_probation_kpi(db: Session) -> dict:
    today    = date.today()
    week_end = today + timedelta(days=7)
    confs    = db.execute(select(EmployeeConfirmation)).scalars().all()

    total = len(confs)
    at_risk = extended = reviews_due = ending_soon = 0
    progress_sum = 0

    for conf in confs:
        days   = _days_left(conf)
        status = _probation_status(conf, days)
        if status == "At Risk":                                     at_risk     += 1
        if status == "Extended":                                    extended    += 1
        if today <= _effective_end(conf) <= today + timedelta(30): ending_soon += 1
        if today <= _effective_end(conf) <= week_end:               reviews_due += 1
        progress_sum += min(100, max(0, int(
            (today - conf.probation_start_date).days /
            max(1, (_effective_end(conf) - conf.probation_start_date).days) * 100
        )))

    return {
        "total_probation":  total,
        "at_risk":          at_risk,
        "ending_soon":      ending_soon,
        "extended":         extended,
        "avg_progress":     round(progress_sum / total, 1) if total else 0.0,
        "reviews_due":      reviews_due,
    }


def list_probation(
    db: Session,
    search: Optional[str] = None,
    department: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
) -> List[dict]:
    rows_raw = db.execute(
        select(EmployeeConfirmation, Employee)
        .join(Employee, Employee.id == EmployeeConfirmation.employee_id)
    ).all()

    result = []
    for conf, e in rows_raw:
        if search:
            sl = search.lower()
            if not any([sl in _full_name(e).lower(), sl in (e.employee_code or "").lower()]):
                continue
        if department and department != "All Departments" and e.department != department:
            continue
        if location and location != "All Locations" and e.location != location:
            continue

        reviews = db.execute(
            select(ProbationReview)
            .where(ProbationReview.employee_id == e.id, ProbationReview.is_active == True)
            .order_by(ProbationReview.review_date)
        ).scalars().all()

        row = _build_probation_row(conf, e, reviews)

        if status and status != "All Status" and row["probation_status"] != status:
            continue
        result.append(row)

    return result[skip: skip + limit]


def get_probation_detail(db: Session, confirmation_id: int) -> dict:
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(404, "Probation record not found")
    e = _emp(db, conf.employee_id)
    reviews = db.execute(
        select(ProbationReview).where(ProbationReview.employee_id == e.id)
        .order_by(ProbationReview.review_date)
    ).scalars().all()
    row = _build_probation_row(conf, e, reviews)
    row.update({
        "probation_start_date": conf.probation_start_date,
        "probation_end_date":   conf.probation_end_date,
        "extended_till":        conf.extended_till,
        "performance_rating":   conf.performance_rating,
        "remarks":              conf.remarks,
        "reviewed_by":          conf.reviewed_by,
        "created_at":           conf.created_at,
        "updated_at":           conf.updated_at,
    })
    return row


def create_probation(db: Session, payload) -> dict:
    existing = db.execute(
        select(EmployeeConfirmation).where(
            EmployeeConfirmation.employee_id == payload.employee_id
        )
    ).scalars().first()
    if existing:
        raise HTTPException(400, "Employee already has a probation record")
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
    return get_probation_detail(db, conf.id)


def update_probation(db: Session, confirmation_id: int, payload) -> dict:
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(404, "Probation record not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(conf, k, v)
    if getattr(payload, "status", None) == "CONFIRMED" and getattr(payload, "confirmation_date", None):
        m = _master(db, conf.employee_id)
        if m:
            m.confirmed_date = payload.confirmation_date
            m.probation_end_date = None
    db.commit()
    db.refresh(conf)
    return get_probation_detail(db, conf.id)


def complete_milestone(db: Session, payload) -> dict:
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == payload.confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(404, "Probation record not found")
    review = ProbationReview(
        employee_id=conf.employee_id,
        review_date=date.today(),
        status="completed",
        rating=payload.rating,
        remarks=payload.remarks,
    )
    
    if hasattr(review, "milestone_day"):
        review.milestone_day = payload.milestone_day
    db.add(review)
    if payload.milestone_day == 90:
        conf.performance_rating = payload.rating
    db.commit()
    return get_probation_detail(db, conf.id)


def probation_bulk_action(db: Session, payload) -> dict:
    success, failed = [], []
    for cid in payload.confirmation_ids:
        try:
            conf = db.execute(
                select(EmployeeConfirmation).where(EmployeeConfirmation.id == cid)
            ).scalars().first()
            if not conf:
                failed.append({"id": cid, "reason": "Not found"})
                continue
            if payload.action == "auto_schedule":
                conf.status = "UNDER_REVIEW"
            elif payload.action == "send_reminders":
                pass  # hook notification service here
            success.append(cid)
        except Exception as exc:
            failed.append({"id": cid, "reason": str(exc)})
    db.commit()
    return {"action": payload.action, "total": len(payload.confirmation_ids),
            "success": len(success), "failed": failed}




def _workflow_steps(conf: EmployeeConfirmation) -> list:
    manager_done = bool(conf.reviewed_by)
    hr_done      = manager_done and conf.status not in ("PENDING",)
    dept_done    = hr_done and conf.status in ("CONFIRMED", "EXTENDED")
    auth_done    = conf.status == "CONFIRMED"
    auto_done    = conf.status == "CONFIRMED"

    steps = [
        {"step": 1, "role": "Manager",    "initial": "M", "status": "approved" if manager_done else "pending"},
        {"step": 2, "role": "HR",         "initial": "H", "status": "approved" if hr_done      else "pending"},
        {"step": 3, "role": "Dept Head",  "initial": "D", "status": "approved" if dept_done    else "pending"},
        {"step": 4, "role": "Authority",  "initial": "A", "status": "approved" if auth_done    else "pending"},
        {"step": 5, "role": "Auto",       "initial": "A", "status": "approved" if auto_done    else "pending"},
    ]
    for s in steps:
        s["actor_name"] = None
    return steps


def _workflow_progress(conf: EmployeeConfirmation) -> int:
    return sum(1 for s in _workflow_steps(conf) if s["status"] == "approved")


def _conf_row(conf: EmployeeConfirmation, e: Employee) -> dict:
    days    = _days_left(conf)
    overdue = conf.status not in ("CONFIRMED", "TERMINATED") and days < 0

    if conf.status == "CONFIRMED":
        c_status = "Confirmed"
        t_label  = "Confirmed"
    elif overdue:
        c_status = "Overdue"
        t_label  = f"{abs(days)} days overdue"
    elif not conf.reviewed_by:
        c_status = "Pending Approval"
        t_label  = f"{max(0, days)} days"
    else:
        c_status = "In Progress"
        t_label  = f"{max(0, days)} days"

    rating_map = {
        "EXCELLENT": (5, "Exceeds Expectations"),
        "GOOD":      (4, "Meets Expectations"),
        "SATISFACTORY": (3, "Meets Expectations"),
        "POOR":      (2, "Needs Improvement"),
    }
    stars, rating_label = rating_map.get(conf.performance_rating or "", (None, conf.performance_rating))

    steps     = _workflow_steps(conf)
    completed = sum(1 for s in steps if s["status"] == "approved")

    return {
        "id":                   conf.id,
        "employee_id":          e.id,
        "employee_code":        e.employee_code,
        "name":                 _full_name(e),
        "designation":          e.designation,
        "department":           e.department,
        "location":             e.location,
        "joined":               e.joining_date,
        "confirmation_status":  c_status,
        "workflow_progress":    completed,
        "workflow_total":       len(steps),
        "workflow_steps":       steps,
        "days_remaining":       max(0, days),
        "due_date":             _effective_end(conf),
        "time_label":           t_label,
        "is_overdue":           overdue,
        "rating":               rating_label,
        "rating_stars":         stars,
    }


def get_confirmation_kpi(db: Session) -> dict:
    confs = db.execute(select(EmployeeConfirmation)).scalars().all()
    total = len(confs)
    confirmed = sum(1 for c in confs if c.status == "CONFIRMED")
    pending   = sum(1 for c in confs if c.status in ("PENDING", "UNDER_REVIEW") and _days_left(c) >= 0)
    overdue   = sum(1 for c in confs if c.status not in ("CONFIRMED", "TERMINATED") and _days_left(c) < 0)
    auto_trig = sum(1 for c in confs if c.status == "UNDER_REVIEW")
    letters   = sum(1 for c in confs if c.status == "CONFIRMED" and c.confirmation_date)

    return {
        "for_confirmation":   total,
        "confirmed":          confirmed,
        "confirmed_rate_pct": round(confirmed / total * 100, 1) if total else 0.0,
        "pending":            pending,
        "overdue":            overdue,
        "auto_triggered":     auto_trig,
        "letters_sent":       letters,
    }


def list_confirmations(
    db: Session,
    search: Optional[str] = None,
    department: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
) -> List[dict]:
    rows_raw = db.execute(
        select(EmployeeConfirmation, Employee)
        .join(Employee, Employee.id == EmployeeConfirmation.employee_id)
    ).all()

    result = []
    for conf, e in rows_raw:
        if search:
            sl = search.lower()
            if not any([sl in _full_name(e).lower(), sl in (e.employee_code or "").lower()]):
                continue
        if department and department != "All Departments" and e.department != department:
            continue
        if location and location != "All Locations" and e.location != location:
            continue
        row = _conf_row(conf, e)
        if status and status != "All Status" and row["confirmation_status"] != status:
            continue
        result.append(row)

    result.sort(key=lambda x: (x["due_date"] is None, x["due_date"]))
    return result[skip: skip + limit]


def get_confirmation_detail(db: Session, confirmation_id: int) -> dict:
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(404, "Confirmation not found")
    e = _emp(db, conf.employee_id)
    return _conf_row(conf, e)


def process_confirmation_approval(db: Session, confirmation_id: int, payload) -> dict:
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(404, "Confirmation not found")

    if payload.action == "approve" and payload.role == "Authority":
        conf.status            = "CONFIRMED"
        conf.confirmation_date = date.today()
        m = _master(db, conf.employee_id)
        if m:
            m.confirmed_date     = conf.confirmation_date
            m.probation_end_date = None
    elif payload.action == "reject":
        conf.status = "PENDING"
    elif payload.action == "conditional":
        conf.status = "EXTENDED"
    elif payload.action == "approve" and payload.role == "Manager":
        conf.reviewed_by = conf.reviewed_by or 0

    if payload.remarks:
        conf.remarks = payload.remarks

    db.commit()
    db.refresh(conf)
    return get_confirmation_detail(db, conf.id)


def confirmation_bulk_action(db: Session, payload) -> dict:
    success, failed = [], []
    for cid in payload.confirmation_ids:
        try:
            conf = db.execute(
                select(EmployeeConfirmation).where(EmployeeConfirmation.id == cid)
            ).scalars().first()
            if not conf:
                failed.append({"id": cid, "reason": "Not found"})
                continue
            if payload.action == "auto_trigger" and conf.status == "PENDING":
                conf.status = "UNDER_REVIEW"
            elif payload.action == "bulk_process" and conf.reviewed_by:
                conf.status = "CONFIRMED"
                conf.confirmation_date = date.today()
            elif payload.action == "generate_letters":
                pass  # letter generation hook
            success.append(cid)
        except Exception as exc:
            failed.append({"id": cid, "reason": str(exc)})
    db.commit()
    return {"action": payload.action, "total": len(payload.confirmation_ids),
            "success": len(success), "failed": failed}




APPROVAL_ROLES = [
    {"role": "Manager",   "initial": "M"},
    {"role": "Dept Head", "initial": "D"},
    {"role": "HR",        "initial": "H"},
    {"role": "Finance",   "initial": "F"},
    {"role": "Lead",      "initial": "L"},
]


def _promo_workflow(promo: Promotion) -> dict:
    total = len(APPROVAL_ROLES)
    if promo.status == "APPROVED":
        completed = total
    elif promo.status == "REJECTED":
        completed = 1
    elif promo.status == "UNDER_REVIEW":
        completed = 2
    else:
        completed = 0

    steps = []
    for i, r in enumerate(APPROVAL_ROLES):
        if i < completed:
            s = "approved"
        elif promo.status == "REJECTED" and i == completed:
            s = "rejected"
        else:
            s = "pending"
        steps.append({"role": r["role"], "initial": r["initial"], "status": s})

    return {"steps": steps, "completed_steps": completed, "total_steps": total}


def _salary_increase_pct(current: Optional[Decimal], revised: Optional[Decimal]) -> Optional[float]:
    if current and revised and current > 0:
        return round(float((revised - current) / current * 100), 1)
    return None


def _salary_range_label(current: Optional[Decimal], revised: Optional[Decimal]) -> Optional[str]:
    if current and revised:
        def fmt(v): return f"₹{int(v):,}"
        return f"{fmt(current)} → {fmt(revised)}"
    return None


def _tenure_years(e: Employee) -> Optional[float]:
    if e.joining_date:
        delta = date.today() - e.joining_date
        return round(delta.days / 365.25, 1)
    return None


def _build_promo_row(promo: Promotion, e: Employee, m: Optional[EmployeeMaster]) -> dict:
    current_sal = m.salary if m else None
    revised_sal = promo.revised_salary
    wf = _promo_workflow(promo)
    inc_pct = _salary_increase_pct(current_sal, revised_sal)

    return {
        "id":                  promo.id,
        "employee_id":         e.id,
        "employee_code":       e.employee_code,
        "name":                _full_name(e),
        "designation":         e.designation,
        "department":          e.department,
        "location":            e.location,
        "tenure_years":        _tenure_years(e),
        "from_grade":          promo.from_grade,
        "to_grade":            promo.to_grade,
        "from_designation":    promo.from_designation,
        "to_designation":      promo.to_designation,
        "from_role":           getattr(promo, "from_role", None),
        "to_role":             getattr(promo, "to_role", None),
        "approval_workflow":   wf,
        "status":              promo.status.replace("_", " ").title(),
        "current_salary":      current_sal,
        "revised_salary":      revised_sal,
        "salary_increase_pct": inc_pct,
        "salary_range_label":  _salary_range_label(current_sal, revised_sal),
        "is_eligible":         promo.status != "REJECTED",
    }


def get_promotion_kpi(db: Session) -> dict:
    promos = db.execute(select(Promotion)).scalars().all()
    total   = len(promos)
    approved = sum(1 for p in promos if p.status == "APPROVED")
    under_review = sum(1 for p in promos if p.status in ("UNDER_REVIEW", "PENDING"))
    rejected = sum(1 for p in promos if p.status == "REJECTED")
    letters  = sum(1 for p in promos if p.status == "APPROVED")

    salary_increases = []
    for p in promos:
        if p.status == "APPROVED" and p.revised_salary:
            m = _master(db, p.employee_id)
            if m and m.salary and m.salary > 0:
                salary_increases.append(float((p.revised_salary - m.salary) / m.salary * 100))

    avg_inc = round(sum(salary_increases) / len(salary_increases), 1) if salary_increases else 0.0

    return {
        "nominations":             total,
        "approved":                approved,
        "approved_success_pct":    round(approved / total * 100, 1) if total else 0.0,
        "under_review":            under_review,
        "avg_salary_increase_pct": avg_inc,
        "letters_generated":       letters,
        "rejected":                rejected,
    }


def list_promotions(
    db: Session,
    search: Optional[str] = None,
    department: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
) -> List[dict]:
    rows_raw = db.execute(
        select(Promotion, Employee)
        .join(Employee, Employee.id == Promotion.employee_id)
    ).all()

    result = []
    for promo, e in rows_raw:
        if search:
            sl = search.lower()
            if not any([sl in _full_name(e).lower(), sl in (e.employee_code or "").lower()]):
                continue
        if department and department != "All Departments" and e.department != department:
            continue
        if location and location != "All Locations" and e.location != location:
            continue
        m   = _master(db, e.id)
        row = _build_promo_row(promo, e, m)
        if status and status != "All Status" and row["status"] != status:
            continue
        result.append(row)

    result.sort(key=lambda x: x["id"], reverse=True)
    return result[skip: skip + limit]


def get_promotion_detail(db: Session, promotion_id: int) -> dict:
    promo = db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    ).scalars().first()
    if not promo:
        raise HTTPException(404, "Promotion not found")
    e = _emp(db, promo.employee_id)
    m = _master(db, e.id)
    return _build_promo_row(promo, e, m)


def create_promotion(db: Session, payload) -> dict:
    promo = Promotion(
        employee_id      = payload.employee_id,
        from_designation = payload.from_designation,
        to_designation   = payload.to_designation,
        from_grade       = payload.from_grade,
        to_grade         = payload.to_grade,
        effective_date   = payload.effective_date,
        revised_salary   = payload.revised_salary,
        reason           = payload.reason,
        status           = "PENDING",
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return get_promotion_detail(db, promo.id)


def update_promotion(db: Session, promotion_id: int, payload) -> dict:
    promo = db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    ).scalars().first()
    if not promo:
        raise HTTPException(404, "Promotion not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(promo, k, v)

    if getattr(payload, "status", None) == "APPROVED":
        e = _emp(db, promo.employee_id)
        e.designation = promo.to_designation
        if promo.to_grade:
            e.grade = promo.to_grade
        m = _master(db, e.id)
        if m and promo.revised_salary:
            m.salary = promo.revised_salary

    db.commit()
    db.refresh(promo)
    return get_promotion_detail(db, promo.id)


def approve_promotion_step(db: Session, promotion_id: int, payload) -> dict:
    promo = db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    ).scalars().first()
    if not promo:
        raise HTTPException(404, "Promotion not found")

    if payload.action == "approve":
        current_step = sum(
            1 for s in _promo_workflow(promo)["steps"] if s["status"] == "approved"
        )
        if current_step >= len(APPROVAL_ROLES) - 1:
            promo.status = "APPROVED"
            
            e = _emp(db, promo.employee_id)
            e.designation = promo.to_designation
            if promo.to_grade:
                e.grade = promo.to_grade
            m = _master(db, e.id)
            if m and promo.revised_salary:
                m.salary = promo.revised_salary
        else:
            promo.status = "UNDER_REVIEW"
    elif payload.action == "reject":
        promo.status = "REJECTED"
    if payload.remarks:
        promo.remarks = payload.remarks

    db.commit()
    db.refresh(promo)
    return get_promotion_detail(db, promo.id)


def promotion_bulk_action(db: Session, payload) -> dict:
    success, failed = [], []
    for pid in payload.promotion_ids:
        try:
            promo = db.execute(
                select(Promotion).where(Promotion.id == pid)
            ).scalars().first()
            if not promo:
                failed.append({"id": pid, "reason": "Not found"})
                continue
            if payload.action == "check_eligibility":
                pass  # eligibility logic hook
            elif payload.action == "schedule_review":
                promo.status = "UNDER_REVIEW"
            elif payload.action == "generate_letters" and promo.status == "APPROVED":
                pass  # letter generation hook
            success.append(pid)
        except Exception as exc:
            failed.append({"id": pid, "reason": str(exc)})
    db.commit()
    return {"action": payload.action, "total": len(payload.promotion_ids),
            "success": len(success), "failed": failed}



_BUDDY_ASSIGNMENTS: dict[int, list[int]] = {}
_BUDDY_RATINGS: dict[int, list[float]]   = {}
_BUDDY_FEEDBACK_COUNT: dict[int, int]    = {}


def _get_buddy_pool(db: Session) -> List[Employee]:
   
    one_year_ago = date.today() - timedelta(days=365)
    return db.execute(
        select(Employee).where(Employee.joining_date <= one_year_ago)
    ).scalars().all()


def get_buddy_kpi(db: Session) -> dict:
    buddies   = _get_buddy_pool(db)
    total     = len(buddies)
    all_assign = sum(len(v) for v in _BUDDY_ASSIGNMENTS.values())
    all_fb    = sum(_BUDDY_FEEDBACK_COUNT.values())
    all_ratings = [r for ratings in _BUDDY_RATINGS.values() for r in ratings]
    avg_rating  = round(sum(all_ratings) / len(all_ratings), 1) if all_ratings else 4.8
    max_cap     = total * 3  # 3 joiners per buddy
    cap_used    = round(all_assign / max_cap * 100) if max_cap else 0

    avg_exp = 0.0
    if buddies:
        exps = [_tenure_years(b) or 0 for b in buddies]
        avg_exp = round(sum(exps) / len(exps), 1)

    return {
        "active_buddies":     total,
        "avg_rating":         avg_rating,
        "assignments":        all_assign,
        "feedback":           all_fb,
        "avg_experience_years": avg_exp,
        "capacity_used_pct":  cap_used,
    }


def list_buddies(
    db: Session,
    search: Optional[str] = None,
    department: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
) -> List[dict]:
    buddies = _get_buddy_pool(db)
    result  = []

    for e in buddies:
        if search:
            sl = search.lower()
            if not any([sl in _full_name(e).lower(), sl in (e.employee_code or "").lower()]):
                continue
        if department and department != "All Departments" and e.department != department:
            continue
        if location and location != "All Locations" and e.location != location:
            continue

        assignments = _BUDDY_ASSIGNMENTS.get(e.id, [])
        ratings     = _BUDDY_RATINGS.get(e.id, [4.7])
        avg_r       = round(sum(ratings) / len(ratings), 1)
        capacity    = min(100, int(len(assignments) / 3 * 100))
        fb_count    = _BUDDY_FEEDBACK_COUNT.get(e.id, 0)

        # Resolve joiner details
        joined_list = []
        for jid in assignments:
            try:
                je = _emp(db, jid)
                joined_list.append({
                    "employee_id":   je.id,
                    "employee_code": je.employee_code,
                    "name":          _full_name(je),
                })
            except Exception:
                pass

        buddy_status = "Active"
        if status and status != "All Status" and buddy_status != status:
            continue

        result.append({
            "id":               e.id,
            "employee_id":      e.id,
            "employee_code":    e.employee_code,
            "name":             _full_name(e),
            "designation":      e.designation,
            "department":       e.department,
            "email":            e.official_email,
            "status":           buddy_status,
            "assigned_joiners": joined_list,
            "assignments_count": len(assignments),
            "experience_years": _tenure_years(e) or 0.0,
            "joined_date":      e.joining_date,
            "rating":           avg_r,
            "rating_out_of":    5.0,
            "rating_label":     f"{avg_r}/5",
            "capacity_pct":     capacity,
            "max_capacity":     3,
        })

    return result[skip: skip + limit]


def assign_buddy(db: Session, payload) -> dict:
    buddy_emp = _emp(db, payload.buddy_employee_id)
    _emp(db, payload.joiner_employee_id)  # validate joiner exists

    existing = _BUDDY_ASSIGNMENTS.setdefault(payload.buddy_employee_id, [])
    if payload.joiner_employee_id in existing:
        raise HTTPException(400, "Joiner already assigned to this buddy")
    if len(existing) >= 3:
        raise HTTPException(400, "Buddy has reached maximum capacity (3)")

    existing.append(payload.joiner_employee_id)
    return {
        "buddy_employee_id":  payload.buddy_employee_id,
        "joiner_employee_id": payload.joiner_employee_id,
        "status":             "assigned",
    }


def submit_buddy_feedback(db: Session, payload) -> dict:
    _BUDDY_RATINGS.setdefault(payload.buddy_employee_id, []).append(payload.rating)
    _BUDDY_FEEDBACK_COUNT[payload.buddy_employee_id] = (
        _BUDDY_FEEDBACK_COUNT.get(payload.buddy_employee_id, 0) + 1
    )
    return {
        "buddy_employee_id":  payload.buddy_employee_id,
        "joiner_employee_id": payload.joiner_employee_id,
        "rating":             payload.rating,
        "status":             "recorded",
    }


def buddy_bulk_action(db: Session, payload) -> dict:
    if payload.action == "auto_assign":
        buddies = _get_buddy_pool(db)
        new_joiners = db.execute(
            select(Employee).where(
                Employee.joining_date >= date.today() - timedelta(days=30)
            )
        ).scalars().all()
        assigned = 0
        for joiner in new_joiners:
            for buddy in buddies:
                existing = _BUDDY_ASSIGNMENTS.get(buddy.id, [])
                if len(existing) < 3 and joiner.id not in existing:
                    _BUDDY_ASSIGNMENTS.setdefault(buddy.id, []).append(joiner.id)
                    assigned += 1
                    break
        return {"action": "auto_assign", "assigned": assigned}

    return {"action": payload.action, "buddy_ids": payload.buddy_ids, "status": "queued"}


def get_buddy_report(db: Session) -> dict:
    buddies = _get_buddy_pool(db)
    return {
        "total_buddies":     len(buddies),
        "total_assignments": sum(len(v) for v in _BUDDY_ASSIGNMENTS.values()),
        "avg_rating":        get_buddy_kpi(db)["avg_rating"],
        "capacity_used_pct": get_buddy_kpi(db)["capacity_used_pct"],
    }