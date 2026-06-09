# routers/Payroll/statutory_compliance.py
# REPLACE your existing 53-byte stub with this
# 22 endpoints covering the full Statutory Compliance Engine

import io
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from model.models import User

from schema.Payroll.statutory_compliance import (
    StatutoryConfigResponse, StatutoryConfigUpdate,
    ComplianceKPIResponse,
    PFStatementResponse, PFStatementCalculateRequest,
    PFRemittanceCreate, PFRemittanceUpdate, PFRemittanceResponse,
    ECRGenerateRequest, ECRSubmissionResponse,
    VPFEnrollmentCreate, VPFEnrollmentResponse,
    UANActivationCreate, UANActivationResponse,
)
import services.Payroll.compliance_service as svc

router = APIRouter(
    prefix="/api/payroll/statutory-compliance",
    tags=["Payroll — Statutory Compliance"],
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. KPI SUMMARY
# GET /api/payroll/statutory-compliance/kpi
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/kpi", response_model=ComplianceKPIResponse,
            summary="Dashboard KPIs — Total PF, ESI, TDS, Pending Declarations")
def get_kpi(
    slip_month: Optional[int] = Query(None, ge=1, le=12),
    slip_year:  Optional[int] = Query(None, ge=2000, le=2100),
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.get_compliance_kpi(db, slip_month=slip_month, slip_year=slip_year)


# ─────────────────────────────────────────────────────────────────────────────
# STATUTORY CONFIG
# ─────────────────────────────────────────────────────────────────────────────

# 2. GET CONFIG
# GET /api/payroll/statutory-compliance/config
@router.get("/config", response_model=StatutoryConfigResponse,
            summary="Get PF/ESI/LWF/PT configuration")
def get_config(
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.get_config(db)


# 3. UPDATE CONFIG
# PUT /api/payroll/statutory-compliance/config
@router.put("/config", response_model=StatutoryConfigResponse,
            summary="Update PF/ESI/LWF/PT configuration")
def update_config(
    payload: StatutoryConfigUpdate,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.update_config(db, payload)


# ─────────────────────────────────────────────────────────────────────────────
# PF STATEMENTS
# ─────────────────────────────────────────────────────────────────────────────

# 4. CALCULATE PF FOR ALL EMPLOYEES
# POST /api/payroll/statutory-compliance/pf/calculate
@router.post("/pf/calculate",
             summary="Calculate PF for all active employees for a period")
def calculate_pf(
    req: PFStatementCalculateRequest,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results, errors = svc.calculate_pf_statements(
        db, req.slip_month, req.slip_year,
        calculated_by=current_user.email,
    )
    return {
        "calculated": len(results),
        "failed":     len(errors),
        "errors":     errors,
    }


# 5. LIST PF STATEMENTS FOR A PERIOD
# GET /api/payroll/statutory-compliance/pf/statements
@router.get("/pf/statements", response_model=List[PFStatementResponse],
            summary="List PF statements for a month/year")
def list_pf_statements(
    slip_month: int = Query(..., ge=1, le=12),
    slip_year:  int = Query(..., ge=2000, le=2100),
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.get_pf_statements(db, slip_month, slip_year)


# 6. GET SINGLE EMPLOYEE PF STATEMENT
# GET /api/payroll/statutory-compliance/pf/statements/{employee_id}
@router.get("/pf/statements/{employee_id}", response_model=PFStatementResponse,
            summary="Get PF statement for one employee for a period")
def get_employee_pf_statement(
    employee_id: int,
    slip_month: int = Query(..., ge=1, le=12),
    slip_year:  int = Query(..., ge=2000, le=2100),
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.get_pf_statement_single(db, employee_id, slip_month, slip_year)


# ─────────────────────────────────────────────────────────────────────────────
# PF REMITTANCES
# ─────────────────────────────────────────────────────────────────────────────

# 7. LIST REMITTANCES
# GET /api/payroll/statutory-compliance/pf/remittances
@router.get("/pf/remittances", response_model=List[PFRemittanceResponse],
            summary="List PF remittance (challan) records")
def list_remittances(
    slip_year: Optional[int] = Query(None),
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_pf_remittances(db, slip_year=slip_year)


# 8. ADD REMITTANCE
# POST /api/payroll/statutory-compliance/pf/remittances
@router.post("/pf/remittances", response_model=PFRemittanceResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Record a PF remittance / challan payment")
def add_remittance(
    payload: PFRemittanceCreate,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.create_pf_remittance(db, payload, created_by=current_user.email)


# 9. UPDATE REMITTANCE  (add challan number, mark paid)
# PUT /api/payroll/statutory-compliance/pf/remittances/{remittance_id}
@router.put("/pf/remittances/{remittance_id}", response_model=PFRemittanceResponse,
            summary="Update remittance — add challan number / mark paid")
def update_remittance(
    remittance_id: int,
    payload: PFRemittanceUpdate,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.update_pf_remittance(db, remittance_id, payload)


# ─────────────────────────────────────────────────────────────────────────────
# ECR
# ─────────────────────────────────────────────────────────────────────────────

# 10. LIST ECR SUBMISSIONS
# GET /api/payroll/statutory-compliance/ecr
@router.get("/ecr", response_model=List[ECRSubmissionResponse],
            summary="List all ECR submissions")
def list_ecr(
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_ecr_submissions(db)


# 11. GENERATE ECR
# POST /api/payroll/statutory-compliance/ecr/generate
@router.post("/ecr/generate", response_model=ECRSubmissionResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Generate ECR (Electronic Challan-cum-Return) for a period")
def generate_ecr(
    req: ECRGenerateRequest,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ecr, _ = svc.generate_ecr(db, req, created_by=current_user.email)
    return ecr


# 12. DOWNLOAD ECR FILE
# GET /api/payroll/statutory-compliance/ecr/{ecr_id}/download
@router.get("/ecr/{ecr_id}/download",
            summary="Download ECR text file for submission to EPFO portal")
def download_ecr(
    ecr_id: int,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from model.Payroll.statutory_compliance import ECRSubmission
    ecr_obj = db.execute(
        select(ECRSubmission).where(ECRSubmission.id == ecr_id)
    ).scalar_one_or_none()
    if not ecr_obj:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="ECR not found")

    req = ECRGenerateRequest(slip_month=ecr_obj.slip_month, slip_year=ecr_obj.slip_year)
    _, ecr_bytes = svc.generate_ecr(db, req, created_by=current_user.email)

    MONTH_NAMES = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    filename = f"ECR_{MONTH_NAMES[ecr_obj.slip_month]}_{ecr_obj.slip_year}.txt"

    return StreamingResponse(
        io.BytesIO(ecr_bytes),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# 13. MARK ECR AS SUBMITTED
# POST /api/payroll/statutory-compliance/ecr/{ecr_id}/submit
@router.post("/ecr/{ecr_id}/submit", response_model=ECRSubmissionResponse,
             summary="Mark ECR as submitted to EPFO portal")
def submit_ecr(
    ecr_id: int,
    acknowledgement_number: Optional[str] = Query(None),
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.mark_ecr_submitted(db, ecr_id, acknowledgement_number)


# ─────────────────────────────────────────────────────────────────────────────
# VPF
# ─────────────────────────────────────────────────────────────────────────────

# 14. LIST VPF ENROLLMENTS
# GET /api/payroll/statutory-compliance/vpf
@router.get("/vpf", response_model=List[VPFEnrollmentResponse],
            summary="List VPF (Voluntary Provident Fund) enrollments")
def list_vpf(
    active_only: bool  = Query(False),
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_vpf_enrollments(db, active_only=active_only)


# 15. ADD VPF
# POST /api/payroll/statutory-compliance/vpf
@router.post("/vpf", response_model=VPFEnrollmentResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Enroll employee in VPF")
def add_vpf(
    payload: VPFEnrollmentCreate,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.enroll_vpf(db, payload, created_by=current_user.email)


# 16. DEACTIVATE VPF
# DELETE /api/payroll/statutory-compliance/vpf/{vpf_id}
@router.delete("/vpf/{vpf_id}", response_model=VPFEnrollmentResponse,
               summary="Deactivate a VPF enrollment")
def deactivate_vpf(
    vpf_id: int,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.deactivate_vpf(db, vpf_id)


# ─────────────────────────────────────────────────────────────────────────────
# UAN
# ─────────────────────────────────────────────────────────────────────────────

# 17. LIST UAN ACTIVATIONS
# GET /api/payroll/statutory-compliance/uan
@router.get("/uan", response_model=List[UANActivationResponse],
            summary="List all UAN activations")
def list_uan(
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_uan_activations(db)


# 18. GET UAN FOR EMPLOYEE
# GET /api/payroll/statutory-compliance/uan/{employee_id}
@router.get("/uan/{employee_id}", response_model=UANActivationResponse,
            summary="Get UAN details for a specific employee")
def get_uan(
    employee_id: int,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.get_uan_by_employee(db, employee_id)


# 19. ACTIVATE UAN
# POST /api/payroll/statutory-compliance/uan/activate
@router.post("/uan/activate", response_model=UANActivationResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Activate or assign a UAN to an employee")
def activate_uan(
    payload: UANActivationCreate,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.activate_uan(db, payload, created_by=current_user.email)


# ─────────────────────────────────────────────────────────────────────────────
# GENERATE FORM (PF Forms 5/10C, 12A, Reconciliation, UAN Report)
# ─────────────────────────────────────────────────────────────────────────────

# 20. GENERATE FORM 5/10C  (Monthly PF Return)
# GET /api/payroll/statutory-compliance/forms/form5-10c
@router.get("/forms/form5-10c",
            summary="Generate Form 5/10C — Monthly PF Return")
def generate_form_5_10c(
    slip_month: int = Query(..., ge=1, le=12),
    slip_year:  int = Query(..., ge=2000, le=2100),
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statements = svc.get_pf_statements(db, slip_month, slip_year)
    if not statements:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No PF statements found for this period")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Employee Code", "Employee Name", "UAN Number",
        "Basic Wages", "PF Wages", "Employee PF",
        "Employer PF", "EPS", "EDLI", "VPF", "Total PF", "Status"
    ])
    for s in statements:
        writer.writerow([
            s.employee_code, s.employee_name, s.uan_number or "",
            s.basic_wages, s.pf_wage, s.employee_contribution,
            s.employer_contribution, s.eps_contribution,
            s.edli_contribution, s.vpf_amount, s.total_pf, s.status
        ])

    MONTH_NAMES = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    filename = f"Form5_10C_{MONTH_NAMES[slip_month]}_{slip_year}.csv"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# 21. GENERATE FORM 12A  (Annual PF Summary / Exit Form)
# GET /api/payroll/statutory-compliance/forms/form12a
@router.get("/forms/form12a",
            summary="Generate Form 12A — Annual PF Summary / Exit Transfer Form")
def generate_form_12a(
    slip_year: int = Query(..., ge=2000, le=2100),
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select as sa_select
    from model.Payroll.statutory_compliance import PFStatement

    statements = db.execute(
        sa_select(PFStatement).where(PFStatement.slip_year == slip_year)
        .order_by(PFStatement.employee_code, PFStatement.slip_month)
    ).scalars().all()

    if not statements:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No PF data for {slip_year}")

    # Aggregate by employee
    emp_map: dict = {}
    for s in statements:
        if s.employee_code not in emp_map:
            emp_map[s.employee_code] = {
                "code": s.employee_code, "name": s.employee_name,
                "uan": s.uan_number or "",
                "emp_total": Decimal("0"), "er_total": Decimal("0"),
                "eps_total": Decimal("0"), "edli_total": Decimal("0"),
            }
        emp_map[s.employee_code]["emp_total"] += _r2(s.employee_contribution)
        emp_map[s.employee_code]["er_total"]  += _r2(s.employer_contribution)
        emp_map[s.employee_code]["eps_total"] += _r2(s.eps_contribution)
        emp_map[s.employee_code]["edli_total"]+= _r2(s.edli_contribution)

    from services.Payroll.compliance_service import _r2
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Employee Code", "Employee Name", "UAN",
        "Annual Employee PF", "Annual Employer PF",
        "Annual EPS", "Annual EDLI",
        "Annual Total PF"
    ])
    for emp in emp_map.values():
        total = emp["emp_total"] + emp["er_total"]
        writer.writerow([
            emp["code"], emp["name"], emp["uan"],
            emp["emp_total"], emp["er_total"],
            emp["eps_total"], emp["edli_total"], total
        ])

    filename = f"Form12A_{slip_year}.csv"
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# 22. UAN UPDATE REPORT
# GET /api/payroll/statutory-compliance/forms/uan-report
@router.get("/forms/uan-report",
            summary="Download UAN Update Report for all employees")
def download_uan_report(
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = svc.list_uan_activations(db)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Employee Code", "Employee Name", "UAN Number",
        "Activation Date", "Status", "Remarks"
    ])
    for r in records:
        writer.writerow([
            r.employee_code, r.employee_name, r.uan_number,
            r.activation_date, r.status, r.remarks or ""
        ])

    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="UAN_Report.csv"'},
    )
