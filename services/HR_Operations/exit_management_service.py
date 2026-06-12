
from __future__ import annotations

import calendar
import csv
import io
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func, select, and_, extract, case
from sqlalchemy.orm import Session, joinedload

from model.HR_Operations.exit_management import (
    AlumniRecord,
    ClearanceItem,
    ClearanceStatus,
    ClearanceTemplate,
    EngagementLevel,
    ExitCase,
    ExitCaseStatus,
    ExitDocument,
    ExitInterview,
    ExitSettlement,
    ExitType,
    SettlementStatus,
)
from model.Employee_Management.employee_master import EmployeeMaster
from model.onboarding.employee import Employee

import schema.HR_Operations.exit_management as schemas

logger = logging.getLogger(__name__)


def _get_employee_or_404(db: Session, employee_id: int) -> Employee:
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalars().first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    return emp


def _get_exit_case_or_404(db: Session, exit_case_id: int) -> ExitCase:
    ec = db.execute(
        select(ExitCase).where(ExitCase.id == exit_case_id)
    ).scalars().first()
    if not ec:
        raise HTTPException(status_code=404, detail=f"Exit case {exit_case_id} not found")
    return ec


def _get_master(db: Session, employee_id: int) -> Optional[EmployeeMaster]:
    return db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalars().first()


def _full_name(emp: Employee) -> str:
    parts = [emp.first_name, getattr(emp, "middle_name", None), emp.last_name]
    return " ".join(p for p in parts if p).strip()


def _tenure_months(joining_date: date, end_date: date) -> int:
    delta = (end_date.year - joining_date.year) * 12 + (end_date.month - joining_date.month)
    return max(0, delta)


def _calc_gratuity(basic_salary: Decimal, tenure_months: int) -> Decimal:

    if tenure_months < 60:
        return Decimal("0")
    years = Decimal(str(tenure_months)) / Decimal("12")
    gratuity = (basic_salary * Decimal("15") / Decimal("26")) * years
    return gratuity.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _recalc_settlement_totals(s: ExitSettlement) -> ExitSettlement:
  
    s.total_earnings = (
        (s.last_month_salary or Decimal("0"))
        + (s.leave_encashment_amount or Decimal("0"))
        + (s.gratuity_amount or Decimal("0"))
        + (s.bonus_amount or Decimal("0"))
        + (s.pending_reimbursements or Decimal("0"))
        + (s.other_earnings or Decimal("0"))
    )
    s.total_deductions = (
        (s.notice_recovery_amount or Decimal("0"))
        + (s.loan_recovery or Decimal("0"))
        + (s.asset_recovery or Decimal("0"))
        + (s.tds_deduction or Decimal("0"))
        + (s.other_deductions or Decimal("0"))
    )
    s.net_payable = s.total_earnings - s.total_deductions
    return s


def _clearance_progress(items: List[ClearanceItem]) -> int:
  
    if not items:
        return 0
    done = sum(1 for i in items if i.status in (ClearanceStatus.COMPLETED, ClearanceStatus.WAIVED))
    return int(done / len(items) * 100)


def _pending_count(items: List[ClearanceItem]) -> int:
    return sum(1 for i in items if i.status == ClearanceStatus.PENDING)


def _enrich_exit_case(db: Session, ec: ExitCase) -> schemas.ExitCaseListItem:
    emp = db.execute(select(Employee).where(Employee.id == ec.employee_id)).scalars().first()
    master = _get_master(db, ec.employee_id) if emp else None
    items = db.execute(
        select(ClearanceItem).where(ClearanceItem.exit_case_id == ec.id)
    ).scalars().all()

    return schemas.ExitCaseListItem(
        id=ec.id,
        employee_id=ec.employee_id,
        employee_name=_full_name(emp) if emp else None,
        employee_code=getattr(emp, "employee_code", None),
        department=getattr(master, "department", None) if master else None,
        designation=getattr(master, "designation", None) if master else None,
        location=getattr(master, "work_location", None) if master else None,
        exit_type=ec.exit_type,
        resignation_date=ec.resignation_date,
        last_working_date=ec.last_working_date,
        exit_reason=ec.exit_reason,
        status=ec.status,
        clearance_status=ec.clearance_status,
        clearance_progress=_clearance_progress(list(items)),
        pending_items_count=_pending_count(list(items)),
        exit_interview_done=ec.exit_interview_done,
        created_at=ec.created_at,
    )
