# routers/Payroll/salary_slip.py
# All 18 salary slip API endpoints

import io
from typing import Optional, List
from fastapi import (
    APIRouter, Depends, HTTPException, Query,
    status, Response, BackgroundTasks
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from core.database import get_db

from schema.Payroll.salary_slip import (
    SalarySlipResponse,
    SalarySlipUpdate,
    SalarySlipGenerateRequest,
    SalarySlipBulkGenerateRequest,
    SalarySlipKPIResponse,
    SendEmailRequest,
    BulkSendEmailRequest,
)
from schema.Payroll.slip_distribution import (
    SlipSettingsResponse,
    SlipSettingsUpdate,
    DistributionLogResponse,
)

import services.Payroll.slip_service     as slip_svc
import services.Payroll.slip_service as pdf_svc
import services.Payroll.slip_service as zip_svc

router = APIRouter(
    prefix="/api/payroll/salary-slip",
    tags=["Payroll — Salary Slips"],
)

settings_router = APIRouter(
    prefix="/api/payroll/slip-settings",
    tags=["Payroll — Slip Settings"],
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. KPI SUMMARY
# GET /api/payroll/salary-slip/kpi-summary
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/kpi-summary",
    response_model=SalarySlipKPIResponse,
    summary="Dashboard KPIs — total slips, employees, distributed, total payout",
)

def kpi_summary(
    slip_month: Optional[int] = Query(None, ge=1, le=12),
    slip_year:  Optional[int] = Query(None, ge=2000, le=2100),
    db: Session               = Depends(get_db),
):
    return slip_svc.get_kpi_summary(db, slip_month=slip_month, slip_year=slip_year)


# ─────────────────────────────────────────────────────────────────────────────
# 2. GENERATE SINGLE SLIP
# POST /api/payroll/salary-slip/generate
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/generate",
    response_model=SalarySlipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate salary slip for one employee",
)
def generate_single_slip(
    req: SalarySlipGenerateRequest,
    db: Session = Depends(get_db),
):
    return slip_svc.generate_salary_slip(
        db, req, generated_by="admin"
    )

# ─────────────────────────────────────────────────────────────────────────────
# 3. BULK GENERATE
# POST /api/payroll/salary-slip/generate-all
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/generate-all",
    summary="Bulk generate salary slips for all active employees",
)
def generate_all_slips(
    req: SalarySlipBulkGenerateRequest,
    db: Session        = Depends(get_db),
):
    slips, errors = slip_svc.bulk_generate_salary_slips(
        db, req, generated_by="admin"
    )
    return {
        "generated": len(slips),
        "failed":    len(errors),
        "errors":    errors,
        "slips":     [s.id for s in slips],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. LIST SLIPS
# GET /api/payroll/salary-slip
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "",
    response_model=List[SalarySlipResponse],
    summary="List salary slips with optional filters",
)
def list_slips(
    employee_id:  Optional[int]  = Query(None),
    slip_month:   Optional[int]  = Query(None, ge=1, le=12),
    slip_year:    Optional[int]  = Query(None, ge=2000, le=2100),
    is_published: Optional[bool] = Query(None),
    skip:  int = Query(0,   ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session        = Depends(get_db),
):
    slips = slip_svc.list_salary_slips(
        db,
        employee_id  = employee_id,
        slip_month   = slip_month,
        slip_year    = slip_year,
        is_published = is_published,
        skip         = skip,
        limit        = limit,
    )
    # Attach components
    result = []
    for slip in slips:
        components = slip_svc.get_components(db, slip.id)
        slip.__dict__["components"] = components
        result.append(slip)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET SINGLE SLIP
# GET /api/payroll/salary-slip/{slip_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/{slip_id}",
    response_model=SalarySlipResponse,
    summary="Get full salary slip detail",
)
def get_slip(
    slip_id: int,
    db: Session        = Depends(get_db),
):
    slip       = slip_svc.get_salary_slip(db, slip_id)
    components = slip_svc.get_components(db, slip_id)
    slip.__dict__["components"] = components
    return slip


# ─────────────────────────────────────────────────────────────────────────────
# 6. GET SLIPS BY EMPLOYEE
# GET /api/payroll/salary-slip/employee/{employee_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/employee/{employee_id}",
    response_model=List[SalarySlipResponse],
    summary="All salary slips for a specific employee",
)
def get_employee_slips(
    employee_id: int,
    db: Session        = Depends(get_db),
):
    slips = slip_svc.get_slips_by_employee(db, employee_id)
    result = []
    for slip in slips:
        components = slip_svc.get_components(db, slip.id)
        slip.__dict__["components"] = components
        result.append(slip)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 7. PREVIEW (compute without saving)
