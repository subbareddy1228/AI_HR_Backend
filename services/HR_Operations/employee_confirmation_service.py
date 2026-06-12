from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from model.HR_Operations.employee_confirmation import EmployeeConfirmation
from model.Employee_Management.employee_master import EmployeeMaster
from model.onboarding.employee import Employee



APPROVAL_ROLES = ["Manager", "HR", "Dept Head", "Authority"]

STATUS_DISPLAY_MAP = {
    "PENDING":    "Pending Review",
    "CONFIRMED":  "Confirmed",
    "EXTENDED":   "Extended",
    "TERMINATED": "Terminated",
    "IN_PROGRESS": "In Progress",
    "UNDER_REVIEW": "Under Review",
}

ELIGIBILITY_MAP = {
    "ELIGIBLE":     "Eligible",
    "CONDITIONAL":  "Conditional",
    "NOT_ELIGIBLE": "Not Eligible",
}


def _get_employee(db: Session, employee_id: int) -> Employee:
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalars().first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    return emp


def _get_master(db: Session, employee_id: int) -> Optional[EmployeeMaster]:
    return db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalars().first()


def _effective_end_date(conf: EmployeeConfirmation) -> date:
    return conf.extended_till or conf.probation_end_date


def _days_remaining(conf: EmployeeConfirmation) -> int:
    return (_effective_end_date(conf) - date.today()).days


def _time_label(conf: EmployeeConfirmation) -> str:
    if conf.status == "CONFIRMED":
        return "Confirmed"
    days = _days_remaining(conf)
    if days < 0:
        return f"{abs(days)} days overdue"
    return f"{days} days"


def _is_overdue(conf: EmployeeConfirmation) -> bool:
    return conf.status not in ("CONFIRMED", "TERMINATED") and _days_remaining(conf) < 0


def _is_due_this_week(conf: EmployeeConfirmation) -> bool:
    today = date.today()
    week_end = today + timedelta(days=7)
    end = _effective_end_date(conf)
    return conf.status not in ("CONFIRMED", "TERMINATED") and today <= end <= week_end


def _confirmation_status_display(conf: EmployeeConfirmation) -> str:
    """Derive the badge shown in the 'Confirmation Status' column."""
    if conf.status == "CONFIRMED":
        conf_date = conf.confirmation_date
        return f"Confirmed"
    if conf.status == "EXTENDED":
        return "Extended"
    if conf.status == "TERMINATED":
        return "Terminated"
    days = _days_remaining(conf)
    if days < 0:
        return "Overdue"
    
    return "Pending Review"


def _extension_count(conf: EmployeeConfirmation) -> int:
    
    return 1 if conf.extended_till and conf.extended_till != conf.probation_end_date else 0


def _eligibility(conf: EmployeeConfirmation, master: Optional[EmployeeMaster]) -> str:
    
    if conf.status == "CONFIRMED":
        return "Eligible"
    if conf.performance_rating in ("POOR", "Unsatisfactory"):
        return "Not Eligible"
    if conf.performance_rating in ("SATISFACTORY", "Needs Improvement") or conf.status == "EXTENDED":
        return "Conditional"
    return "Eligible"


def _employment_type(master: Optional[EmployeeMaster]) -> str:
    if master and master.employment_type:
        return master.employment_type
    return "Regular"


def _build_approval_workflow(conf: EmployeeConfirmation) -> list[dict]:
    
    
    manager_status = "approved" if conf.reviewed_by else "pending"
    if conf.performance_rating == "POOR":
        manager_status = "rejected"

    
    hr_status = "approved" if manager_status == "approved" and conf.status not in ("PENDING",) else "pending"

    
    dept_status = "approved" if hr_status == "approved" and conf.status in ("CONFIRMED", "EXTENDED") else "pending"

    
    auth_status = "approved" if conf.status == "CONFIRMED" else "pending"

    return [
        {"role": "Manager",   "status": manager_status},
        {"role": "HR",        "status": hr_status},
        {"role": "Dept Head", "status": dept_status},
        {"role": "Authority", "status": auth_status},
    ]


def _manager_recommendation(conf: EmployeeConfirmation) -> str:
    
    if conf.status == "CONFIRMED":
        return "Recommended"
    if conf.status == "EXTENDED" or conf.performance_rating in ("POOR", "Unsatisfactory"):
        return "Not Recommended"
    if conf.performance_rating in ("SATISFACTORY", "Needs Improvement"):
        return "Conditional"
    return "Pending"


def _build_row(
    conf: EmployeeConfirmation,
    emp: Employee,
    master: Optional[EmployeeMaster],
) -> dict:
    
    return {
        "id":                    conf.id,
        "employee_id":           emp.id,
        "employee_code":         emp.employee_code,
        "name":                  f"{emp.first_name} {emp.last_name or ''}".strip(),
        "designation":           emp.designation,
        "department":            emp.department,
        "location":              emp.location,

        "confirmation_status":   _confirmation_status_display(conf),
        "confirmation_date":     conf.confirmation_date,
        "extension_count":       _extension_count(conf),

        "eligibility":           _eligibility(conf, master),
        "employment_type":       _employment_type(master),

        "approval_workflow":     _build_approval_workflow(conf),
        "manager_recommendation": _manager_recommendation(conf),

        "days_remaining":        _days_remaining(conf),
        "due_date":              _effective_end_date(conf),
        "time_label":            _time_label(conf),
        "is_overdue":            _is_overdue(conf),
    }


