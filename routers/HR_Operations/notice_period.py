"""
routers/HR_Operations/notice_period.py

Notice Period Tracking & Management — full backend matching the dashboard:

  AI Dashboard         : active cases / pending approvals / AI time saved / retention success
  Active Cases         : list of all notice period cases (Daily Countdown Tracker)
  Resignation Workflow : Submit Resignation modal -> AI retention prediction
  Buyout Requests      : raise / approve (Manager/HR/Finance) / reject
  Waiver Requests      : raise (with documents) / approve (Manager/HR/Director) / reject
  Counter Offers       : raise -> AI retention probability -> accept / reject
  Extension Requests   : raise / approve (Manager/HR) / reject
  Calculators           : LWD / Buyout / Waiver / Shortfall
  Export Reports        : JSON / CSV / PDF / EXCEL
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db
from model.HR_Operations.notice_period import (
    NoticePeriod,
    ResignationSubmission,
    BuyoutRequest,
    WaiverRequest,
    WaiverDocument,
    CounterOffer,
    ExtensionRequest,
)
from model.onboarding.employee import Employee
from schema.HR_Operations.notice_period import (
    NoticePeriodCreate,
    NoticePeriodUpdate,
    NoticePeriodResponse,
    ResignationSubmissionCreate,
    ResignationSubmissionResponse,
    BuyoutRequestCreate,
    BuyoutApprovalAction,
    BuyoutRequestResponse,
    WaiverRequestCreate,
    WaiverApprovalAction,
    WaiverRequestResponse,
    WaiverDocumentResponse,
    CounterOfferCreate,
    CounterOfferDecision,
    CounterOfferResponse,
    ExtensionRequestCreate,
    ExtensionApprovalAction,
    ExtensionRequestResponse,
    LWDCalculatorRequest,
    LWDCalculatorResponse,
    BuyoutCalculatorRequest,
    BuyoutCalculatorResponse,
    WaiverCalculatorRequest,
    WaiverCalculatorResponse,
    ShortfallCalculatorRequest,
    ShortfallCalculatorResponse,
    NoticePeriodDashboardStats,
)
from services.notice_period_service import (
    ai_predict_resignation_retention,
    ai_predict_counter_offer_retention,
    calculate_lwd,
    calculate_buyout,
    calculate_after_waiver,
    calculate_shortfall,
    save_waiver_document,
    get_dashboard_stats,
    export_reports_json,
    export_reports_csv,
    export_reports_excel,
    export_reports_pdf,
)

router = APIRouter(prefix="/api/hr-operations/notice-period", tags=["HR Operations - Notice Period"])


# ======================================================
# HELPERS
# ======================================================
def _get_employee_or_404(db: Session, employee_id: int) -> Employee:
    employee = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


def _get_notice_period_or_404(db: Session, notice_period_id: int) -> NoticePeriod:
    np = db.execute(select(NoticePeriod).where(NoticePeriod.id == notice_period_id)).scalar_one_or_none()
    if not np:
        raise HTTPException(status_code=404, detail="Notice period case not found")
    return np


def _employee_mini(employee: Optional[Employee]) -> Optional[dict]:
    if not employee:
        return None
    full_name = " ".join(p for p in [employee.first_name, employee.middle_name, employee.last_name] if p)
    return {
        "id": employee.id,
        "employee_code": employee.employee_code,
        "full_name": full_name,
        "department": employee.department,
        "designation": employee.designation,
    }


def _serialize_notice_period(np: NoticePeriod, employee: Optional[Employee]) -> dict:
    data = NoticePeriodResponse.model_validate(np).model_dump()
    data["employee"] = _employee_mini(employee)

    today = date.today()
    if np.notice_end_date:
        data["days_left"] = max((np.notice_end_date - today).days, 0)
    if np.notice_start_date and np.notice_end_date:
        total_days = (np.notice_end_date - np.notice_start_date).days or 1
        elapsed = (today - np.notice_start_date).days
        data["progress_percent"] = round(min(max(elapsed / total_days, 0), 1) * 100, 1)

    return data


def _serialize_buyout(req: BuyoutRequest, employee: Optional[Employee]) -> dict:
    data = BuyoutRequestResponse.model_validate(req).model_dump()
    data["employee"] = _employee_mini(employee)
    return data


def _serialize_waiver(req: WaiverRequest, employee: Optional[Employee], documents: list) -> dict:
    data = WaiverRequestResponse.model_validate(req).model_dump()
    data["employee"] = _employee_mini(employee)
    data["documents"] = [WaiverDocumentResponse.model_validate(d).model_dump() for d in documents]
    data["document_count"] = len(documents)
    return data


def _serialize_counter_offer(co: CounterOffer, employee: Optional[Employee]) -> dict:
    data = CounterOfferResponse.model_validate(co).model_dump()
    data["employee"] = _employee_mini(employee)
    return data


def _serialize_extension(req: ExtensionRequest, employee: Optional[Employee]) -> dict:
    data = ExtensionRequestResponse.model_validate(req).model_dump()
    data["employee"] = _employee_mini(employee)
    return data


def _resolve_overall_status(*approvals: str) -> str:
    """REJECTED wins, else APPROVED only if all approved, else PENDING."""
    if any(a == "REJECTED" for a in approvals):
        return "REJECTED"
    if all(a == "APPROVED" for a in approvals):
        return "APPROVED"
    return "PENDING"


# ======================================================
# 1. AI DASHBOARD
# ======================================================
@router.get("/dashboard", response_model=NoticePeriodDashboardStats)
def get_notice_period_dashboard(db: Session = Depends(get_db)):
    return get_dashboard_stats(db)


# ======================================================
# 2. ACTIVE CASES / NOTICE PERIODS  (Daily Countdown Tracker)
# ======================================================
@router.post("/cases", response_model=NoticePeriodResponse, status_code=status.HTTP_201_CREATED)
def create_notice_period_case(payload: NoticePeriodCreate, db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, payload.employee_id)

    case = NoticePeriod(**payload.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return _serialize_notice_period(case, employee)


@router.get("/cases", response_model=List[NoticePeriodResponse])
def list_notice_period_cases(
    status_filter: Optional[str] = Query(None, alias="status"),
    department: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Powers 'Active Cases' tab and the Daily Countdown Tracker cards."""
    query = select(NoticePeriod, Employee).join(Employee, NoticePeriod.employee_id == Employee.id)

    if status_filter:
        query = query.where(NoticePeriod.status == status_filter.upper())
    if department:
        query = query.where(Employee.department.ilike(f"%{department}%"))

    query = query.order_by(NoticePeriod.notice_end_date.asc()).offset(offset).limit(limit)
    rows = db.execute(query).all()
    return [_serialize_notice_period(np, emp) for np, emp in rows]