# GET /api/payroll/salary-slip/preview?employee_id=&slip_month=&slip_year=
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/preview",
    summary="Preview computed salary slip without saving",
)
def preview_slip(
    employee_id: int = Query(...),
    slip_month:  int = Query(..., ge=1, le=12),
    slip_year:   int = Query(..., ge=2000, le=2100),
    db: Session        = Depends(get_db),
):
    data = slip_svc.preview_salary_slip(db, employee_id, slip_month, slip_year)
    # Remove internal employer-side keys before returning
    data.pop("_pf_employer",  None)
    data.pop("_esi_employer", None)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# 8. UPDATE SLIP
# PUT /api/payroll/salary-slip/{slip_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.put(
    "/{slip_id}",
    response_model=SalarySlipResponse,
    summary="Partially update a salary slip",
)
def update_slip(
    slip_id: int,
    payload: SalarySlipUpdate,
    db: Session        = Depends(get_db),
):
    slip       = slip_svc.update_salary_slip(db, slip_id, payload)
    components = slip_svc.get_components(db, slip_id)
    slip.__dict__["components"] = components
    return slip


# ─────────────────────────────────────────────────────────────────────────────
# 9. PUBLISH SLIP
# POST /api/payroll/salary-slip/{slip_id}/publish
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/{slip_id}/publish",
    response_model=SalarySlipResponse,
    summary="Publish slip — makes it visible to employee",
)
def publish_slip(
    slip_id: int,
    db: Session = Depends(get_db),
):
    slip = slip_svc.publish_salary_slip(db, slip_id)
    components = slip_svc.get_components(db, slip_id)
    slip.__dict__["components"] = components

    # Auto-email if setting is enabled
    settings = slip_svc.get_slip_settings(db)
    if settings.auto_email_on_publish and slip.official_email:
        import asyncio
        try:
            from services.Payroll.slip_email_service import send_slip_email
            asyncio.get_event_loop().run_until_complete(
                send_slip_email(
                    db=db,
                    slip_id=slip_id,
                    sent_by="admin"
                )
            )
        except Exception:
            pass

    return slip
# ─────────────────────────────────────────────────────────────────────────────
# 10. UNPUBLISH SLIP
# POST /api/payroll/salary-slip/{slip_id}/unpublish
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/{slip_id}/unpublish",
    response_model=SalarySlipResponse,
    summary="Unpublish slip — hides it from employee",
)
def unpublish_slip(
    slip_id: int,
    db: Session        = Depends(get_db),
):
    slip       = slip_svc.unpublish_salary_slip(db, slip_id)
    components = slip_svc.get_components(db, slip_id)
    slip.__dict__["components"] = components
    return slip


# ─────────────────────────────────────────────────────────────────────────────
# 11. DELETE SLIP (soft)
# DELETE /api/payroll/salary-slip/{slip_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.delete(
    "/{slip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a salary slip",
)
def delete_slip(
    slip_id: int,
    db: Session        = Depends(get_db),
):
    slip_svc.delete_salary_slip(db, slip_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# 12. DOWNLOAD SINGLE PDF
# GET /api/payroll/salary-slip/{slip_id}/pdf
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/{slip_id}/pdf",
    summary="Generate and download a single salary slip PDF",
)
def download_pdf(
    slip_id: int,
    db: Session        = Depends(get_db),
):
    slip       = slip_svc.get_salary_slip(db, slip_id)
    components = slip_svc.get_components(db, slip_id)
    settings   = slip_svc.get_slip_settings(db)

    slip_dict = {
        "employee_id":      slip.employee_id,
        "employee_code":    slip.employee_code,
        "employee_name":    slip.employee_name,
        "department":       slip.department,
        "designation":      slip.designation,
        "pan_number":       slip.pan_number,
        "uan_number":       slip.uan_number,
        "bank_account":     slip.bank_account,
        "bank_name":        slip.bank_name,
        "slip_month":       slip.slip_month,
        "slip_year":        slip.slip_year,
        "days_in_month":    slip.days_in_month,
        "days_worked":      slip.days_worked,
        "days_absent":      slip.days_absent,
        "lop_days":         slip.lop_days,
        "gross_salary":     slip.gross_salary,
        "total_earnings":   slip.total_earnings,
        "total_deductions": slip.total_deductions,
        "net_pay":          slip.net_pay,
    }

    comp_list = [
        {
            "component_type": c.component_type,
            "component_name": c.component_name,
            "component_code": c.component_code,
            "amount":         c.amount,
            "is_statutory":   c.is_statutory,
        }
        for c in components
    ]

    pdf_bytes = pdf_svc.generate_pdf_bytes(
        slip_data        = slip_dict,
        components       = comp_list,
        company_name     = settings.company_name or "Company",
        company_address  = settings.company_address or "",
        signatory_name   = settings.signatory_name or "HR Manager",
        footer_text      = settings.footer_text or "",
        confidentiality_note = settings.confidentiality_note or "",
    )

    if settings.password_protect:
        password = pdf_svc.get_slip_password(
            slip_data       = slip_dict,
            password_type   = settings.password_type or "dob",
            custom_password = settings.custom_password,
        )
        if password:
            pdf_bytes = pdf_svc.apply_pdf_password(pdf_bytes, password)

    MONTH_NAMES = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month_label = f"{MONTH_NAMES[slip.slip_month]}_{slip.slip_year}"
    filename    = f"SalarySlip_{slip.employee_code}_{month_label}.pdf"

    # Log the download
    from model.Payroll.slip_distribution import SlipDistributionLog
    log = SlipDistributionLog(
    salary_slip_id=slip_id,
    employee_id=slip.employee_id,
    distribution_method="download",
    sent_by="admin",
    status="sent",
)
    db.add(log)
    db.commit()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type = "application/pdf",
        headers    = {"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 13. SEND EMAIL (single)
# POST /api/payroll/salary-slip/{slip_id}/send-email
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/{slip_id}/send-email",
    summary="Email salary slip PDF to employee",
)
async def send_slip_email(
    slip_id: int,
    body: SendEmailRequest,
    db: Session = Depends(get_db),
):
    from services.Payroll.slip_email_service import send_slip_email as _send

    log = await _send(
        db=db,
        slip_id=slip_id,
        sent_by="admin",
        recipient_override=body.recipient_email,
        cc_hr=body.cc_hr or False,
    )
    return {
        "message": "Email sent successfully",
        "log_id":  log.id,
        "status":  log.status,
    }