def _build_detail(conf: EmployeeConfirmation, emp: Employee, master: Optional[EmployeeMaster]) -> dict:
    row = _build_row(conf, emp, master)
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




def get_confirmation_kpi(db: Session) -> dict:
   
    confs = db.execute(select(EmployeeConfirmation)).scalars().all()
    today = date.today()
    week_end = today + timedelta(days=7)

    total            = len(confs)
    pending_review   = 0
    pending_approval = 0
    confirmed        = 0
    overdue          = 0
    due_this_week    = 0

    for conf in confs:
        if conf.status == "CONFIRMED":
            confirmed += 1
            continue

        days = _days_remaining(conf)

        if days < 0:
            overdue += 1
        elif days <= 7:
            due_this_week += 1

        
        if not conf.reviewed_by:
            pending_review += 1
        
        elif conf.status not in ("CONFIRMED", "TERMINATED"):
            pending_approval += 1

    return {
        "total":            total,
        "pending_review":   pending_review,
        "pending_approval": pending_approval,
        "confirmed":        confirmed,
        "overdue":          overdue,
        "due_this_week":    due_this_week,
    }


def list_confirmations(
    db:          Session,
    search:      Optional[str] = None,
    status:      Optional[str] = None,
    department:  Optional[str] = None,
    eligibility: Optional[str] = None,
    sort_by:     str = "due_date",
    skip:        int = 0,
    limit:       int = 50,
) -> List[dict]:
   
    rows_raw = db.execute(
        select(EmployeeConfirmation, Employee)
        .join(Employee, Employee.id == EmployeeConfirmation.employee_id)
    ).all()

    result = []
    for conf, emp in rows_raw:
        
        if search:
            sl = search.lower()
            name_full = f"{emp.first_name} {emp.last_name or ''}".lower()
            if not any([
                sl in name_full,
                sl in (emp.employee_code or "").lower(),
                sl in (emp.official_email or "").lower(),
                sl in (emp.department or "").lower(),
            ]):
                continue

       
        if department and department not in ("All Departments", ""):
            if emp.department != department:
                continue

        master = _get_master(db, emp.id)
        row    = _build_row(conf, emp, master)

        
        if status and status not in ("All Status", ""):
            if row["confirmation_status"] != status:
                continue

        
        if eligibility and eligibility not in ("All Eligibility", ""):
            if row["eligibility"] != eligibility:
                continue

        result.append(row)

   
    if sort_by == "name":
        result.sort(key=lambda x: x["name"])
    elif sort_by == "days_remaining":
        result.sort(key=lambda x: (x["days_remaining"] is None, x["days_remaining"]))
    elif sort_by == "status":
        result.sort(key=lambda x: x["confirmation_status"])
    else:  
        result.sort(key=lambda x: (x["due_date"] is None, x["due_date"]))

    return result[skip: skip + limit]


def get_confirmation(db: Session, confirmation_id: int) -> dict:
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(status_code=404, detail="Confirmation record not found")

    emp    = _get_employee(db, conf.employee_id)
    master = _get_master(db, emp.id)
    return _build_detail(conf, emp, master)


def create_confirmation(db: Session, payload) -> dict:
    emp = _get_employee(db, payload.employee_id)

    existing = db.execute(
        select(EmployeeConfirmation).where(
            EmployeeConfirmation.employee_id == payload.employee_id
        )
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee already has a confirmation record")

    conf = EmployeeConfirmation(
        employee_id          = payload.employee_id,
        probation_start_date = payload.probation_start_date,
        probation_end_date   = payload.probation_end_date,
        reviewed_by          = payload.reviewed_by,
        remarks              = payload.remarks,
        status               = "PENDING",
    )
    db.add(conf)
    db.commit()
    db.refresh(conf)
    return get_confirmation(db, conf.id)


def update_confirmation(db: Session, confirmation_id: int, payload) -> dict:
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(status_code=404, detail="Confirmation record not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(conf, key, value)

    
    if getattr(payload, "status", None) == "CONFIRMED" and getattr(payload, "confirmation_date", None):
        master = _get_master(db, conf.employee_id)
        if master:
            master.confirmed_date     = payload.confirmation_date
            master.probation_end_date = None

       
        emp = _get_employee(db, conf.employee_id)
        emp.confirmation_date = payload.confirmation_date

    db.commit()
    db.refresh(conf)
    return get_confirmation(db, conf.id)


def process_approval(db: Session, confirmation_id: int, payload) -> dict:
    
    conf = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == confirmation_id)
    ).scalars().first()
    if not conf:
        raise HTTPException(status_code=404, detail="Confirmation record not found")

    role   = payload.role
    action = payload.action   

    if action == "reject":
        conf.status = "PENDING"   
    elif action == "conditional":
        conf.status = "EXTENDED"
    elif action == "approve":
        if role == "Authority":
            conf.status            = "CONFIRMED"
            conf.confirmation_date = date.today()
            # Sync master
            master = _get_master(db, conf.employee_id)
            if master:
                master.confirmed_date     = conf.confirmation_date
                master.probation_end_date = None
            emp = _get_employee(db, conf.employee_id)
            emp.confirmation_date = conf.confirmation_date
       
        elif role == "Manager":
            conf.reviewed_by = conf.reviewed_by 

    if payload.remarks:
        conf.remarks = payload.remarks

    db.commit()
    db.refresh(conf)
    return get_confirmation(db, conf.id)