@router.get("/cases/{case_id}", response_model=NoticePeriodResponse)
def get_notice_period_case(case_id: int, db: Session = Depends(get_db)):
    case = _get_notice_period_or_404(db, case_id)
    employee = _get_employee_or_404(db, case.employee_id)
    return _serialize_notice_period(case, employee)


@router.put("/cases/{case_id}", response_model=NoticePeriodResponse)
def update_notice_period_case(case_id: int, payload: NoticePeriodUpdate, db: Session = Depends(get_db)):
    case = _get_notice_period_or_404(db, case_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    employee = _get_employee_or_404(db, case.employee_id)
    return _serialize_notice_period(case, employee)


@router.post("/cases/{case_id}/acknowledge", response_model=NoticePeriodResponse)
def acknowledge_notice_period_case(case_id: int, db: Session = Depends(get_db)):
    """Manager acknowledges the resignation -> clears 'Manager Ack Pending' badge."""
    case = _get_notice_period_or_404(db, case_id)
    case.manager_ack_status = "ACKNOWLEDGED"
    db.commit()
    db.refresh(case)
    employee = _get_employee_or_404(db, case.employee_id)
    return _serialize_notice_period(case, employee)


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notice_period_case(case_id: int, db: Session = Depends(get_db)):
    case = _get_notice_period_or_404(db, case_id)
    db.delete(case)
    db.commit()


# ======================================================
# 3. RESIGNATION WORKFLOW  ("Submit Resignation" modal + tab)
# ======================================================
@router.post("/resignation/submit", response_model=ResignationSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_resignation(payload: ResignationSubmissionCreate, db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, payload.employee_id)

    # AI retention prediction
    try:
        prediction = ai_predict_resignation_retention(
            employee=employee,
            resignation_reason=payload.resignation_reason,
            notice_period_days=payload.notice_period_days,
            additional_comments=payload.additional_comments,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI prediction failed: {exc}")

    # auto-create the underlying NoticePeriod case
    notice_end_date = calculate_lwd(payload.resignation_date, payload.notice_period_days)
    case = NoticePeriod(
        employee_id=payload.employee_id,
        notice_start_date=payload.resignation_date,
        notice_end_date=notice_end_date,
        notice_period_days=payload.notice_period_days,
        status="SERVING",
    )
    db.add(case)
    db.flush()  # get case.id without committing yet

    submission = ResignationSubmission(
        employee_id=payload.employee_id,
        notice_period_id=case.id,
        department=payload.department,
        role=payload.role,
        resignation_date=payload.resignation_date,
        notice_period_days=payload.notice_period_days,
        resignation_reason=payload.resignation_reason,
        additional_comments=payload.additional_comments,
        reporting_manager_email=payload.reporting_manager_email,
        ai_retention_probability=prediction["retention_probability"],
        ai_risk_level=prediction["risk_level"],
        ai_recommendation=prediction["recommendation"],
        status="SUBMITTED",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return_data = ResignationSubmissionResponse.model_validate(submission).model_dump()
    return_data["employee"] = _employee_mini(employee)
    return return_data


@router.get("/resignation", response_model=List[ResignationSubmissionResponse])
def list_resignation_submissions(
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(ResignationSubmission, Employee).join(
        Employee, ResignationSubmission.employee_id == Employee.id
    )
    if employee_id:
        query = query.where(ResignationSubmission.employee_id == employee_id)

    rows = db.execute(query.order_by(ResignationSubmission.id.desc())).all()
    results = []
    for sub, emp in rows:
        data = ResignationSubmissionResponse.model_validate(sub).model_dump()
        data["employee"] = _employee_mini(emp)
        results.append(data)
    return results


@router.get("/resignation/{submission_id}", response_model=ResignationSubmissionResponse)
def get_resignation_submission(submission_id: int, db: Session = Depends(get_db)):
    sub = db.execute(
        select(ResignationSubmission).where(ResignationSubmission.id == submission_id)
    ).scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Resignation submission not found")

    employee = _get_employee_or_404(db, sub.employee_id)
    data = ResignationSubmissionResponse.model_validate(sub).model_dump()
    data["employee"] = _employee_mini(employee)
    return data


# ======================================================
# 4. BUYOUT REQUESTS
# ======================================================
@router.post("/buyout-requests", response_model=BuyoutRequestResponse, status_code=status.HTTP_201_CREATED)
def create_buyout_request(payload: BuyoutRequestCreate, db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, payload.employee_id)

    calc = calculate_buyout(payload.monthly_salary, payload.days_to_buyout)

    req = BuyoutRequest(
        employee_id=payload.employee_id,
        notice_period_id=payload.notice_period_id,
        requested_date=payload.requested_date or date.today(),
        monthly_salary=payload.monthly_salary,
        days_to_buyout=payload.days_to_buyout,
        buyout_amount=calc["buyout_amount"],
        remarks=payload.remarks,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _serialize_buyout(req, employee)


@router.get("/buyout-requests", response_model=List[BuyoutRequestResponse])
def list_buyout_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = select(BuyoutRequest, Employee).join(Employee, BuyoutRequest.employee_id == Employee.id)
    if status_filter:
        query = query.where(BuyoutRequest.status == status_filter.upper())

    rows = db.execute(query.order_by(BuyoutRequest.id.desc())).all()
    return [_serialize_buyout(req, emp) for req, emp in rows]


@router.post("/buyout-requests/{request_id}/action", response_model=BuyoutRequestResponse)
def act_on_buyout_request(request_id: int, payload: BuyoutApprovalAction, db: Session = Depends(get_db)):
    req = db.execute(select(BuyoutRequest).where(BuyoutRequest.id == request_id)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Buyout request not found")
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    role = payload.approver_role.upper()
    decision = payload.decision.upper()
    if role == "MANAGER":
        req.manager_approval = decision
    elif role == "HR":
        req.hr_approval = decision
    elif role == "FINANCE":
        req.finance_approval = decision
    else:
        raise HTTPException(status_code=400, detail="approver_role must be MANAGER, HR, or FINANCE")

    if payload.remarks:
        req.remarks = payload.remarks

    req.status = _resolve_overall_status(req.manager_approval, req.hr_approval, req.finance_approval)

    db.commit()
    db.refresh(req)
    employee = _get_employee_or_404(db, req.employee_id)
    return _serialize_buyout(req, employee)


# ======================================================
# 5. WAIVER REQUESTS (+ documents)
# ======================================================
@router.post("/waiver-requests", response_model=WaiverRequestResponse, status_code=status.HTTP_201_CREATED)
def create_waiver_request(payload: WaiverRequestCreate, db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, payload.employee_id)

    req = WaiverRequest(
        employee_id=payload.employee_id,
        notice_period_id=payload.notice_period_id,
        requested_date=payload.requested_date or date.today(),
        waiver_days=payload.waiver_days,
        reason=payload.reason,
        remarks=payload.remarks,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _serialize_waiver(req, employee, [])


@router.post("/waiver-requests/{request_id}/documents", response_model=WaiverDocumentResponse)
def upload_waiver_document(request_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    req = db.execute(select(WaiverRequest).where(WaiverRequest.id == request_id)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Waiver request not found")

    saved = save_waiver_document(file, request_id)

    doc = WaiverDocument(waiver_request_id=request_id, **saved)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/waiver-requests", response_model=List[WaiverRequestResponse])
def list_waiver_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = select(WaiverRequest, Employee).join(Employee, WaiverRequest.employee_id == Employee.id)
    if status_filter:
        query = query.where(WaiverRequest.status == status_filter.upper())

    rows = db.execute(query.order_by(WaiverRequest.id.desc())).all()

    results = []
    for req, emp in rows:
        docs = db.execute(
            select(WaiverDocument).where(WaiverDocument.waiver_request_id == req.id)
        ).scalars().all()
        results.append(_serialize_waiver(req, emp, docs))
    return results


@router.post("/waiver-requests/{request_id}/action", response_model=WaiverRequestResponse)
def act_on_waiver_request(request_id: int, payload: WaiverApprovalAction, db: Session = Depends(get_db)):
    req = db.execute(select(WaiverRequest).where(WaiverRequest.id == request_id)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Waiver request not found")
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    role = payload.approver_role.upper()
    decision = payload.decision.upper()
    if role == "MANAGER":
        req.manager_approval = decision
    elif role == "HR":
        req.hr_approval = decision
    elif role == "DIRECTOR":
        req.director_approval = decision
    else:
        raise HTTPException(status_code=400, detail="approver_role must be MANAGER, HR, or DIRECTOR")

    if payload.remarks:
        req.remarks = payload.remarks

    req.status = _resolve_overall_status(req.manager_approval, req.hr_approval, req.director_approval)

    if req.status == "APPROVED" and req.notice_period_id:
        case = db.execute(select(NoticePeriod).where(NoticePeriod.id == req.notice_period_id)).scalar_one_or_none()
        if case:
            case.waiver_approved = "YES"
            case.status = "WAIVED"

    db.commit()
    db.refresh(req)
    employee = _get_employee_or_404(db, req.employee_id)
    docs = db.execute(select(WaiverDocument).where(WaiverDocument.waiver_request_id == req.id)).scalars().all()
    return _serialize_waiver(req, employee, docs)


# ======================================================
# 6. COUNTER OFFERS & RETENTION
# ======================================================
@router.post("/counter-offers", response_model=CounterOfferResponse, status_code=status.HTTP_201_CREATED)
def create_counter_offer(payload: CounterOfferCreate, db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, payload.employee_id)

    hike_percent = round(
        ((payload.offered_salary - payload.current_salary) / payload.current_salary) * 100, 1
    )

    try:
        prediction = ai_predict_counter_offer_retention(
            employee=employee,
            current_salary=payload.current_salary,
            offered_salary=payload.offered_salary,
            hike_percent=hike_percent,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI prediction failed: {exc}")

    offer = CounterOffer(
        employee_id=payload.employee_id,
        notice_period_id=payload.notice_period_id,
        current_salary=payload.current_salary,
        offered_salary=payload.offered_salary,
        hike_percent=hike_percent,
        retention_probability=prediction["retention_probability"],
        ai_rationale=prediction["rationale"],
        remarks=payload.remarks,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return _serialize_counter_offer(offer, employee)


@router.get("/counter-offers", response_model=List[CounterOfferResponse])
def list_counter_offers(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = select(CounterOffer, Employee).join(Employee, CounterOffer.employee_id == Employee.id)
    if status_filter:
        query = query.where(CounterOffer.status == status_filter.upper())

    rows = db.execute(query.order_by(CounterOffer.id.desc())).all()
    return [_serialize_counter_offer(co, emp) for co, emp in rows]


@router.post("/counter-offers/{offer_id}/decision", response_model=CounterOfferResponse)
def decide_counter_offer(offer_id: int, payload: CounterOfferDecision, db: Session = Depends(get_db)):
    offer = db.execute(select(CounterOffer).where(CounterOffer.id == offer_id)).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Counter offer not found")
    if offer.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Counter offer is already {offer.status}")

    decision = payload.decision.upper()
    if decision not in ("ACCEPTED", "REJECTED"):
        raise HTTPException(status_code=400, detail="decision must be ACCEPTED or REJECTED")

    offer.status = decision
    if payload.remarks:
        offer.remarks = payload.remarks

    if decision == "ACCEPTED" and offer.notice_period_id:
        case = db.execute(
            select(NoticePeriod).where(NoticePeriod.id == offer.notice_period_id)
        ).scalar_one_or_none()
        if case:
            case.status = "COMPLETED"
            case.remarks = (case.remarks or "") + " | Retained via counter offer"

    db.commit()
    db.refresh(offer)
    employee = _get_employee_or_404(db, offer.employee_id)
    return _serialize_counter_offer(offer, employee)


# ======================================================
# 7. EXTENSION REQUESTS
# ======================================================
@router.post("/extension-requests", response_model=ExtensionRequestResponse, status_code=status.HTTP_201_CREATED)
def create_extension_request(payload: ExtensionRequestCreate, db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, payload.employee_id)

    extension_days = (payload.requested_lwd - payload.current_lwd).days
    if extension_days <= 0:
        raise HTTPException(status_code=400, detail="requested_lwd must be after current_lwd")

    req = ExtensionRequest(
        employee_id=payload.employee_id,
        notice_period_id=payload.notice_period_id,
        current_lwd=payload.current_lwd,
        requested_lwd=payload.requested_lwd,
        extension_days=extension_days,
        reason=payload.reason,
        remarks=payload.remarks,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _serialize_extension(req, employee)


@router.get("/extension-requests", response_model=List[ExtensionRequestResponse])
def list_extension_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = select(ExtensionRequest, Employee).join(Employee, ExtensionRequest.employee_id == Employee.id)
    if status_filter:
        query = query.where(ExtensionRequest.status == status_filter.upper())

    rows = db.execute(query.order_by(ExtensionRequest.id.desc())).all()
    return [_serialize_extension(req, emp) for req, emp in rows]


@router.post("/extension-requests/{request_id}/action", response_model=ExtensionRequestResponse)
def act_on_extension_request(request_id: int, payload: ExtensionApprovalAction, db: Session = Depends(get_db)):
    req = db.execute(select(ExtensionRequest).where(ExtensionRequest.id == request_id)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Extension request not found")
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    role = payload.approver_role.upper()
    decision = payload.decision.upper()
    if role == "MANAGER":
        req.manager_approval = decision
    elif role == "HR":
        req.hr_approval = decision
    else:
        raise HTTPException(status_code=400, detail="approver_role must be MANAGER or HR")

    if payload.remarks:
        req.remarks = payload.remarks

    req.status = _resolve_overall_status(req.manager_approval, req.hr_approval)

    if req.status == "APPROVED" and req.notice_period_id:
        case = db.execute(
            select(NoticePeriod).where(NoticePeriod.id == req.notice_period_id)
        ).scalar_one_or_none()
        if case:
            case.notice_end_date = req.requested_lwd

    db.commit()
    db.refresh(req)
    employee = _get_employee_or_404(db, req.employee_id)
    return _serialize_extension(req, employee)


# ======================================================
# 8. CALCULATORS
# ======================================================
@router.post("/calculators/lwd", response_model=LWDCalculatorResponse)
def calculator_lwd(payload: LWDCalculatorRequest):
    lwd = calculate_lwd(payload.resignation_date, payload.notice_period_days)
    return {
        "resignation_date": payload.resignation_date,
        "notice_period_days": payload.notice_period_days,
        "last_working_day": lwd,
    }


@router.post("/calculators/buyout", response_model=BuyoutCalculatorResponse)
def calculator_buyout(payload: BuyoutCalculatorRequest):
    calc = calculate_buyout(payload.monthly_salary, payload.days_to_buyout)
    return {
        "monthly_salary": payload.monthly_salary,
        "days_to_buyout": payload.days_to_buyout,
        "per_day_salary": calc["per_day_salary"],
        "buyout_amount": calc["buyout_amount"],
    }


@router.post("/calculators/waiver", response_model=WaiverCalculatorResponse)
def calculator_waiver(payload: WaiverCalculatorRequest):
    remaining = calculate_after_waiver(payload.current_notice_period_days, payload.waiver_days_requested)
    return {
        "current_notice_period_days": payload.current_notice_period_days,
        "waiver_days_requested": payload.waiver_days_requested,
        "remaining_notice_days": remaining,
    }


@router.post("/calculators/shortfall", response_model=ShortfallCalculatorResponse)
def calculator_shortfall(payload: ShortfallCalculatorRequest):
    calc = calculate_shortfall(payload.required_notice_period_days, payload.actual_service_days)
    return {
        "required_notice_period_days": payload.required_notice_period_days,
        "actual_service_days": payload.actual_service_days,
        "shortfall_days": calc["shortfall_days"],
        "is_shortfall": calc["is_shortfall"],
    }


# ======================================================
# 9. EXPORT REPORTS
# ======================================================
@router.get("/export")
def export_reports(
    export_format: str = Query(..., alias="format", description="JSON | CSV | PDF | EXCEL"),
    include_cases: bool = Query(True),
    include_requests: bool = Query(True),
    include_statistics: bool = Query(True),
    db: Session = Depends(get_db),
):
    fmt = export_format.upper()

    if fmt == "JSON":
        payload = export_reports_json(db, include_cases, include_requests, include_statistics)
        return JSONResponse(content=payload)

    if fmt == "CSV":
        buffer = export_reports_csv(db)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="notice_period_report.csv"'},
        )

    if fmt == "EXCEL":
        buffer = export_reports_excel(db)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="notice_period_report.xlsx"'},
        )

    if fmt == "PDF":
        buffer = export_reports_pdf(db)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="notice_period_report.pdf"'},
        )

    raise HTTPException(status_code=400, detail="format must be one of JSON, CSV, PDF, EXCEL")