# ─────────────────────────────────────────────────────────────────────────────
## ─────────────────────────────────────────────────────────────────────────────
# 14. BULK SEND EMAIL
# POST /api/payroll/salary-slip/bulk-send-email
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/bulk-send-email",
    summary="Send salary slip emails to all employees for a given period",
)
async def bulk_send_email(
    body: BulkSendEmailRequest,
    db: Session = Depends(get_db),
):
    from services.Payroll.slip_email_service import bulk_send_slip_emails

    result = await bulk_send_slip_emails(
        db=db,
        slip_month=body.slip_month,
        slip_year=body.slip_year,
        sent_by="admin",
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# 15. BULK DOWNLOAD ZIP
# GET /api/payroll/salary-slip/bulk-download?slip_month=&slip_year=
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/bulk-download",
    summary="Download all salary slips for a period as a ZIP file",
)
def bulk_download_zip(
    slip_month: int = Query(..., ge=1, le=12),
    slip_year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
):
    zip_bytes, zip_filename = zip_svc.generate_bulk_zip(
        db=db,
        slip_month=slip_month,
        slip_year=slip_year,
        downloaded_by="admin",
    )

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"'
        },
    )
# ─────────────────────────────────────────────────────────────────────────────
# 16. DISTRIBUTION LOG
# GET /api/payroll/salary-slip/distribution-log
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/distribution-log",
    response_model=List[DistributionLogResponse],
    summary="View email / download distribution history",
)
def get_distribution_log(
    slip_month: Optional[int] = Query(None, ge=1, le=12),
    slip_year: Optional[int] = Query(None, ge=2000, le=2100),
    employee_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select, join
    from model.Payroll.slip_distribution import SlipDistributionLog
    from model.Payroll.salary_slip import SalarySlip

    stmt = (
        select(SlipDistributionLog)
        .join(SalarySlip, SalarySlip.id == SlipDistributionLog.salary_slip_id)
    )
    if slip_month:
        stmt = stmt.where(SalarySlip.slip_month == slip_month)
    if slip_year:
        stmt = stmt.where(SalarySlip.slip_year == slip_year)
    if employee_id:
        stmt = stmt.where(SlipDistributionLog.employee_id == employee_id)

    stmt = stmt.order_by(SlipDistributionLog.sent_at.desc()).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# 17. GET SETTINGS
# GET /api/payroll/slip-settings
# ─────────────────────────────────────────────────────────────────────────────
@settings_router.get(
    "",
    response_model=SlipSettingsResponse,
    summary="Get company salary slip settings",
)
def get_settings(
    db: Session        = Depends(get_db),
):
    return slip_svc.get_slip_settings(db)


# ─────────────────────────────────────────────────────────────────────────────
# 18. UPDATE SETTINGS
# PUT /api/payroll/slip-settings
# ─────────────────────────────────────────────────────────────────────────────
@settings_router.put(
    "",
    response_model=SlipSettingsResponse,
    summary="Update company salary slip settings",
)
def update_settings(
    payload: SlipSettingsUpdate,
    db: Session        = Depends(get_db),
):
    return slip_svc.update_slip_settings(db, payload)
