# routers/HR_Operations/promotions.py
# ═══════════════════════════════════════════════════════════════════════════════
#  Promotions & Career Progression — Complete Router
#
#  Tab 1 — Probation Management   →  /hr-ops/promotions/probation/*
#  Tab 2 — Employee Confirmation  →  /hr-ops/promotions/confirmation/*
#  Tab 3 — Promotions             →  /hr-ops/promotions/promotion/*
#  Tab 4 — Buddy Program          →  /hr-ops/promotions/buddy/*
#
#  Shared util                    →  /hr-ops/promotions/filter-options
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, select
from typing import List, Optional
from datetime import date, timedelta
from decimal import Decimal

from core.database import get_db

# ── Models ────────────────────────────────────────────────────────────────────
from model.HR_Operations.probation_management import ProbationManagement
from model.HR_Operations.employee_confirmation import EmployeeConfirmation
from model.HR_Operations.promotion import Promotion
from model.HR_Operations.buddy_program import BuddyProgram, BuddyAssignment
from model.onboarding.employee import Employee

# ── Schemas ───────────────────────────────────────────────────────────────────
from schema.HR_Operations.probation_management import (
    ProbationCreate, ProbationUpdate, ProbationResponse, ProbationDashboard,
)
from schema.HR_Operations.employee_confirmation import (
    EmployeeConfirmationCreate, EmployeeConfirmationUpdate,
    EmployeeConfirmationResponse, ConfirmationDashboard,
)
from schema.HR_Operations.promotion import (
    PromotionCreate, PromotionUpdate, PromotionResponse, PromotionDashboard,
)
from schema.HR_Operations.buddy_program import (
    BuddyCreate, BuddyUpdate, BuddyResponse,
    BuddyAssignmentCreate, BuddyAssignmentResponse,
    BuddyFeedbackSubmit, BuddyDashboard,
)

router = APIRouter(
    prefix="/hr-ops/promotions",
    tags=["HR Operations – Promotions & Career"],
)


# ─────────────────────────────────────────────────────────────────────────────
#  INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_employee_or_404(employee_id: int, db: Session) -> Employee:
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id={employee_id} not found",
        )
    return emp


def _employee_dict(emp: Employee) -> dict:
    return {
        "id":             emp.id,
        "first_name":     emp.first_name,
        "last_name":      emp.last_name,
        "employee_code":  emp.employee_code,
        "designation":    emp.designation,
        "department":     emp.department,
        "location":       emp.location,
        "official_email": emp.official_email,
    }


def _attach_employee(record, db: Session):
    """Attach .employee attribute to any record that has .employee_id."""
    try:
        emp = _get_employee_or_404(record.employee_id, db)
        record.employee = _employee_dict(emp)
    except HTTPException:
        record.employee = None


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 1  ·  PROBATION MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

# ── Dashboard stat cards ──────────────────────────────────────────────────────
@router.get(
    "/probation/dashboard",
    response_model=ProbationDashboard,
    summary="Probation – summary stat cards",
)
def probation_dashboard(db: Session = Depends(get_db)):
    today       = date.today()
    soon_cutoff = today + timedelta(days=30)
    next_7      = today + timedelta(days=7)

    total = db.execute(func.count(ProbationManagement.id)).scalar() or 0

    # re-query with proper select() for count aggregates
    total = db.execute(
        select(func.count()).select_from(ProbationManagement)
    ).scalar() or 0

    in_progress = db.execute(
        select(func.count()).select_from(ProbationManagement)
        .where(ProbationManagement.status == "In Progress")
    ).scalar() or 0

    at_risk = db.execute(
        select(func.count()).select_from(ProbationManagement)
        .where(ProbationManagement.risk_level == "High")
    ).scalar() or 0

    ending_soon = db.execute(
        select(func.count()).select_from(ProbationManagement)
        .where(
            and_(
                ProbationManagement.probation_end_date >= today,
                ProbationManagement.probation_end_date <= soon_cutoff,
                ProbationManagement.status.in_(["In Progress", "At Risk"]),
            )
        )
    ).scalar() or 0

    extended = db.execute(
        select(func.count()).select_from(ProbationManagement)
        .where(ProbationManagement.status == "Extended")
    ).scalar() or 0

    avg_progress = db.execute(
        select(func.avg(ProbationManagement.progress_percentage))
        .select_from(ProbationManagement)
    ).scalar() or 0.0

    reviews_due = db.execute(
        select(func.count()).select_from(ProbationManagement)
        .where(
            and_(
                ProbationManagement.review_date >= today,
                ProbationManagement.review_date <= next_7,
            )
        )
    ).scalar() or 0

    return ProbationDashboard(
        total_probation=total,
        in_progress=in_progress,
        at_risk=at_risk,
        ending_soon=ending_soon,
        extended=extended,
        avg_progress_pct=round(float(avg_progress), 1),
        reviews_due_next_7_days=reviews_due,
    )