def bulk_action(db: Session, payload) -> dict:
   
    results = {"success": [], "failed": []}

    for conf_id in payload.confirmation_ids:
        try:
            conf = db.execute(
                select(EmployeeConfirmation).where(EmployeeConfirmation.id == conf_id)
            ).scalars().first()
            if not conf:
                results["failed"].append({"id": conf_id, "reason": "Not found"})
                continue

            action = payload.action

            if action == "approve_pending":
                if conf.status == "PENDING" and conf.reviewed_by:
                    conf.status            = "CONFIRMED"
                    conf.confirmation_date = date.today()
                    master = _get_master(db, conf.employee_id)
                    if master:
                        master.confirmed_date     = conf.confirmation_date
                        master.probation_end_date = None

            elif action == "send_reminder":
               
                pass

            elif action == "auto_trigger_review":
                if conf.status not in ("CONFIRMED", "TERMINATED"):
                    
                    if _is_overdue(conf) or _is_due_this_week(conf):
                        conf.status = "UNDER_REVIEW"

            results["success"].append(conf_id)

        except Exception as exc:
            results["failed"].append({"id": conf_id, "reason": str(exc)})

    db.commit()
    return {
        "action":  payload.action,
        "total":   len(payload.confirmation_ids),
        "success": len(results["success"]),
        "failed":  results["failed"],
    }


def send_reminders(db: Session) -> dict:
    
    confs = db.execute(select(EmployeeConfirmation)).scalars().all()
    targets = [c for c in confs if _is_overdue(c) or _is_due_this_week(c)]

   

    return {
        "reminders_sent": len(targets),
        "details": [
            {
                "confirmation_id": c.id,
                "employee_id":     c.employee_id,
                "due_date":        str(_effective_end_date(c)),
                "is_overdue":      _is_overdue(c),
            }
            for c in targets
        ],
    }


def auto_trigger_reviews(db: Session) -> dict:
   
    confs = db.execute(select(EmployeeConfirmation)).scalars().all()
    triggered = []
    skipped   = []

    for conf in confs:
        if conf.status in ("CONFIRMED", "TERMINATED"):
            skipped.append({"id": conf.id, "reason": "already terminal"})
            continue
        if _is_overdue(conf) and conf.status == "PENDING":
            conf.status = "UNDER_REVIEW"
            triggered.append({"id": conf.id, "employee_id": conf.employee_id})
        else:
            skipped.append({"id": conf.id, "reason": "not eligible"})

    db.commit()
    return {
        "triggered": len(triggered),
        "skipped":   len(skipped),
        "details":   triggered,
    }


def export_confirmations(
    db:          Session,
    status:      Optional[str] = None,
    department:  Optional[str] = None,
) -> List[dict]:
    
    rows = list_confirmations(db, status=status, department=department, limit=10000)
    export = []
    for r in rows:
        wf = r.get("approval_workflow", [])
        export.append({
            "Employee Code":        r["employee_code"],
            "Name":                 r["name"],
            "Designation":          r["designation"],
            "Department":           r["department"],
            "Location":             r["location"],
            "Confirmation Status":  r["confirmation_status"],
            "Eligibility":          r["eligibility"],
            "Employment Type":      r["employment_type"],
            "Due Date":             str(r["due_date"]) if r["due_date"] else "",
            "Days Remaining":       r["days_remaining"],
            "Is Overdue":           r["is_overdue"],
            "Manager":              wf[0]["status"] if len(wf) > 0 else "",
            "HR":                   wf[1]["status"] if len(wf) > 1 else "",
            "Dept Head":            wf[2]["status"] if len(wf) > 2 else "",
            "Authority":            wf[3]["status"] if len(wf) > 3 else "",
            "Recommendation":       r["manager_recommendation"],
            "Confirmation Date":    str(r["confirmation_date"]) if r.get("confirmation_date") else "",
        })
    return export


def get_departments(db: Session) -> List[str]:
    
    rows = db.execute(
        select(Employee.department)
        .join(EmployeeConfirmation, EmployeeConfirmation.employee_id == Employee.id)
        .where(Employee.department.isnot(None))
        .distinct()
    ).scalars().all()
    return sorted(rows)