def get_exit_case_kpi(db: Session) -> schemas.ExitKPISummary:
  
    total = db.execute(select(func.count()).select_from(ExitCase)).scalar() or 0
    pending = db.execute(
        select(func.count()).select_from(ExitCase)
        .where(ExitCase.status.in_([ExitCaseStatus.INITIATED, ExitCaseStatus.IN_PROGRESS]))
    ).scalar() or 0
    completed = db.execute(
        select(func.count()).select_from(ExitCase)
        .where(ExitCase.status == ExitCaseStatus.COMPLETED)
    ).scalar() or 0
    alumni = db.execute(select(func.count()).select_from(AlumniRecord)).scalar() or 0

    today = date.today()
    escalated = db.execute(
        select(func.count()).select_from(ExitCase).where(
            and_(
                ExitCase.status == ExitCaseStatus.IN_PROGRESS,
                ExitCase.last_working_date < today,
                ExitCase.clearance_status != ClearanceStatus.COMPLETED,
            )
        )
    ).scalar() or 0

    one_year_ago = date(today.year - 1, today.month, today.day)
    exits_ytd = db.execute(
        select(func.count()).select_from(ExitCase)
        .where(ExitCase.resignation_date >= one_year_ago)
    ).scalar() or 0
    total_employees = db.execute(select(func.count()).select_from(Employee)).scalar() or 1
    exit_rate = round((exits_ytd / total_employees) * 100, 1)

    tenures = db.execute(
        select(Employee.joining_date, ExitCase.last_working_date)
        .join(ExitCase, ExitCase.employee_id == Employee.id)
        .where(ExitCase.last_working_date.isnot(None))
    ).all()
    if tenures:
        months = [_tenure_months(r.joining_date, r.last_working_date) for r in tenures if r.joining_date]
        avg_tenure = round(sum(months) / len(months), 1) if months else 0.0
    else:
        avg_tenure = 0.0

    reason_row = db.execute(
        select(ExitCase.exit_reason, func.count().label("cnt"))
        .where(ExitCase.exit_reason.isnot(None))
        .group_by(ExitCase.exit_reason)
        .order_by(func.count().desc())
        .limit(1)
    ).first()
    top_reason = reason_row[0] if reason_row else None

    pending_settlements = db.execute(
        select(func.count()).select_from(ExitSettlement)
        .where(ExitSettlement.settlement_status.in_(
            [SettlementStatus.DRAFT, SettlementStatus.PENDING_APPROVAL]
        ))
    ).scalar() or 0

    return schemas.ExitKPISummary(
        total_cases=total,
        pending_cases=pending,
        escalated_cases=escalated,
        completed_cases=completed,
        alumni_count=alumni,
        exit_rate_percent=exit_rate,
        avg_tenure_months=avg_tenure,
        top_exit_reason=top_reason,
        pending_settlements=pending_settlements,
        avg_clearance_days=None, 
    )


