# services/Payroll/compliance_service.py
# NEW FILE — place in services/Payroll/
# Full business logic for Statutory Compliance Engine







# services/statutory_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException

from model.onboarding.statutory import StatutoryDetails
from schema.onboarding.statutory import StatutoryCreate


def create_statutory_details(db: Session, payload: StatutoryCreate) -> StatutoryDetails:
    existing = db.query(StatutoryDetails).filter(
        StatutoryDetails.aadhaar_number == payload.aadhaar_number
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Statutory details already exist for this Aadhaar number")

    record = StatutoryDetails(
        aadhaar_number = payload.aadhaar_number,
        pan_number     = payload.pan_number,
        uan_number     = payload.uan_number,
        esi_number     = payload.esi_number,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
import json
import csv
import io
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Tuple
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from model.Payroll.statutory_compliance import (
    StatutoryConfig, PFStatement, PFRemittance,
    ECRSubmission, VPFEnrollment, UANActivation,
)
from model.Payroll.salary_structure import EmployeeSalaryMapping
from model.onboarding.employee import Employee
from model.onboarding.statutory import StatutoryDetails
from schema.Payroll.statutory_compliance import (
    StatutoryConfigUpdate,
    PFStatementCalculateRequest,
    PFRemittanceCreate, PFRemittanceUpdate,
    ECRGenerateRequest,
    VPFEnrollmentCreate,
    UANActivationCreate,
    ComplianceKPIResponse,
)

TWO = Decimal("0.01")
MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def _r2(v) -> Decimal:
    return Decimal(str(v)).quantize(TWO, rounding=ROUND_HALF_UP)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

def get_config(db: Session) -> StatutoryConfig:
    cfg = db.execute(
        select(StatutoryConfig).where(StatutoryConfig.config_name == "default")
    ).scalar_one_or_none()
    if not cfg:
        cfg = StatutoryConfig(config_name="default")
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def update_config(db: Session, payload: StatutoryConfigUpdate) -> StatutoryConfig:
    cfg = get_config(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cfg, k, v)
    db.commit()
    db.refresh(cfg)
    return cfg


# ─────────────────────────────────────────────────────────────────────────────
# KPI SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def get_compliance_kpi(
    db: Session,
    slip_month: Optional[int] = None,
    slip_year: Optional[int] = None,
) -> ComplianceKPIResponse:
    stmt = select(PFStatement)
    if slip_month:
        stmt = stmt.where(PFStatement.slip_month == slip_month)
    if slip_year:
        stmt = stmt.where(PFStatement.slip_year == slip_year)

    statements = db.execute(stmt).scalars().all()

    total_pf  = sum(_r2(s.total_pf) for s in statements)
    total_emp = sum(_r2(s.employee_contribution) for s in statements)
    total_er  = sum(_r2(s.employer_contribution) for s in statements)

    # ESI: read from salary_slip_components if available else estimate
    try:
        from model.Payroll.salary_slip import SalarySlipComponent
        esi_q = select(func.sum(SalarySlipComponent.amount)).where(
            SalarySlipComponent.component_code == "ESI_EMP"
        )
        total_esi = db.execute(esi_q).scalar() or Decimal("0")
    except Exception:
        total_esi = Decimal("0")

    # TDS
    try:
        from model.Payroll.salary_slip import SalarySlipComponent
        tds_q = select(func.sum(SalarySlipComponent.amount)).where(
            SalarySlipComponent.component_code == "TDS"
        )
        total_tds = db.execute(tds_q).scalar() or Decimal("0")
    except Exception:
        total_tds = Decimal("0")

    # Pending declarations = employees without UAN
    active_employees = db.execute(
        select(func.count(Employee.id)).where(Employee.is_active == True)
    ).scalar() or 0
    activated_uans = db.execute(
        select(func.count(UANActivation.id)).where(UANActivation.status == "Active")
    ).scalar() or 0
    pending = max(0, active_employees - activated_uans)

    return ComplianceKPIResponse(
        total_pf_contribution  = _r2(total_pf),
        total_esi_contribution = _r2(total_esi),
        total_tds_deduction    = _r2(total_tds),
        pending_declarations   = pending,
        slip_month             = slip_month,
        slip_year              = slip_year,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PF STATEMENTS — calculate for all employees for a period
# ─────────────────────────────────────────────────────────────────────────────

def _get_employee_basic(db: Session, employee_id: int) -> Decimal:
    """Get monthly basic salary from salary mapping + structure."""
    try:
        from model.Payroll.salary_structure import SalaryStructure, EmployeeSalaryMapping
        mapping = db.execute(
            select(EmployeeSalaryMapping).where(
                EmployeeSalaryMapping.employee_id == employee_id
            )
        ).scalar_one_or_none()
        if not mapping:
            return Decimal("0")
        structure = db.execute(
            select(SalaryStructure).where(SalaryStructure.id == mapping.salary_structure_id)
        ).scalar_one_or_none()
        if not structure:
            return Decimal("0")
        monthly_ctc = Decimal(str(mapping.annual_ctc)) / Decimal("12")
        return _r2(float(monthly_ctc) * (structure.basic_percent / 100))
    except Exception:
        return Decimal("0")


def _get_vpf_amount(db: Session, employee_id: int, basic: Decimal) -> Decimal:
    vpf = db.execute(
        select(VPFEnrollment).where(
            VPFEnrollment.employee_id == employee_id,
            VPFEnrollment.status == "Active",
        )
    ).scalar_one_or_none()
    if vpf:
        return _r2(float(basic) * (vpf.vpf_rate / 100))
    return Decimal("0")


def _get_uan(db: Session, employee_id: int) -> Optional[str]:
    uan = db.execute(
        select(UANActivation).where(
            UANActivation.employee_id == employee_id,
            UANActivation.status == "Active",
        )
    ).scalar_one_or_none()
    if uan:
        return uan.uan_number
    stat = db.execute(
        select(StatutoryDetails).where(StatutoryDetails.id == employee_id)
    ).scalar_one_or_none()
    return stat.uan_number if stat else None


def calculate_pf_statements(
    db: Session,
    slip_month: int,
    slip_year: int,
    calculated_by: Optional[str] = None,
) -> Tuple[List[PFStatement], List[dict]]:
    """
    Calculate PF for all active employees for the given period.
    Upserts — safe to call multiple times.
    """
    cfg = get_config(db)
    employees = db.execute(
        select(Employee).where(Employee.is_active == True)
    ).scalars().all()

    results, errors = [], []

    for emp in employees:
        try:
            full_name = f"{emp.first_name} {emp.last_name or ''}".strip()
            basic     = _get_employee_basic(db, emp.id)

            if basic == Decimal("0"):
                errors.append({"employee_id": emp.id, "error": "No salary mapping found"})
                continue

            pf_wage_limit = Decimal(str(cfg.pf_wage_limit or 15000))
            pf_wage       = min(basic, pf_wage_limit)

            emp_contrib = _r2(float(pf_wage) * (float(cfg.pf_employee_rate or 12.0) / 100))
            er_contrib  = _r2(float(pf_wage) * (float(cfg.pf_employer_rate or 12.0) / 100))
            eps         = _r2(float(pf_wage) * (float(cfg.eps_rate or 3.67) / 100))
            edli        = _r2(float(pf_wage) * (float(cfg.edli_rate or 0.5) / 100))
            vpf         = _get_vpf_amount(db, emp.id, basic)
            total_pf    = emp_contrib + er_contrib + vpf
            uan         = _get_uan(db, emp.id)

            # Upsert
            existing = db.execute(
                select(PFStatement).where(
                    PFStatement.employee_id == emp.id,
                    PFStatement.slip_month  == slip_month,
                    PFStatement.slip_year   == slip_year,
                )
            ).scalar_one_or_none()

            if existing:
                existing.basic_wages           = basic
                existing.pf_wage               = pf_wage
                existing.employee_contribution = emp_contrib
                existing.employer_contribution = er_contrib
                existing.eps_contribution      = eps
                existing.edli_contribution     = edli
                existing.vpf_amount            = vpf
                existing.total_pf              = total_pf
                existing.uan_number            = uan
                results.append(existing)
            else:
                stmt = PFStatement(
                    employee_id           = emp.id,
                    employee_code         = emp.employee_code,
                    employee_name         = full_name,
                    uan_number            = uan,
                    slip_month            = slip_month,
                    slip_year             = slip_year,
                    basic_wages           = basic,
                    pf_wage               = pf_wage,
                    employee_contribution = emp_contrib,
                    employer_contribution = er_contrib,
                    eps_contribution      = eps,
                    edli_contribution     = edli,
                    vpf_amount            = vpf,
                    total_pf              = total_pf,
                )
                db.add(stmt)
                results.append(stmt)

        except Exception as e:
            errors.append({"employee_id": emp.id, "error": str(e)})

    db.commit()
    return results, errors


def get_pf_statements(
    db: Session,
    slip_month: int,
    slip_year: int,
) -> List[PFStatement]:
    return db.execute(
        select(PFStatement).where(
            PFStatement.slip_month == slip_month,
            PFStatement.slip_year  == slip_year,
        ).order_by(PFStatement.employee_code)
    ).scalars().all()


def get_pf_statement_single(db: Session, employee_id: int, slip_month: int, slip_year: int) -> PFStatement:
    stmt = db.execute(
        select(PFStatement).where(
            PFStatement.employee_id == employee_id,
            PFStatement.slip_month  == slip_month,
            PFStatement.slip_year   == slip_year,
        )
    ).scalar_one_or_none()
    if not stmt:
        raise HTTPException(status_code=404, detail="PF statement not found for this employee/period")
    return stmt


# ─────────────────────────────────────────────────────────────────────────────
# PF REMITTANCES
# ─────────────────────────────────────────────────────────────────────────────

def create_pf_remittance(
    db: Session,
    payload: PFRemittanceCreate,
    created_by: Optional[str] = None,
) -> PFRemittance:
    # Check existing
    existing = db.execute(
        select(PFRemittance).where(
            PFRemittance.slip_month == payload.slip_month,
            PFRemittance.slip_year  == payload.slip_year,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Remittance already exists for {MONTH_NAMES[payload.slip_month]} {payload.slip_year}. Use update instead."
        )

    # Aggregate from PF statements
    statements = db.execute(
        select(PFStatement).where(
            PFStatement.slip_month == payload.slip_month,
            PFStatement.slip_year  == payload.slip_year,
        )
    ).scalars().all()

    if not statements:
        raise HTTPException(
            status_code=404,
            detail=f"No PF statements found for {MONTH_NAMES[payload.slip_month]} {payload.slip_year}. Run Calculate first."
        )

    total_emp  = sum(_r2(s.employee_contribution) for s in statements)
    total_er   = sum(_r2(s.employer_contribution)  for s in statements)
    total_eps  = sum(_r2(s.eps_contribution)        for s in statements)
    total_edli = sum(_r2(s.edli_contribution)       for s in statements)
    total      = total_emp + total_er

    rem = PFRemittance(
        slip_month            = payload.slip_month,
        slip_year             = payload.slip_year,
        challan_number        = payload.challan_number,
        remittance_date       = payload.remittance_date,
        total_employees       = len(statements),
        total_contribution    = total,
        employee_contribution = total_emp,
        employer_contribution = total_er,
        eps_contribution      = total_eps,
        edli_contribution     = total_edli,
        status                = "Paid" if payload.challan_number else "Pending",
        remarks               = payload.remarks,
        created_by            = created_by,
    )
    db.add(rem)
    db.flush()

    # Link statements to this remittance and mark Paid
    for s in statements:
        s.remittance_id = rem.id
        s.status = "Paid" if payload.challan_number else "Pending"

    db.commit()
    db.refresh(rem)
    return rem


def list_pf_remittances(
    db: Session,
    slip_year: Optional[int] = None,
) -> List[PFRemittance]:
    stmt = select(PFRemittance)
    if slip_year:
        stmt = stmt.where(PFRemittance.slip_year == slip_year)
    return db.execute(stmt.order_by(PFRemittance.slip_year.desc(), PFRemittance.slip_month.desc())).scalars().all()


def update_pf_remittance(
    db: Session, remittance_id: int, payload: PFRemittanceUpdate
) -> PFRemittance:
    rem = db.execute(
        select(PFRemittance).where(PFRemittance.id == remittance_id)
    ).scalar_one_or_none()
    if not rem:
        raise HTTPException(status_code=404, detail="Remittance not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(rem, k, v)
    # If challan number added → mark paid
    if payload.challan_number and rem.status == "Pending":
        rem.status = "Paid"
        statements = db.execute(
            select(PFStatement).where(
                PFStatement.remittance_id == remittance_id
            )
        ).scalars().all()
        for s in statements:
            s.status = "Paid"
    db.commit()
    db.refresh(rem)
    return rem


# ─────────────────────────────────────────────────────────────────────────────
# ECR
# ─────────────────────────────────────────────────────────────────────────────

def generate_ecr(
    db: Session,
    req: ECRGenerateRequest,
    created_by: Optional[str] = None,
) -> Tuple[ECRSubmission, bytes]:
    """
    Generate ECR submission record + downloadable ECR text file (EPFO format).
    Returns (ECRSubmission ORM object, ecr_bytes).
    """
    statements = db.execute(
        select(PFStatement).where(
            PFStatement.slip_month == req.slip_month,
            PFStatement.slip_year  == req.slip_year,
        )
    ).scalars().all()

    if not statements:
        raise HTTPException(
            status_code=404,
            detail=f"No PF statements for {MONTH_NAMES[req.slip_month]} {req.slip_year}. Run Calculate first."
        )

    # Build ECR text (EPFO standard tab-delimited format)
    buf = io.StringIO()
    buf.write(f"#~#\n")  # Header marker
    buf.write(f"ECR\t1.0\t{req.slip_month:02d}/{req.slip_year}\n")

    total_wages = Decimal("0")
    total_epf   = Decimal("0")
    total_eps   = Decimal("0")
    total_edli  = Decimal("0")

    for i, s in enumerate(statements, 1):
        uan = s.uan_number or "PENDING"
        buf.write(
            f"{i}\t{uan}\t{s.employee_name}\t"
            f"{s.basic_wages}\t{s.pf_wage}\t"
            f"{s.employee_contribution}\t{s.employer_contribution}\t"
            f"{s.eps_contribution}\t{s.edli_contribution}\t"
            f"{s.vpf_amount}\n"
        )
        total_wages += _r2(s.basic_wages)
        total_epf   += _r2(s.employee_contribution) + _r2(s.employer_contribution)
        total_eps   += _r2(s.eps_contribution)
        total_edli  += _r2(s.edli_contribution)

    ecr_bytes = buf.getvalue().encode("utf-8")

    # Upsert ECR record
    existing = db.execute(
        select(ECRSubmission).where(
            ECRSubmission.slip_month == req.slip_month,
            ECRSubmission.slip_year  == req.slip_year,
        )
    ).scalar_one_or_none()

    if existing:
        existing.total_employees  = len(statements)
        existing.total_wages      = total_wages
        existing.epf_contribution = total_epf
        existing.eps_contribution = total_eps
        existing.edli_contribution= total_edli
        existing.status           = "Draft"
        db.commit()
        db.refresh(existing)
        return existing, ecr_bytes

    ecr = ECRSubmission(
        slip_month        = req.slip_month,
        slip_year         = req.slip_year,
        total_employees   = len(statements),
        total_wages       = total_wages,
        epf_contribution  = total_epf,
        eps_contribution  = total_eps,
        edli_contribution = total_edli,
        status            = "Draft",
        created_by        = created_by,
    )
    db.add(ecr)
    db.commit()
    db.refresh(ecr)
    return ecr, ecr_bytes


def list_ecr_submissions(db: Session) -> List[ECRSubmission]:
    return db.execute(
        select(ECRSubmission).order_by(
            ECRSubmission.slip_year.desc(), ECRSubmission.slip_month.desc()
        )
    ).scalars().all()


def mark_ecr_submitted(
    db: Session,
    ecr_id: int,
    acknowledgement_number: Optional[str] = None,
) -> ECRSubmission:
    ecr = db.execute(
        select(ECRSubmission).where(ECRSubmission.id == ecr_id)
    ).scalar_one_or_none()
    if not ecr:
        raise HTTPException(status_code=404, detail="ECR submission not found")
    ecr.status                 = "Submitted"
    ecr.submitted_date         = date.today()
    ecr.acknowledgement_number = acknowledgement_number
    db.commit()
    db.refresh(ecr)
    return ecr


# ─────────────────────────────────────────────────────────────────────────────
# VPF
# ─────────────────────────────────────────────────────────────────────────────

def enroll_vpf(
    db: Session,
    payload: VPFEnrollmentCreate,
    created_by: Optional[str] = None,
) -> VPFEnrollment:
    emp = db.execute(
        select(Employee).where(Employee.id == payload.employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee {payload.employee_id} not found")

    # Deactivate existing VPF for this employee
    existing = db.execute(
        select(VPFEnrollment).where(
            VPFEnrollment.employee_id == payload.employee_id,
            VPFEnrollment.status == "Active",
        )
    ).scalars().all()
    for e in existing:
        e.status       = "Inactive"
        e.effective_to = payload.effective_from

    full_name = f"{emp.first_name} {emp.last_name or ''}".strip()
    vpf = VPFEnrollment(
        employee_id    = payload.employee_id,
        employee_name  = full_name,
        employee_code  = emp.employee_code,
        vpf_rate       = payload.vpf_rate,
        effective_from = payload.effective_from,
        status         = "Active",
        created_by     = created_by,
    )
    db.add(vpf)
    db.commit()
    db.refresh(vpf)
    return vpf


def list_vpf_enrollments(
    db: Session,
    active_only: bool = False,
) -> List[VPFEnrollment]:
    stmt = select(VPFEnrollment)
    if active_only:
        stmt = stmt.where(VPFEnrollment.status == "Active")
    return db.execute(stmt.order_by(VPFEnrollment.employee_code)).scalars().all()


def deactivate_vpf(db: Session, vpf_id: int) -> VPFEnrollment:
    vpf = db.execute(
        select(VPFEnrollment).where(VPFEnrollment.id == vpf_id)
    ).scalar_one_or_none()
    if not vpf:
        raise HTTPException(status_code=404, detail="VPF enrollment not found")
    vpf.status       = "Inactive"
    vpf.effective_to = date.today()
    db.commit()
    db.refresh(vpf)
    return vpf


# ─────────────────────────────────────────────────────────────────────────────
# UAN
# ─────────────────────────────────────────────────────────────────────────────

def activate_uan(
    db: Session,
    payload: UANActivationCreate,
    created_by: Optional[str] = None,
) -> UANActivation:
    emp = db.execute(
        select(Employee).where(Employee.id == payload.employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee {payload.employee_id} not found")

    # Check duplicate UAN
    dup = db.execute(
        select(UANActivation).where(UANActivation.uan_number == payload.uan_number)
    ).scalar_one_or_none()
    if dup and dup.employee_id != payload.employee_id:
        raise HTTPException(
            status_code=409,
            detail=f"UAN {payload.uan_number} already assigned to another employee"
        )

    # Check existing for this employee
    existing = db.execute(
        select(UANActivation).where(UANActivation.employee_id == payload.employee_id)
    ).scalar_one_or_none()

    full_name = f"{emp.first_name} {emp.last_name or ''}".strip()

    if existing:
        existing.uan_number       = payload.uan_number
        existing.activation_date  = payload.activation_date
        existing.status           = "Active"
        existing.remarks          = payload.remarks
        db.commit()
        db.refresh(existing)
        return existing

    uan = UANActivation(
        employee_id     = payload.employee_id,
        employee_name   = full_name,
        employee_code   = emp.employee_code,
        uan_number      = payload.uan_number,
        activation_date = payload.activation_date,
        status          = "Active",
        remarks         = payload.remarks,
        created_by      = created_by,
    )
    db.add(uan)
    db.commit()
    db.refresh(uan)
    return uan


def list_uan_activations(db: Session) -> List[UANActivation]:
    return db.execute(
        select(UANActivation).order_by(UANActivation.employee_code)
    ).scalars().all()


def get_uan_by_employee(db: Session, employee_id: int) -> UANActivation:
    uan = db.execute(
        select(UANActivation).where(UANActivation.employee_id == employee_id)
    ).scalar_one_or_none()
    if not uan:
        raise HTTPException(status_code=404, detail="UAN record not found for this employee")
    return uan
