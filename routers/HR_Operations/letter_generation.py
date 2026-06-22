"""
routers/HR_Operations/letter_generation.py

HR Letter Generation System — full backend matching the
"HR Letter Generation System" dashboard:

  Dashboard tiles : templates / requests / auto-approved / downloads
  Templates       : CRUD for the 12 reusable letter templates
  Generator       : create a letter request from a template (manual or AI)
  Requests        : list / filter / view all letter requests
  Workflow        : approve / reject pending requests
  Employees       : letters grouped by employee
  Archive         : approved + rejected (closed) requests
  Reports         : category-wise breakdown
  Export          : PDF (single letter) / Excel (request list)
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from core.database import get_db
from model.HR_Operations.letter_generation import LetterRequest, LetterTemplate
from model.onboarding.employee import Employee
from schema.HR_Operations.letter_generation import (
    LetterTemplateCreate,
    LetterTemplateUpdate,
    LetterTemplateResponse,
    LetterRequestCreate,
    LetterRequestAIGenerate,
    LetterRequestUpdate,
    LetterRequestApprove,
    LetterRequestReject,
    LetterRequestResponse,
    LetterDashboardStats,
)
from services.letters_service import  (
    generate_request_code,
    build_placeholder_context,
    render_template_string,
    ai_generate_letter,
    get_dashboard_stats,
    export_requests_to_excel,
    export_letter_to_pdf,
)

router = APIRouter(prefix="/api/hr-operations/letters", tags=["HR Operations - Letter Generation"])


# ======================================================
# HELPERS
# ======================================================
def _get_employee_or_404(db: Session, employee_id: int) -> Employee:
    employee = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


def _get_request_or_404(db: Session, request_id: int) -> LetterRequest:
    req = db.execute(
        select(LetterRequest).where(LetterRequest.id == request_id)
    ).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Letter request not found")
    return req


def _get_template_or_404(db: Session, template_id: int) -> LetterTemplate:
    tpl = db.execute(
        select(LetterTemplate).where(LetterTemplate.id == template_id)
    ).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Letter template not found")
    return tpl


def _serialize_request(req: LetterRequest, employee: Optional[Employee] = None) -> dict:
    data = LetterRequestResponse.model_validate(req).model_dump()
    if employee:
        full_name = " ".join(
            p for p in [employee.first_name, employee.middle_name, employee.last_name] if p
        )
        data["employee"] = {
            "id": employee.id,
            "employee_code": employee.employee_code,
            "full_name": full_name,
            "department": employee.department,
            "designation": employee.designation,
        }
    return data


# ======================================================
# 1. DASHBOARD
# ======================================================
@router.get("/dashboard", response_model=LetterDashboardStats)
def get_letters_dashboard(db: Session = Depends(get_db)):
    """Powers the top tiles: Templates / Requests / Auto Approved / Downloads."""
    return get_dashboard_stats(db)


# ======================================================
# 2. TEMPLATES  (Templates tab)
# ======================================================
@router.post("/templates", response_model=LetterTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(payload: LetterTemplateCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(LetterTemplate).where(LetterTemplate.code == payload.code)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Template code already exists")

    template = LetterTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/templates", response_model=List[LetterTemplateResponse])
def list_templates(
    category: Optional[str] = Query(None, description="Employment | Financial | Exit | Legal | Career | Disciplinary"),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(LetterTemplate)
    if category:
        query = query.where(LetterTemplate.category == category)
    if is_active is not None:
        query = query.where(LetterTemplate.is_active == is_active)

    result = db.execute(query.order_by(LetterTemplate.id))
    return result.scalars().all()


@router.get("/templates/categories")
def get_template_categories(db: Session = Depends(get_db)):
    """Powers the 'Template Categories' tile row (Employment 3, Financial 3, Exit 2 ...)."""
    rows = (
        db.query(LetterTemplate.category, func.count(LetterTemplate.id))
        .group_by(LetterTemplate.category)
        .all()
    )
    return [{"category": c, "count": n} for c, n in rows]


@router.get("/templates/{template_id}", response_model=LetterTemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db)):
    return _get_template_or_404(db, template_id)


@router.put("/templates/{template_id}", response_model=LetterTemplateResponse)
def update_template(template_id: int, payload: LetterTemplateUpdate, db: Session = Depends(get_db)):
    template = _get_template_or_404(db, template_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = _get_template_or_404(db, template_id)
    db.delete(template)
    db.commit()


# ======================================================
# 3. GENERATOR  (Generator tab — manual, from template)
# ======================================================
@router.post("/requests", response_model=LetterRequestResponse, status_code=status.HTTP_201_CREATED)
def generate_letter_request(payload: LetterRequestCreate, db: Session = Depends(get_db)):
    """
    Creates a new letter request.
    - If template_id is given and subject/body are omitted, they are rendered
      from the template using {{placeholders}} + employee data.
    - If the template has auto_approve=True, the request is auto-approved.
    """
    employee = _get_employee_or_404(db, payload.employee_id)

    subject = payload.subject
    body = payload.body
    auto_approved = False
    template = None

    if payload.template_id:
        template = _get_template_or_404(db, payload.template_id)
        context = build_placeholder_context(employee, payload.placeholders)

        if not subject:
            subject = render_template_string(template.subject_template, context)
        if not body:
            body = render_template_string(template.template_body, context)

        auto_approved = bool(template.auto_approve)

    if not subject or not body:
        raise HTTPException(
            status_code=400,
            detail="subject and body are required when no template_id is provided",
        )

    letter_request = LetterRequest(
        request_code=generate_request_code(db),
        employee_id=payload.employee_id,
        template_id=payload.template_id,
        letter_type=payload.letter_type,
        subject=subject,
        body=body,
        status="APPROVED" if auto_approved else "PENDING",
        generated_by=payload.generated_by,
        is_ai_generated=False,
        auto_approved=auto_approved,
        letter_date=payload.letter_date or date.today(),
    )

    db.add(letter_request)
    db.commit()
    db.refresh(letter_request)
    return _serialize_request(letter_request, employee)


@router.post("/requests/ai-generate", response_model=LetterRequestResponse, status_code=status.HTTP_201_CREATED)
def ai_generate_letter_request(payload: LetterRequestAIGenerate, db: Session = Depends(get_db)):
    """Powers the 'AI' button on the dashboard — drafts subject + body via OpenAI."""
    employee = _get_employee_or_404(db, payload.employee_id)

    auto_approved = False
    if payload.template_id:
        template = _get_template_or_404(db, payload.template_id)
        auto_approved = bool(template.auto_approve)

    context = build_placeholder_context(employee, payload.placeholders)

    try:
        ai_result = ai_generate_letter(
            letter_type=payload.letter_type,
            context=context,
            tone=payload.tone or "formal",
            extra_instructions=payload.extra_instructions,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}")

    letter_request = LetterRequest(
        request_code=generate_request_code(db),
        employee_id=payload.employee_id,
        template_id=payload.template_id,
        letter_type=payload.letter_type,
        subject=ai_result["subject"],
        body=ai_result["body"],
        status="APPROVED" if auto_approved else "PENDING",
        generated_by=payload.generated_by,
        is_ai_generated=True,
        auto_approved=auto_approved,
        letter_date=payload.letter_date or date.today(),
    )

    db.add(letter_request)
    db.commit()
    db.refresh(letter_request)
    return _serialize_request(letter_request, employee)


# ======================================================
# 4. REQUESTS  (Requests tab — "Recent Letter Requests" table)
# ======================================================
@router.get("/requests", response_model=List[LetterRequestResponse])
def list_letter_requests(
    status_filter: Optional[str] = Query(None, alias="status", description="PENDING | APPROVED | REJECTED"),
    employee_id: Optional[int] = Query(None),
    letter_type: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(LetterRequest, Employee).join(Employee, LetterRequest.employee_id == Employee.id)

    if status_filter:
        query = query.where(LetterRequest.status == status_filter.upper())
    if employee_id:
        query = query.where(LetterRequest.employee_id == employee_id)
    if letter_type:
        query = query.where(LetterRequest.letter_type.ilike(f"%{letter_type}%"))
    if department:
        query = query.where(Employee.department.ilike(f"%{department}%"))

    query = query.order_by(LetterRequest.id.desc()).offset(offset).limit(limit)

    rows = db.execute(query).all()
    return [_serialize_request(req, emp) for req, emp in rows]


@router.get("/requests/{request_id}", response_model=LetterRequestResponse)
def get_letter_request(request_id: int, db: Session = Depends(get_db)):
    req = _get_request_or_404(db, request_id)
    employee = _get_employee_or_404(db, req.employee_id)
    return _serialize_request(req, employee)


@router.put("/requests/{request_id}", response_model=LetterRequestResponse)
def update_letter_request(request_id: int, payload: LetterRequestUpdate, db: Session = Depends(get_db)):
    req = _get_request_or_404(db, request_id)

    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only PENDING requests can be edited")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(req, key, value)

    db.commit()
    db.refresh(req)
    employee = _get_employee_or_404(db, req.employee_id)
    return _serialize_request(req, employee)


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_letter_request(request_id: int, db: Session = Depends(get_db)):
    req = _get_request_or_404(db, request_id)
    db.delete(req)
    db.commit()


# ======================================================
# 5. WORKFLOW  (Workflow tab — approve / reject actions)
# ======================================================
@router.post("/requests/{request_id}/approve", response_model=LetterRequestResponse)
def approve_letter_request(request_id: int, payload: LetterRequestApprove, db: Session = Depends(get_db)):
    from datetime import datetime as _dt

    req = _get_request_or_404(db, request_id)
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    req.status = "APPROVED"
    req.approved_by = payload.approved_by
    req.approved_at = _dt.utcnow()

    db.commit()
    db.refresh(req)
    employee = _get_employee_or_404(db, req.employee_id)
    return _serialize_request(req, employee)


@router.post("/requests/{request_id}/reject", response_model=LetterRequestResponse)
def reject_letter_request(request_id: int, payload: LetterRequestReject, db: Session = Depends(get_db)):
    from datetime import datetime as _dt

    req = _get_request_or_404(db, request_id)
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    req.status = "REJECTED"
    req.approved_by = payload.approved_by
    req.rejection_reason = payload.rejection_reason
    req.approved_at = _dt.utcnow()

    db.commit()
    db.refresh(req)
    employee = _get_employee_or_404(db, req.employee_id)
    return _serialize_request(req, employee)


# ======================================================
# 6. EMPLOYEES  (Employees tab — letters grouped by employee)
# ======================================================
@router.get("/employees/{employee_id}/letters", response_model=List[LetterRequestResponse])
def get_employee_letters(employee_id: int, db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, employee_id)

    rows = db.execute(
        select(LetterRequest)
        .where(LetterRequest.employee_id == employee_id)
        .order_by(LetterRequest.id.desc())
    ).scalars().all()

    return [_serialize_request(r, employee) for r in rows]


# ======================================================
# 7. ARCHIVE  (Archive tab — closed requests: approved/rejected)
# ======================================================
@router.get("/archive", response_model=List[LetterRequestResponse])
def get_archived_requests(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = (
        select(LetterRequest, Employee)
        .join(Employee, LetterRequest.employee_id == Employee.id)
        .where(LetterRequest.status.in_(["APPROVED", "REJECTED"]))
        .order_by(LetterRequest.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = db.execute(query).all()
    return [_serialize_request(req, emp) for req, emp in rows]


# ======================================================
# 8. REPORTS  (Reports tab)
# ======================================================
@router.get("/reports/summary")
def get_letters_report_summary(db: Session = Depends(get_db)):
    by_status = db.query(LetterRequest.status, func.count(LetterRequest.id)).group_by(LetterRequest.status).all()
    by_type = (
        db.query(LetterRequest.letter_type, func.count(LetterRequest.id))
        .group_by(LetterRequest.letter_type)
        .order_by(func.count(LetterRequest.id).desc())
        .all()
    )

    return {
        "by_status": [{"status": s, "count": n} for s, n in by_status],
        "by_letter_type": [{"letter_type": t, "count": n} for t, n in by_type],
    }


# ======================================================
# 9. EXPORT  (PDF download / Excel export buttons)
# ======================================================
@router.get("/requests/{request_id}/export/pdf")
def export_letter_pdf(request_id: int, db: Session = Depends(get_db)):
    req = _get_request_or_404(db, request_id)
    if req.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Only APPROVED letters can be downloaded")

    employee = _get_employee_or_404(db, req.employee_id)

    pdf_buffer = export_letter_to_pdf(req, employee)

    req.download_count = (req.download_count or 0) + 1
    db.commit()

    filename = f"{req.request_code}_{req.letter_type.replace(' ', '_')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/requests/export/excel")
def export_requests_excel(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = (
        select(LetterRequest, Employee)
        .join(Employee, LetterRequest.employee_id == Employee.id)
        .order_by(LetterRequest.id.desc())
    )
    if status_filter:
        query = query.where(LetterRequest.status == status_filter.upper())

    rows = db.execute(query).all()

    excel_buffer = export_requests_to_excel(rows)

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="letter_requests.xlsx"'},
    )