# ── List with filters ─────────────────────────────────────────────────────────
@router.get("/probation", response_model=List[ProbationResponse])
def list_probation(
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    search:     Optional[str] = Query(None),
    skip:       int           = Query(0,  ge=0),
    limit:      int           = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = (
        select(ProbationManagement)
        .join(Employee, ProbationManagement.employee_id == Employee.id)
    )
    if department and department != "All Departments":
        q = q.where(Employee.department == department)
    if location and location != "All Locations":
        q = q.where(Employee.location == location)
    if status and status != "All Status":
        q = q.where(ProbationManagement.status == status)
    if search:
        q = q.where(
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
            )
        )
    records = db.execute(q.offset(skip).limit(limit)).scalars().all()
    for r in records:
        _attach_employee(r, db)
    return records


# ── Create ────────────────────────────────────────────────────────────────────
@router.post("/probation", response_model=ProbationResponse, status_code=201)
def create_probation(payload: ProbationCreate, db: Session = Depends(get_db)):
    _get_employee_or_404(payload.employee_id, db)
    # Prevent duplicate active probations
    existing = db.execute(
        select(ProbationManagement)
        .where(
            and_(
                ProbationManagement.employee_id == payload.employee_id,
                ProbationManagement.status.in_(["In Progress", "At Risk", "Extended"]),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Employee already has an active probation record",
        )
    record = ProbationManagement(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    _attach_employee(record, db)
    return record


# ── Get single ────────────────────────────────────────────────────────────────
@router.get("/probation/{probation_id}", response_model=ProbationResponse)
def get_probation(probation_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(ProbationManagement).where(ProbationManagement.id == probation_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Probation record not found")
    _attach_employee(record, db)
    return record


# ── Update ────────────────────────────────────────────────────────────────────
@router.patch("/probation/{probation_id}", response_model=ProbationResponse)
def update_probation(
    probation_id: int,
    payload: ProbationUpdate,
    db: Session = Depends(get_db),
):
    record = db.execute(
        select(ProbationManagement).where(ProbationManagement.id == probation_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Probation record not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    _attach_employee(record, db)
    return record


# ── Delete ────────────────────────────────────────────────────────────────────
@router.delete("/probation/{probation_id}", status_code=204)
def delete_probation(probation_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(ProbationManagement).where(ProbationManagement.id == probation_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Probation record not found")
    db.delete(record)
    db.commit()


# ── Quick-action: Auto-Schedule reviews ──────────────────────────────────────
@router.post("/probation/auto-schedule", summary="Auto-schedule probation review dates")
def auto_schedule_probation(db: Session = Depends(get_db)):
    """Sets review_date = probation_end_date − 7 days for all unscheduled active records."""
    records = db.execute(
        select(ProbationManagement)
        .where(
            and_(
                ProbationManagement.status.in_(["In Progress", "At Risk"]),
                ProbationManagement.review_date.is_(None),
            )
        )
    ).scalars().all()
    updated = 0
    for r in records:
        r.review_date   = r.probation_end_date - timedelta(days=7)
        r.auto_scheduled = True
        updated += 1
    db.commit()
    return {"scheduled": updated, "message": f"Auto-scheduled {updated} review(s)"}


# ── Quick-action: Send Reminders ──────────────────────────────────────────────
@router.post("/probation/send-reminders", summary="Queue probation reminder emails")
def send_probation_reminders(db: Session = Depends(get_db)):
    today  = date.today()
    due_in_3 = db.execute(
        select(func.count()).select_from(ProbationManagement)
        .where(
            and_(
                ProbationManagement.review_date >= today,
                ProbationManagement.review_date <= today + timedelta(days=3),
            )
        )
    ).scalar() or 0
    # TODO: plug in your email service here (core/mail.py)
    return {"reminders_queued": due_in_3, "message": "Reminder emails queued successfully"}


# ── Quick-action: Assign Buddies ──────────────────────────────────────────────
@router.post("/probation/assign-buddies", summary="Assign best available buddy to probationers")
def assign_buddies_to_probationers(db: Session = Depends(get_db)):
    """Finds all In Progress probationers without a buddy and auto-assigns the best available buddy."""
    no_buddy = db.execute(
        select(ProbationManagement)
        .where(
            and_(
                ProbationManagement.status == "In Progress",
                ProbationManagement.buddy_id.is_(None),
            )
        )
    ).scalars().all()
    assigned = 0
    for r in no_buddy:
        best_buddy = db.execute(
            select(BuddyProgram)
            .where(
                and_(
                    BuddyProgram.status == "Active",
                    BuddyProgram.current_assignments < BuddyProgram.max_capacity,
                )
            )
            .order_by(BuddyProgram.rating.desc())
        ).scalar_one_or_none()
        if best_buddy:
            r.buddy_id = best_buddy.buddy_employee_id
            best_buddy.current_assignments += 1
            assigned += 1
    db.commit()
    return {"assigned": assigned, "message": f"Assigned buddies to {assigned} probationer(s)"}


# ── Quick-action: Import Data (bulk) ──────────────────────────────────────────
@router.post("/probation/import", summary="Bulk import probation records")
def import_probation(records: List[ProbationCreate], db: Session = Depends(get_db)):
    created, errors = 0, []
    for i, payload in enumerate(records):
        try:
            _get_employee_or_404(payload.employee_id, db)
            db.add(ProbationManagement(**payload.model_dump()))
            created += 1
        except Exception as exc:
            errors.append({"row": i + 1, "error": str(exc)})
    db.commit()
    return {"created": created, "errors": errors}


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 2  ·  EMPLOYEE CONFIRMATION
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/confirmation/dashboard",
    response_model=ConfirmationDashboard,
    summary="Confirmation – summary stat cards",
)
def confirmation_dashboard(db: Session = Depends(get_db)):
    today = date.today()

    total = db.execute(
        select(func.count()).select_from(EmployeeConfirmation)
    ).scalar() or 0

    confirmed = db.execute(
        select(func.count()).select_from(EmployeeConfirmation)
        .where(EmployeeConfirmation.status == "Confirmed")
    ).scalar() or 0

    pending = db.execute(
        select(func.count()).select_from(EmployeeConfirmation)
        .where(EmployeeConfirmation.status == "Pending Approval")
    ).scalar() or 0

    overdue = db.execute(
        select(func.count()).select_from(EmployeeConfirmation)
        .where(
            and_(
                EmployeeConfirmation.due_date < today,
                EmployeeConfirmation.status == "Pending Approval",
            )
        )
    ).scalar() or 0

    auto_trig = db.execute(
        select(func.count()).select_from(EmployeeConfirmation)
        .where(EmployeeConfirmation.auto_triggered == True)  # noqa: E712
    ).scalar() or 0

    letters = db.execute(
        select(func.count()).select_from(EmployeeConfirmation)
        .where(EmployeeConfirmation.letter_sent == True)  # noqa: E712
    ).scalar() or 0

    confirmed_rate = round((confirmed / total * 100) if total > 0 else 0.0, 1)
    for_confirmation = total - confirmed

    return ConfirmationDashboard(
        for_confirmation=for_confirmation,
        confirmed=confirmed,
        confirmed_rate_pct=confirmed_rate,
        pending=pending,
        overdue=overdue,
        auto_triggered=auto_trig,
        letters_sent=letters,
    )


@router.get("/confirmation", response_model=List[EmployeeConfirmationResponse])
def list_confirmations(
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    search:     Optional[str] = Query(None),
    skip:       int           = Query(0,  ge=0),
    limit:      int           = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    today = date.today()
    q = (
        select(EmployeeConfirmation)
        .join(Employee, EmployeeConfirmation.employee_id == Employee.id)
    )
    if department and department != "All Departments":
        q = q.where(Employee.department == department)
    if location and location != "All Locations":
        q = q.where(Employee.location == location)
    if status and status != "All Status":
        q = q.where(EmployeeConfirmation.status == status)
    if search:
        q = q.where(
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
            )
        )
    records = db.execute(q.offset(skip).limit(limit)).scalars().all()
    for r in records:
        # Compute live days_remaining
        r.days_remaining = (r.due_date - today).days if r.due_date else None
        _attach_employee(r, db)
    return records


@router.post("/confirmation", response_model=EmployeeConfirmationResponse, status_code=201)
def create_confirmation(payload: EmployeeConfirmationCreate, db: Session = Depends(get_db)):
    _get_employee_or_404(payload.employee_id, db)
    record = EmployeeConfirmation(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    record.days_remaining = (record.due_date - date.today()).days if record.due_date else None
    _attach_employee(record, db)
    return record


@router.get("/confirmation/{conf_id}", response_model=EmployeeConfirmationResponse)
def get_confirmation(conf_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == conf_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Confirmation record not found")
    record.days_remaining = (record.due_date - date.today()).days if record.due_date else None
    _attach_employee(record, db)
    return record


@router.patch("/confirmation/{conf_id}", response_model=EmployeeConfirmationResponse)
def update_confirmation(
    conf_id: int,
    payload: EmployeeConfirmationUpdate,
    db: Session = Depends(get_db),
):
    record = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == conf_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Confirmation record not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    # Re-compute workflow_step from boolean flags
    record.workflow_step = sum([
        record.step_1_done, record.step_2_done, record.step_3_done,
        record.step_4_done, record.step_5_done,
    ])
    db.commit()
    db.refresh(record)
    record.days_remaining = (record.due_date - date.today()).days if record.due_date else None
    _attach_employee(record, db)
    return record


@router.delete("/confirmation/{conf_id}", status_code=204)
def delete_confirmation(conf_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id == conf_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Confirmation record not found")
    db.delete(record)
    db.commit()


# ── Quick-action: Auto-Trigger ────────────────────────────────────────────────
@router.post("/confirmation/auto-trigger", summary="Mark confirmations as auto-triggered")
def auto_trigger_confirmations(db: Session = Depends(get_db)):
    updated = db.execute(
        select(EmployeeConfirmation)
        .where(
            and_(
                EmployeeConfirmation.due_date <= date.today() + timedelta(days=7),
                EmployeeConfirmation.auto_triggered == False,  # noqa: E712
                EmployeeConfirmation.status == "Pending Approval",
            )
        )
    ).scalars().all()
    count = 0
    for r in updated:
        r.auto_triggered = True
        count += 1
    db.commit()
    return {"auto_triggered": count}


# ── Quick-action: Send Reminders ──────────────────────────────────────────────
@router.post("/confirmation/send-reminders", summary="Queue confirmation reminder emails")
def send_confirmation_reminders(db: Session = Depends(get_db)):
    pending = db.execute(
        select(func.count()).select_from(EmployeeConfirmation)
        .where(
            and_(
                EmployeeConfirmation.status == "Pending Approval",
                EmployeeConfirmation.due_date >= date.today(),
            )
        )
    ).scalar() or 0
    # TODO: integrate core/mail.py here
    return {"reminders_queued": pending, "message": "Reminder emails queued successfully"}


# ── Quick-action: Bulk Process ────────────────────────────────────────────────
@router.post("/confirmation/bulk-process", summary="Bulk confirm / extend / terminate")
def bulk_process_confirmations(
    conf_ids: List[int],
    action:   str = Query(..., description="confirm | extend | terminate"),
    db: Session = Depends(get_db),
):
    status_map = {"confirm": "Confirmed", "extend": "Extended", "terminate": "Terminated"}
    if action not in status_map:
        raise HTTPException(status_code=400, detail=f"Invalid action '{action}'")
    records = db.execute(
        select(EmployeeConfirmation).where(EmployeeConfirmation.id.in_(conf_ids))
    ).scalars().all()
    for r in records:
        r.status = status_map[action]
    db.commit()
    return {"updated": len(records), "new_status": status_map[action]}


# ── Quick-action: Generate Letters ───────────────────────────────────────────
@router.post("/confirmation/generate-letters", summary="Generate confirmation letters")
def generate_confirmation_letters(conf_ids: List[int], db: Session = Depends(get_db)):
    records = db.execute(
        select(EmployeeConfirmation)
        .where(
            and_(
                EmployeeConfirmation.id.in_(conf_ids),
                EmployeeConfirmation.status == "Confirmed",
            )
        )
    ).scalars().all()
    for r in records:
        r.letter_sent = True
    db.commit()
    return {"letters_generated": len(records)}


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 3  ·  PROMOTIONS
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/promotion/dashboard",
    response_model=PromotionDashboard,
    summary="Promotions – summary stat cards",
)
def promotion_dashboard(db: Session = Depends(get_db)):
    total = db.execute(
        select(func.count()).select_from(Promotion)
    ).scalar() or 0

    approved = db.execute(
        select(func.count()).select_from(Promotion).where(Promotion.status == "Approved")
    ).scalar() or 0

    under_review = db.execute(
        select(func.count()).select_from(Promotion).where(Promotion.status == "Under Review")
    ).scalar() or 0

    rejected = db.execute(
        select(func.count()).select_from(Promotion).where(Promotion.status == "Rejected")
    ).scalar() or 0

    letters = db.execute(
        select(func.count()).select_from(Promotion).where(Promotion.letter_generated == True)  # noqa: E712
    ).scalar() or 0

    avg_inc = db.execute(
        select(func.avg(Promotion.salary_increase_percent)).select_from(Promotion)
    ).scalar() or 0.0

    success_rate = round((approved / total * 100) if total > 0 else 0.0, 1)

    return PromotionDashboard(
        total_nominations=total,
        approved=approved,
        approved_success_rate_pct=success_rate,
        under_review=under_review,
        avg_salary_increase_pct=round(float(avg_inc), 1),
        letters_generated=letters,
        rejected=rejected,
    )


@router.get("/promotion", response_model=List[PromotionResponse])
def list_promotions(
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    search:     Optional[str] = Query(None),
    skip:       int           = Query(0,  ge=0),
    limit:      int           = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Promotion).join(Employee, Promotion.employee_id == Employee.id)
    if department and department != "All Departments":
        q = q.where(Employee.department == department)
    if location and location != "All Locations":
        q = q.where(Employee.location == location)
    if status and status != "All Status":
        q = q.where(Promotion.status == status)
    if search:
        q = q.where(
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
            )
        )
    records = db.execute(q.offset(skip).limit(limit)).scalars().all()
    for r in records:
        # Sync approval_step counter from flags
        r.approval_step = sum([r.step_m_done, r.step_d_done, r.step_h_done,
                                r.step_p_done, r.step_l_done])
        _attach_employee(r, db)
    return records


@router.post("/promotion", response_model=PromotionResponse, status_code=201)
def create_promotion(payload: PromotionCreate, db: Session = Depends(get_db)):
    _get_employee_or_404(payload.employee_id, db)
    data = payload.model_dump()
    # Auto-compute salary_increase_percent if not supplied
    if (
        data.get("current_salary")
        and data.get("revised_salary")
        and not data.get("salary_increase_percent")
    ):
        cur = float(data["current_salary"])
        rev = float(data["revised_salary"])
        if cur > 0:
            data["salary_increase_percent"] = round((rev - cur) / cur * 100, 2)
    record = Promotion(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    _attach_employee(record, db)
    return record


@router.get("/promotion/{promotion_id}", response_model=PromotionResponse)
def get_promotion(promotion_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Promotion record not found")
    record.approval_step = sum([record.step_m_done, record.step_d_done, record.step_h_done,
                                 record.step_p_done, record.step_l_done])
    _attach_employee(record, db)
    return record


@router.patch("/promotion/{promotion_id}", response_model=PromotionResponse)
def update_promotion(
    promotion_id: int,
    payload: PromotionUpdate,
    db: Session = Depends(get_db),
):
    record = db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Promotion record not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.approval_step = sum([record.step_m_done, record.step_d_done, record.step_h_done,
                                 record.step_p_done, record.step_l_done])
    db.commit()
    db.refresh(record)
    _attach_employee(record, db)
    return record


@router.delete("/promotion/{promotion_id}", status_code=204)
def delete_promotion(promotion_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Promotion record not found")
    db.delete(record)
    db.commit()


# ── Quick-action: Check Eligibility ──────────────────────────────────────────
@router.get(
    "/promotion/check-eligibility/{employee_id}",
    summary="Check if an employee is eligible for promotion",
)
def check_promotion_eligibility(employee_id: int, db: Session = Depends(get_db)):
    _get_employee_or_404(employee_id, db)
    six_months_ago = date.today() - timedelta(days=180)

    active_probation = db.execute(
        select(ProbationManagement)
        .where(
            and_(
                ProbationManagement.employee_id == employee_id,
                ProbationManagement.status.in_(["In Progress", "At Risk"]),
            )
        )
    ).scalar_one_or_none()

    recent_rejection = db.execute(
        select(Promotion)
        .where(
            and_(
                Promotion.employee_id == employee_id,
                Promotion.status == "Rejected",
                Promotion.created_at >= six_months_ago,
            )
        )
    ).scalar_one_or_none()

    reasons = []
    if active_probation:
        reasons.append("Employee is currently on active probation")
    if recent_rejection:
        reasons.append("Promotion was rejected within the last 6 months")

    return {
        "employee_id": employee_id,
        "eligible": not bool(reasons),
        "reasons": reasons,
    }


# ── Quick-action: Schedule Review ─────────────────────────────────────────────
@router.patch(
    "/promotion/{promotion_id}/schedule-review",
    summary="Set a review date for a promotion",
)
def schedule_promotion_review(
    promotion_id: int,
    review_date: date,
    db: Session = Depends(get_db),
):
    record = db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Promotion record not found")
    record.review_date = review_date
    db.commit()
    return {"message": "Review date scheduled", "review_date": str(review_date)}


# ── Quick-action: Generate Letters ────────────────────────────────────────────
@router.post("/promotion/generate-letters", summary="Generate promotion letters")
def generate_promotion_letters(promotion_ids: List[int], db: Session = Depends(get_db)):
    records = db.execute(
        select(Promotion)
        .where(
            and_(
                Promotion.id.in_(promotion_ids),
                Promotion.status == "Approved",
            )
        )
    ).scalars().all()
    for r in records:
        r.letter_generated = True
    db.commit()
    return {"letters_generated": len(records)}


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 4  ·  BUDDY PROGRAM
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/buddy/dashboard",
    response_model=BuddyDashboard,
    summary="Buddy Program – summary stat cards",
)
def buddy_dashboard(db: Session = Depends(get_db)):
    active = db.execute(
        select(func.count()).select_from(BuddyProgram)
        .where(BuddyProgram.status == "Active")
    ).scalar() or 0

    avg_rating = db.execute(
        select(func.avg(BuddyProgram.rating)).select_from(BuddyProgram)
        .where(BuddyProgram.status == "Active")
    ).scalar() or 0.0

    total_assignments = db.execute(
        select(func.count()).select_from(BuddyAssignment)
    ).scalar() or 0

    total_feedback = db.execute(
        select(func.count()).select_from(BuddyAssignment)
        .where(BuddyAssignment.feedback.isnot(None))
    ).scalar() or 0

    avg_exp = db.execute(
        select(func.avg(BuddyProgram.experience_years)).select_from(BuddyProgram)
        .where(BuddyProgram.status == "Active")
    ).scalar() or 0.0

    cap_row = db.execute(
        select(
            func.sum(BuddyProgram.current_assignments),
            func.sum(BuddyProgram.max_capacity),
        ).select_from(BuddyProgram).where(BuddyProgram.status == "Active")
    ).one_or_none()
    used      = float(cap_row[0] or 0) if cap_row else 0.0
    total_cap = float(cap_row[1] or 1) if cap_row else 1.0
    cap_pct   = round(used / total_cap * 100, 1)

    return BuddyDashboard(
        active_buddies=active,
        avg_rating=round(float(avg_rating), 1),
        total_assignments=total_assignments,
        total_feedback_collected=total_feedback,
        avg_experience_years=round(float(avg_exp), 1),
        capacity_used_pct=cap_pct,
    )


@router.get("/buddy", response_model=List[BuddyResponse])
def list_buddies(
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    search:     Optional[str] = Query(None),
    skip:       int           = Query(0,  ge=0),
    limit:      int           = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = (
        select(BuddyProgram)
        .join(Employee, BuddyProgram.buddy_employee_id == Employee.id)
    )
    if department and department != "All Departments":
        q = q.where(Employee.department == department)
    if location and location != "All Locations":
        q = q.where(Employee.location == location)
    if status and status != "All Status":
        q = q.where(BuddyProgram.status == status)
    if search:
        q = q.where(
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
            )
        )
    records = db.execute(q.offset(skip).limit(limit)).scalars().all()
    for r in records:
        r.capacity_pct = round(
            (r.current_assignments / r.max_capacity * 100) if r.max_capacity > 0 else 0.0, 1
        )
        # Buddy employee info
        try:
            emp = _get_employee_or_404(r.buddy_employee_id, db)
            r.buddy = _employee_dict(emp)
        except HTTPException:
            r.buddy = None
        # New joiners assigned to this buddy
        assignments = db.execute(
            select(BuddyAssignment)
            .where(and_(BuddyAssignment.buddy_id == r.id, BuddyAssignment.is_active == True))  # noqa: E712
        ).scalars().all()
        r.assigned_new_joiners = []
        for a in assignments:
            try:
                nj = _get_employee_or_404(a.new_joiner_employee_id, db)
                r.assigned_new_joiners.append(_employee_dict(nj))
            except HTTPException:
                pass
    return records


@router.post("/buddy", response_model=BuddyResponse, status_code=201)
def create_buddy(payload: BuddyCreate, db: Session = Depends(get_db)):
    _get_employee_or_404(payload.buddy_employee_id, db)
    existing = db.execute(
        select(BuddyProgram).where(BuddyProgram.buddy_employee_id == payload.buddy_employee_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="This employee is already registered as a buddy")
    count = db.execute(select(func.count()).select_from(BuddyProgram)).scalar() or 0
    buddy_code = f"BUD{str(count + 1).zfill(3)}"
    record = BuddyProgram(**payload.model_dump(), buddy_code=buddy_code)
    db.add(record)
    db.commit()
    db.refresh(record)
    record.capacity_pct       = 0.0
    record.buddy              = None
    record.assigned_new_joiners = []
    return record


@router.get("/buddy/{buddy_id}", response_model=BuddyResponse)
def get_buddy(buddy_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(BuddyProgram).where(BuddyProgram.id == buddy_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Buddy not found")
    record.capacity_pct = round(
        (record.current_assignments / record.max_capacity * 100) if record.max_capacity > 0 else 0.0, 1
    )
    try:
        emp = _get_employee_or_404(record.buddy_employee_id, db)
        record.buddy = _employee_dict(emp)
    except HTTPException:
        record.buddy = None
    assignments = db.execute(
        select(BuddyAssignment)
        .where(and_(BuddyAssignment.buddy_id == record.id, BuddyAssignment.is_active == True))  # noqa: E712
    ).scalars().all()
    record.assigned_new_joiners = []
    for a in assignments:
        try:
            nj = _get_employee_or_404(a.new_joiner_employee_id, db)
            record.assigned_new_joiners.append(_employee_dict(nj))
        except HTTPException:
            pass
    return record


@router.patch("/buddy/{buddy_id}", response_model=BuddyResponse)
def update_buddy(buddy_id: int, payload: BuddyUpdate, db: Session = Depends(get_db)):
    record = db.execute(
        select(BuddyProgram).where(BuddyProgram.id == buddy_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Buddy not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    record.capacity_pct       = round(
        (record.current_assignments / record.max_capacity * 100) if record.max_capacity > 0 else 0.0, 1
    )
    record.buddy              = None
    record.assigned_new_joiners = []
    return record


@router.delete("/buddy/{buddy_id}", status_code=204)
def delete_buddy(buddy_id: int, db: Session = Depends(get_db)):
    record = db.execute(
        select(BuddyProgram).where(BuddyProgram.id == buddy_id)
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Buddy not found")
    db.delete(record)
    db.commit()


# ── Assign buddy to a new joiner ──────────────────────────────────────────────
@router.post("/buddy/assign", response_model=BuddyAssignmentResponse, status_code=201)
def assign_buddy(payload: BuddyAssignmentCreate, db: Session = Depends(get_db)):
    buddy = db.execute(
        select(BuddyProgram).where(BuddyProgram.id == payload.buddy_id)
    ).scalar_one_or_none()
    if not buddy:
        raise HTTPException(status_code=404, detail="Buddy not found")
    if buddy.current_assignments >= buddy.max_capacity:
        raise HTTPException(status_code=400, detail="Buddy has reached maximum capacity")
    _get_employee_or_404(payload.new_joiner_employee_id, db)

    assignment = BuddyAssignment(
        **payload.model_dump(),
        assigned_date=payload.assigned_date or date.today(),
    )
    db.add(assignment)
    buddy.current_assignments += 1
    db.commit()
    db.refresh(assignment)
    assignment.new_joiner = None
    return assignment


# ── Quick-action: Auto-Assign ─────────────────────────────────────────────────
@router.post("/buddy/auto-assign", summary="Auto-assign best buddy to a list of new joiners")
def auto_assign_buddy(new_joiner_ids: List[int], db: Session = Depends(get_db)):
    today = date.today()
    assigned, errors = [], []
    for emp_id in new_joiner_ids:
        try:
            _get_employee_or_404(emp_id, db)
            best = db.execute(
                select(BuddyProgram)
                .where(
                    and_(
                        BuddyProgram.status == "Active",
                        BuddyProgram.current_assignments < BuddyProgram.max_capacity,
                    )
                )
                .order_by(BuddyProgram.rating.desc())
            ).scalar_one_or_none()
            if not best:
                errors.append({"employee_id": emp_id, "error": "No available buddy with free capacity"})
                continue
            a = BuddyAssignment(
                buddy_id=best.id,
                new_joiner_employee_id=emp_id,
                assigned_date=today,
                is_active=True,
            )
            db.add(a)
            best.current_assignments += 1
            assigned.append({"employee_id": emp_id, "assigned_buddy_id": best.id,
                              "buddy_code": best.buddy_code})
        except Exception as exc:
            errors.append({"employee_id": emp_id, "error": str(exc)})
    db.commit()
    return {"assigned": assigned, "errors": errors}


# ── Quick-action: Collect Feedback ────────────────────────────────────────────
@router.post("/buddy/feedback", summary="Submit feedback for a buddy assignment")
def collect_buddy_feedback(payload: BuddyFeedbackSubmit, db: Session = Depends(get_db)):
    assignment = db.execute(
        select(BuddyAssignment).where(BuddyAssignment.id == payload.assignment_id)
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment.feedback      = payload.feedback
    assignment.feedback_date = date.today()

    # Update buddy's rolling average rating
    if payload.rating:
        buddy = db.execute(
            select(BuddyProgram).where(BuddyProgram.id == assignment.buddy_id)
        ).scalar_one_or_none()
        if buddy:
            n          = buddy.feedback_count or 0
            old        = float(buddy.rating or 0)
            new_rating = ((old * n) + float(payload.rating)) / (n + 1)
            buddy.rating         = round(new_rating, 1)
            buddy.feedback_count = n + 1

    db.commit()
    return {"message": "Feedback recorded successfully"}


# ── Quick-action: Program Report ──────────────────────────────────────────────
@router.get("/buddy/program-report", summary="Aggregate buddy program report")
def buddy_program_report(db: Session = Depends(get_db)):
    buddies = db.execute(
        select(BuddyProgram).where(BuddyProgram.status == "Active")
    ).scalars().all()
    report = []
    for b in buddies:
        total_a = db.execute(
            select(func.count()).select_from(BuddyAssignment)
            .where(BuddyAssignment.buddy_id == b.id)
        ).scalar() or 0
        total_f = db.execute(
            select(func.count()).select_from(BuddyAssignment)
            .where(and_(BuddyAssignment.buddy_id == b.id,
                         BuddyAssignment.feedback.isnot(None)))
        ).scalar() or 0
        report.append({
            "buddy_id":               b.id,
            "buddy_code":             b.buddy_code,
            "buddy_employee_id":      b.buddy_employee_id,
            "status":                 b.status,
            "total_assignments":      total_a,
            "feedbacks_collected":    total_f,
            "rating":                 float(b.rating) if b.rating else None,
            "capacity_used_pct":      round(
                (b.current_assignments / b.max_capacity * 100) if b.max_capacity > 0 else 0.0, 1
            ),
        })
    return {"buddies": report, "total": len(report)}


# ═════════════════════════════════════════════════════════════════════════════
#  SHARED  ·  FILTER OPTIONS  (departments + locations for dropdowns)
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/filter-options", summary="Dropdown options for Department & Location filters")
def get_filter_options(db: Session = Depends(get_db)):
    departments = db.execute(
        select(Employee.department).distinct().where(Employee.department.isnot(None))
    ).scalars().all()
    locations = db.execute(
        select(Employee.location).distinct().where(Employee.location.isnot(None))
    ).scalars().all()
    return {
        "departments": ["All Departments"] + sorted(departments),
        "locations":   ["All Locations"]   + sorted(locations),
    }