def list_exit_cases(
    db: Session,
    status: Optional[str] = None,
    department: Optional[str] = None,
    exit_reason: Optional[str] = None,
    location: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> schemas.PaginatedExitCases:
 
    q = select(ExitCase)

    if status:
        q = q.where(ExitCase.status == status)
    if exit_reason:
        q = q.where(ExitCase.exit_reason == exit_reason)
    if from_date:
        q = q.where(ExitCase.resignation_date >= from_date)
    if to_date:
        q = q.where(ExitCase.resignation_date <= to_date)

    q = q.order_by(ExitCase.created_at.desc())

    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    cases_raw = db.execute(q.offset((page - 1) * page_size).limit(page_size)).scalars().all()

    items = [_enrich_exit_case(db, ec) for ec in cases_raw]

    if department:
        items = [i for i in items if i.department and department.lower() in i.department.lower()]
    if location:
        items = [i for i in items if i.location and location.lower() in i.location.lower()]
    if search:
        s = search.lower()
        items = [
            i for i in items
            if (i.employee_name and s in i.employee_name.lower())
            or (i.employee_code and s in i.employee_code.lower())
        ]

    return schemas.PaginatedExitCases(total=total, page=page, page_size=page_size, items=items)


def get_exit_case_detail(db: Session, exit_case_id: int) -> schemas.ExitCaseDetailResponse:
    ec = db.execute(
        select(ExitCase)
        .options(
            joinedload(ExitCase.clearance_items),
            joinedload(ExitCase.settlement),
            joinedload(ExitCase.exit_interview),
            joinedload(ExitCase.alumni_record),
            joinedload(ExitCase.documents),
        )
        .where(ExitCase.id == exit_case_id)
    ).unique().scalars().first()
    if not ec:
        raise HTTPException(status_code=404, detail="Exit case not found")

    emp = db.execute(select(Employee).where(Employee.id == ec.employee_id)).scalars().first()
    master = _get_master(db, ec.employee_id) if emp else None
    today = date.today()

    return schemas.ExitCaseDetailResponse(
        **schemas.ExitCaseResponse.model_validate(ec).model_dump(),
        employee_name=_full_name(emp) if emp else None,
        employee_code=getattr(emp, "employee_code", None),
        department=getattr(master, "department", None) if master else None,
        designation=getattr(master, "designation", None) if master else None,
        location=getattr(master, "work_location", None) if master else None,
        joining_date=getattr(emp, "joining_date", None),
        tenure_months=_tenure_months(emp.joining_date, today) if emp and emp.joining_date else None,
        clearance_items=[schemas.ClearanceItemResponse.model_validate(i) for i in (ec.clearance_items or [])],
        settlement=schemas.ExitSettlementResponse.model_validate(ec.settlement) if ec.settlement else None,
        exit_interview=schemas.ExitInterviewResponse.model_validate(ec.exit_interview) if ec.exit_interview else None,
        alumni_record=schemas.AlumniRecordResponse.model_validate(ec.alumni_record) if ec.alumni_record else None,
        documents=[schemas.ExitDocumentResponse.model_validate(d) for d in (ec.documents or [])],
    )


def initiate_exit(
    db: Session,
    payload: schemas.ExitCaseCreate,
    initiated_by: Optional[int] = None,
) -> schemas.InitiateExitResponse:

    _get_employee_or_404(db, payload.employee_id)

    existing = db.execute(
        select(ExitCase).where(
            and_(
                ExitCase.employee_id == payload.employee_id,
                ExitCase.status.in_([ExitCaseStatus.INITIATED, ExitCaseStatus.IN_PROGRESS]),
            )
        )
    ).scalars().first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Active exit case #{existing.id} already exists for this employee",
        )

    master = _get_master(db, payload.employee_id)
    notice_days = getattr(master, "notice_period_days", 30) or 30
    expected_last = payload.resignation_date + timedelta(days=notice_days)

    ec = ExitCase(
        employee_id=payload.employee_id,
        exit_type=payload.exit_type,
        resignation_date=payload.resignation_date,
        last_working_date=payload.last_working_date,
        expected_last_day=expected_last,
        exit_reason=payload.exit_reason,
        reason_detail=payload.reason_detail,
        status=ExitCaseStatus.INITIATED,
        clearance_status=ClearanceStatus.PENDING,
        initiated_by=initiated_by,
        remarks=payload.remarks,
    )
    db.add(ec)
    db.flush() 
    templates = db.execute(
        select(ClearanceTemplate).where(ClearanceTemplate.is_active == True)
        .order_by(ClearanceTemplate.sort_order)
    ).scalars().all()

    for tmpl in templates:
        item = ClearanceItem(
            exit_case_id=ec.id,
            department=tmpl.department,
            item_name=tmpl.item_name,
            is_mandatory=tmpl.is_mandatory,
            sort_order=tmpl.sort_order,
            status=ClearanceStatus.PENDING,
        )
        db.add(item)

    db.commit()
    db.refresh(ec)
    logger.info("Exit case %d initiated for employee %d", ec.id, payload.employee_id)

    return schemas.InitiateExitResponse(
        exit_case=schemas.ExitCaseResponse.model_validate(ec),
        clearance_items_created=len(templates),
        message=f"Exit case initiated successfully. {len(templates)} clearance items created.",
    )


def update_exit_case(
    db: Session,
    exit_case_id: int,
    payload: schemas.ExitCaseUpdate,
) -> schemas.ExitCaseResponse:
    ec = _get_exit_case_or_404(db, exit_case_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ec, field, value)

    if ec.status == ExitCaseStatus.IN_PROGRESS and ec.clearance_status == ClearanceStatus.PENDING:
        ec.clearance_status = ClearanceStatus.IN_PROGRESS

    db.commit()
    db.refresh(ec)
    return schemas.ExitCaseResponse.model_validate(ec)


def close_exit_case(
    db: Session,
    exit_case_id: int,
    payload: schemas.CloseExitRequest,
) -> schemas.ExitCaseResponse:

    ec = _get_exit_case_or_404(db, exit_case_id)

    pending_mandatory = db.execute(
        select(ClearanceItem).where(
            and_(
                ClearanceItem.exit_case_id == exit_case_id,
                ClearanceItem.is_mandatory == True,
                ClearanceItem.status.not_in([ClearanceStatus.COMPLETED, ClearanceStatus.WAIVED]),
            )
        )
    ).scalars().all()

    if pending_mandatory:
        names = ", ".join(i.item_name for i in pending_mandatory[:5])
        raise HTTPException(
            status_code=422,
            detail=f"Cannot close: {len(pending_mandatory)} mandatory clearance item(s) pending: {names}",
        )

    ec.status = ExitCaseStatus.COMPLETED
    ec.clearance_status = ClearanceStatus.COMPLETED
    if payload.remarks:
        ec.remarks = payload.remarks
    existing_alumni = db.execute(
        select(AlumniRecord).where(AlumniRecord.exit_case_id == exit_case_id)
    ).scalars().first()
    if not existing_alumni:
        alumni = AlumniRecord(
            exit_case_id=exit_case_id,
            employee_id=ec.employee_id,
            rehire_eligible=True,
            engagement_level=EngagementLevel.MEDIUM,
        )
        db.add(alumni)

    db.commit()
    db.refresh(ec)
    logger.info("Exit case %d closed for employee %d", ec.id, ec.employee_id)
    return schemas.ExitCaseResponse.model_validate(ec)


def cancel_exit_case(db: Session, exit_case_id: int, remarks: Optional[str] = None) -> schemas.ExitCaseResponse:
    ec = _get_exit_case_or_404(db, exit_case_id)
    if ec.status == ExitCaseStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Cannot cancel a completed exit case")
    ec.status = ExitCaseStatus.CANCELLED
    if remarks:
        ec.remarks = remarks
    db.commit()
    db.refresh(ec)
    return schemas.ExitCaseResponse.model_validate(ec)


def delete_exit_case(db: Session, exit_case_id: int) -> Dict[str, str]:
    ec = _get_exit_case_or_404(db, exit_case_id)
    if ec.status not in (ExitCaseStatus.INITIATED, ExitCaseStatus.CANCELLED):
        raise HTTPException(status_code=409, detail="Only Initiated or Cancelled exit cases can be deleted")
    db.delete(ec)
    db.commit()
    return {"message": f"Exit case {exit_case_id} deleted successfully"}


def list_clearance_items(db: Session, exit_case_id: int) -> List[schemas.ClearanceItemResponse]:
    _get_exit_case_or_404(db, exit_case_id)
    items = db.execute(
        select(ClearanceItem)
        .where(ClearanceItem.exit_case_id == exit_case_id)
        .order_by(ClearanceItem.sort_order, ClearanceItem.department)
    ).scalars().all()
    return [schemas.ClearanceItemResponse.model_validate(i) for i in items]


def update_clearance_item(
    db: Session,
    item_id: int,
    payload: schemas.ClearanceItemUpdate,
) -> schemas.ClearanceItemResponse:
    item = db.execute(select(ClearanceItem).where(ClearanceItem.id == item_id)).scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Clearance item not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    if payload.status == ClearanceStatus.COMPLETED and not item.completed_at:
        item.completed_at = datetime.utcnow()

    db.commit()

    # Refresh exit case clearance_status
    _refresh_case_clearance_status(db, item.exit_case_id)
    db.refresh(item)
    return schemas.ClearanceItemResponse.model_validate(item)


def bulk_update_clearance_items(
    db: Session,
    payload: schemas.BulkClearanceUpdateRequest,
) -> Dict[str, Any]:
    updated = 0
    for item_id in payload.item_ids:
        item = db.execute(select(ClearanceItem).where(ClearanceItem.id == item_id)).scalars().first()
        if item:
            item.status = payload.status
            if payload.remarks:
                item.remarks = payload.remarks
            if payload.status == ClearanceStatus.COMPLETED and not item.completed_at:
                item.completed_at = datetime.utcnow()
            updated += 1

    db.commit()
    return {"updated_count": updated, "message": f"{updated} clearance item(s) updated"}


def _refresh_case_clearance_status(db: Session, exit_case_id: int) -> None:

    items = db.execute(
        select(ClearanceItem).where(ClearanceItem.exit_case_id == exit_case_id)
    ).scalars().all()
    if not items:
        return
    progress = _clearance_progress(list(items))
    ec = db.execute(select(ExitCase).where(ExitCase.id == exit_case_id)).scalars().first()
    if not ec:
        return
    if progress == 100:
        ec.clearance_status = ClearanceStatus.COMPLETED
    elif progress > 0:
        ec.clearance_status = ClearanceStatus.IN_PROGRESS
    db.commit()


def create_exit_interview(
    db: Session,
    payload: schemas.ExitInterviewCreate,
) -> schemas.ExitInterviewResponse:
    _get_exit_case_or_404(db, payload.exit_case_id)
    existing = db.execute(
        select(ExitInterview).where(ExitInterview.exit_case_id == payload.exit_case_id)
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Exit interview already exists for this case")

    interview = ExitInterview(
        **{k: v for k, v in payload.model_dump().items() if k != "responses"},
        responses=[r.model_dump() for r in payload.responses],
    )
    db.add(interview)

    # Mark interview done on parent case
    ec = _get_exit_case_or_404(db, payload.exit_case_id)
    ec.exit_interview_done = True
    if payload.interview_date:
        ec.exit_interview_date = payload.interview_date

    db.commit()
    db.refresh(interview)
    return schemas.ExitInterviewResponse.model_validate(interview)


def update_exit_interview(
    db: Session,
    interview_id: int,
    payload: schemas.ExitInterviewUpdate,
) -> schemas.ExitInterviewResponse:
    interview = db.execute(select(ExitInterview).where(ExitInterview.id == interview_id)).scalars().first()
    if not interview:
        raise HTTPException(status_code=404, detail="Exit interview not found")

    data = payload.model_dump(exclude_unset=True)
    if "responses" in data and data["responses"] is not None:
        data["responses"] = [r.model_dump() if hasattr(r, "model_dump") else r for r in data["responses"]]

    for field, value in data.items():
        setattr(interview, field, value)

    db.commit()
    db.refresh(interview)
    return schemas.ExitInterviewResponse.model_validate(interview)


def get_exit_interview(db: Session, exit_case_id: int) -> schemas.ExitInterviewResponse:
    interview = db.execute(
        select(ExitInterview).where(ExitInterview.exit_case_id == exit_case_id)
    ).scalars().first()
    if not interview:
        raise HTTPException(status_code=404, detail="Exit interview not found for this case")
    return schemas.ExitInterviewResponse.model_validate(interview)


def auto_calculate_settlement(
    db: Session,
    req: schemas.SettlementCalculateRequest,
) -> schemas.ExitSettlementCreate:

    ec = _get_exit_case_or_404(db, req.exit_case_id)
    emp = _get_employee_or_404(db, ec.employee_id)
    master = _get_master(db, ec.employee_id)

    basic = req.override_basic_salary or (
        Decimal(str(master.salary)) if master and master.salary else Decimal("0")
    )

    last_day = ec.last_working_date or date.today()
    joining = getattr(emp, "joining_date", None) or date.today()
    tenure_months = _tenure_months(joining, last_day)

    gratuity = _calc_gratuity(basic, tenure_months)

    # Notice shortfall
    contractual_notice = getattr(master, "notice_period_days", 30) or 30
    if ec.resignation_date and ec.last_working_date:
        actual_notice_days = (ec.last_working_date - ec.resignation_date).days
    else:
        actual_notice_days = contractual_notice
    shortfall_days = max(0, contractual_notice - actual_notice_days)
    daily_basic = basic / Decimal("30")
    notice_recovery = (daily_basic * Decimal(str(shortfall_days))).quantize(Decimal("0.01"))

    return schemas.ExitSettlementCreate(
        exit_case_id=req.exit_case_id,
        employee_id=ec.employee_id,
        basic_salary=basic,
        last_month_salary=basic,
        gratuity_amount=gratuity,
        notice_period_shortfall_days=shortfall_days,
        notice_recovery_amount=notice_recovery,
    )


def create_settlement(
    db: Session,
    payload: schemas.ExitSettlementCreate,
) -> schemas.ExitSettlementResponse:
    _get_exit_case_or_404(db, payload.exit_case_id)
    existing = db.execute(
        select(ExitSettlement).where(ExitSettlement.exit_case_id == payload.exit_case_id)
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Settlement already exists for this exit case")

    s = ExitSettlement(**payload.model_dump())
    s = _recalc_settlement_totals(s)
    db.add(s)
    db.commit()
    db.refresh(s)
    return schemas.ExitSettlementResponse.model_validate(s)


def update_settlement(
    db: Session,
    settlement_id: int,
    payload: schemas.ExitSettlementUpdate,
) -> schemas.ExitSettlementResponse:
    s = db.execute(select(ExitSettlement).where(ExitSettlement.id == settlement_id)).scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="Settlement not found")
    if s.settlement_status == SettlementStatus.PAID:
        raise HTTPException(status_code=409, detail="Cannot edit a paid settlement")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(s, field, value)

    s = _recalc_settlement_totals(s)
    db.commit()
    db.refresh(s)
    return schemas.ExitSettlementResponse.model_validate(s)


def approve_settlement(
    db: Session,
    settlement_id: int,
    payload: schemas.ApproveSettlementRequest,
) -> schemas.ExitSettlementResponse:
    s = db.execute(select(ExitSettlement).where(ExitSettlement.id == settlement_id)).scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="Settlement not found")
    if s.settlement_status not in (SettlementStatus.DRAFT, SettlementStatus.PENDING_APPROVAL):
        raise HTTPException(status_code=409, detail=f"Settlement already {s.settlement_status}")

    s.settlement_status = SettlementStatus.APPROVED
    s.approved_by_id = payload.approved_by_id
    s.approved_at = datetime.utcnow()
    if payload.payment_reference:
        s.payment_reference = payload.payment_reference
    if payload.payment_date:
        s.payment_date = payload.payment_date
    if payload.remarks:
        s.remarks = payload.remarks

    db.commit()
    db.refresh(s)
    return schemas.ExitSettlementResponse.model_validate(s)


def mark_settlement_paid(
    db: Session,
    settlement_id: int,
    payment_reference: str,
    payment_date: Optional[date] = None,
) -> schemas.ExitSettlementResponse:
    s = db.execute(select(ExitSettlement).where(ExitSettlement.id == settlement_id)).scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="Settlement not found")
    if s.settlement_status != SettlementStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Settlement must be Approved before marking as Paid")

    s.settlement_status = SettlementStatus.PAID
    s.payment_reference = payment_reference
    s.payment_date = payment_date or date.today()
    db.commit()
    db.refresh(s)
    return schemas.ExitSettlementResponse.model_validate(s)


def list_settlements(
    db: Session,
    department: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> schemas.PaginatedSettlements:
    q = select(ExitSettlement).order_by(ExitSettlement.created_at.desc())
    if status:
        q = q.where(ExitSettlement.settlement_status == status)

    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    records = db.execute(q.offset((page - 1) * page_size).limit(page_size)).scalars().all()

    items = []
    for s in records:
        emp = db.execute(select(Employee).where(Employee.id == s.employee_id)).scalars().first()
        master = _get_master(db, s.employee_id) if emp else None
        item = schemas.SettlementListItem(
            id=s.id,
            exit_case_id=s.exit_case_id,
            employee_id=s.employee_id,
            employee_name=_full_name(emp) if emp else None,
            employee_code=getattr(emp, "employee_code", None),
            department=getattr(master, "department", None) if master else None,
            net_payable=s.net_payable,
            payment_date=s.payment_date,
            settlement_status=s.settlement_status,
            created_at=s.created_at,
        )
        items.append(item)

    if department:
        items = [i for i in items if i.department and department.lower() in i.department.lower()]
    if search:
        s_lower = search.lower()
        items = [
            i for i in items
            if (i.employee_name and s_lower in i.employee_name.lower())
            or (i.employee_code and s_lower in i.employee_code.lower())
        ]

    return schemas.PaginatedSettlements(total=total, page=page, page_size=page_size, items=items)


def list_alumni(
    db: Session,
    department: Optional[str] = None,
    rehire_eligible: Optional[bool] = None,
    engagement_level: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> schemas.PaginatedAlumni:
    q = select(AlumniRecord)
    if rehire_eligible is not None:
        q = q.where(AlumniRecord.rehire_eligible == rehire_eligible)
    if engagement_level:
        q = q.where(AlumniRecord.engagement_level == engagement_level)

    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    records = db.execute(
        q.order_by(AlumniRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    items = []
    for alumni in records:
        emp = db.execute(select(Employee).where(Employee.id == alumni.employee_id)).scalars().first()
        master = _get_master(db, alumni.employee_id) if emp else None
        ec = db.execute(select(ExitCase).where(ExitCase.id == alumni.exit_case_id)).scalars().first()
        item = schemas.AlumniListItem(
            id=alumni.id,
            employee_id=alumni.employee_id,
            employee_name=_full_name(emp) if emp else None,
            employee_code=getattr(emp, "employee_code", None),
            department=getattr(master, "department", None) if master else None,
            exit_date=ec.last_working_date if ec else None,
            rehire_eligible=alumni.rehire_eligible,
            boomerang_interest=alumni.boomerang_interest,
            engagement_level=alumni.engagement_level,
            blacklisted=alumni.blacklisted,
        )
        items.append(item)

    if department:
        items = [i for i in items if i.department and department.lower() in i.department.lower()]
    if search:
        s = search.lower()
        items = [
            i for i in items
            if (i.employee_name and s in i.employee_name.lower())
            or (i.employee_code and s in i.employee_code.lower())
        ]

    return schemas.PaginatedAlumni(total=total, page=page, page_size=page_size, items=items)


def get_alumni_record(db: Session, alumni_id: int) -> schemas.AlumniRecordResponse:
    alumni = db.execute(select(AlumniRecord).where(AlumniRecord.id == alumni_id)).scalars().first()
    if not alumni:
        raise HTTPException(status_code=404, detail="Alumni record not found")
    return schemas.AlumniRecordResponse.model_validate(alumni)


def create_alumni_record(
    db: Session, payload: schemas.AlumniRecordCreate
) -> schemas.AlumniRecordResponse:
    _get_exit_case_or_404(db, payload.exit_case_id)
    existing = db.execute(
        select(AlumniRecord).where(AlumniRecord.exit_case_id == payload.exit_case_id)
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Alumni record already exists for this exit case")

    alumni = AlumniRecord(**payload.model_dump())
    db.add(alumni)
    db.commit()
    db.refresh(alumni)
    return schemas.AlumniRecordResponse.model_validate(alumni)


def update_alumni_record(
    db: Session, alumni_id: int, payload: schemas.AlumniRecordUpdate
) -> schemas.AlumniRecordResponse:
    alumni = db.execute(select(AlumniRecord).where(AlumniRecord.id == alumni_id)).scalars().first()
    if not alumni:
        raise HTTPException(status_code=404, detail="Alumni record not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(alumni, field, value)

    db.commit()
    db.refresh(alumni)
    return schemas.AlumniRecordResponse.model_validate(alumni)


def get_trend_analysis(
    db: Session,
    months: int = 3,
    department: Optional[str] = None,
) -> schemas.TrendAnalysisResponse:

    today = date.today()
    start_date = date(today.year, today.month, 1) - timedelta(days=30 * (months - 1))
    start_date = date(start_date.year, start_date.month, 1)

    q = select(ExitCase).where(ExitCase.resignation_date >= start_date)
    cases = db.execute(q).scalars().all()

    if department and department.lower() != "all departments":
        filtered = []
        for ec in cases:
            master = _get_master(db, ec.employee_id)
            if master and getattr(master, "department", None) == department:
                filtered.append(ec)
        cases = filtered

    total = len(cases)
    total_employees = db.execute(select(func.count()).select_from(Employee)).scalar() or 1
    exit_rate = round((total / total_employees) * 100, 1)

    tenures_months = []
    for ec in cases:
        emp = db.execute(select(Employee).where(Employee.id == ec.employee_id)).scalars().first()
        if emp and emp.joining_date and ec.last_working_date:
            tenures_months.append(_tenure_months(emp.joining_date, ec.last_working_date))
    avg_tenure = round(sum(tenures_months) / len(tenures_months), 1) if tenures_months else 0.0

    monthly: Dict[str, Dict] = {}
    for ec in cases:
        key = ec.resignation_date.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = {"exit_count": 0, "exit_type_breakdown": {}}
        monthly[key]["exit_count"] += 1
        monthly[key]["exit_type_breakdown"][ec.exit_type] = (
            monthly[key]["exit_type_breakdown"].get(ec.exit_type, 0) + 1
        )

    monthly_trends = [
        schemas.MonthlyTrend(month=k, **v) for k, v in sorted(monthly.items())
    ]

    type_breakdown: Dict[str, int] = {}
    for ec in cases:
        type_breakdown[ec.exit_type] = type_breakdown.get(ec.exit_type, 0) + 1

    reason_breakdown: Dict[str, int] = {}
    for ec in cases:
        if ec.exit_reason:
            reason_breakdown[ec.exit_reason] = reason_breakdown.get(ec.exit_reason, 0) + 1

    top_reason = max(reason_breakdown, key=lambda k: reason_breakdown[k]) if reason_breakdown else None

    dept_map: Dict[str, List[ExitCase]] = {}
    for ec in cases:
        master = _get_master(db, ec.employee_id)
        dept = getattr(master, "department", "Unknown") if master else "Unknown"
        dept_map.setdefault(dept, []).append(ec)

    dept_stats = []
    for dept, dept_cases in dept_map.items():
        dept_reasons: Dict[str, int] = {}
        for ec in dept_cases:
            if ec.exit_reason:
                dept_reasons[ec.exit_reason] = dept_reasons.get(ec.exit_reason, 0) + 1
        dept_top = max(dept_reasons, key=lambda k: dept_reasons[k]) if dept_reasons else None
        dept_stats.append(
            schemas.DepartmentExitStat(
                department=dept,
                total_exits=len(dept_cases),
                exit_rate=round(len(dept_cases) / total * 100, 1) if total else 0.0,
                top_reason=dept_top,
            )
        )

    period_map = {3: "Last 3 Months", 6: "Last 6 Months", 12: "Last 12 Months"}
    period_label = period_map.get(months, f"Last {months} Months")

    return schemas.TrendAnalysisResponse(
        period_label=period_label,
        total_exits=total,
        exit_rate_percent=exit_rate,
        avg_tenure_months=avg_tenure,
        top_exit_reason=top_reason,
        monthly_trends=monthly_trends,
        department_stats=dept_stats,
        exit_type_breakdown=type_breakdown,
        reason_breakdown=reason_breakdown,
    )


def list_clearance_templates(db: Session) -> List[schemas.ClearanceTemplateResponse]:
    templates = db.execute(
        select(ClearanceTemplate).order_by(ClearanceTemplate.sort_order, ClearanceTemplate.department)
    ).scalars().all()
    return [schemas.ClearanceTemplateResponse.model_validate(t) for t in templates]


def create_clearance_template(
    db: Session, payload: schemas.ClearanceTemplateCreate
) -> schemas.ClearanceTemplateResponse:
    template = ClearanceTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return schemas.ClearanceTemplateResponse.model_validate(template)


def update_clearance_template(
    db: Session, template_id: int, payload: schemas.ClearanceTemplateUpdate
) -> schemas.ClearanceTemplateResponse:
    t = db.execute(select(ClearanceTemplate).where(ClearanceTemplate.id == template_id)).scalars().first()
    if not t:
        raise HTTPException(status_code=404, detail="Clearance template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    db.commit()
    db.refresh(t)
    return schemas.ClearanceTemplateResponse.model_validate(t)


def delete_clearance_template(db: Session, template_id: int) -> Dict[str, str]:
    t = db.execute(select(ClearanceTemplate).where(ClearanceTemplate.id == template_id)).scalars().first()
    if not t:
        raise HTTPException(status_code=404, detail="Clearance template not found")
    db.delete(t)
    db.commit()
    return {"message": f"Clearance template {template_id} deleted"}


def export_exit_cases_csv(
    db: Session,
    status: Optional[str] = None,
    department: Optional[str] = None,
) -> str:
    result = list_exit_cases(db, status=status, department=department, page=1, page_size=10000)
    output = io.StringIO()
    fields = [
        "id", "employee_code", "employee_name", "department",
        "designation", "exit_type", "resignation_date", "last_working_date",
        "exit_reason", "status", "clearance_status",
        "clearance_progress", "exit_interview_done", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for item in result.items:
        row = item.model_dump()
        row["resignation_date"] = str(row["resignation_date"])
        row["last_working_date"] = str(row["last_working_date"]) if row["last_working_date"] else ""
        row["created_at"] = str(row["created_at"])
        writer.writerow(row)
    return output.getvalue()


def export_settlements_csv(db: Session, status: Optional[str] = None) -> str:
    result = list_settlements(db, status=status, page=1, page_size=10000)
    output = io.StringIO()
    fields = [
        "id", "employee_code", "employee_name", "department",
        "net_payable", "payment_date", "settlement_status", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for item in result.items:
        row = item.model_dump()
        row["payment_date"] = str(row["payment_date"]) if row["payment_date"] else ""
        row["created_at"] = str(row["created_at"])
        writer.writerow(row)
    return output.getvalue()
