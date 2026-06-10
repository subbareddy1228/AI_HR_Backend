# services/Payroll/slip_service.py
# Complete service layer for SalarySlip module
# Includes: CRUD, generate, bulk generate, publish, unpublish,
#           soft-delete, KPI summary, components, settings, distribution log

import calendar
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from model.Payroll.salary_slip import SalarySlip, SalarySlipComponent
from model.Payroll.slip_distribution import SlipDistributionLog, SlipSettings
from model.Payroll.salary_structure import SalaryStructure, EmployeeSalaryMapping
from model.Payroll.statutory_compliance import StatutoryConfig
from model.onboarding.employee import Employee
from schema.Payroll.salary_slip import (
    SalarySlipCreate, SalarySlipUpdate,
    SalarySlipGenerateRequest, SalarySlipBulkGenerateRequest,
    SalarySlipKPIResponse,
)

TWO_PLACES = Decimal("0.01")


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _round2(value: float) -> Decimal:
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _get_slip_or_404(db: Session, slip_id: int) -> SalarySlip:
    slip = db.execute(
        select(SalarySlip).where(
            SalarySlip.id == slip_id,
            SalarySlip.is_deleted == False,
        )
    ).scalar_one_or_none()
    if not slip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Salary slip {slip_id} not found",
        )
    return slip


def _save_components(db: Session, slip_id: int, components: list):
    """Delete and re-insert components for a slip (used on generate/regenerate)."""
    existing = db.execute(
        select(SalarySlipComponent).where(SalarySlipComponent.salary_slip_id == slip_id)
    ).scalars().all()
    for c in existing:
        db.delete(c)

    for comp in components:
        obj = SalarySlipComponent(
            salary_slip_id = slip_id,
            component_type = comp["component_type"],
            component_name = comp["component_name"],
            component_code = comp.get("component_code"),
            amount         = comp["amount"],
            is_statutory   = comp.get("is_statutory", False),
            sort_order     = comp.get("sort_order", 0),
        )
        db.add(obj)


# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE ENGINE  (was slip_generator.py — merged here)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_salary(
    db: Session,
    employee_id: int,
    slip_month: int,
    slip_year: int,
    lop_days: int = 0,
    days_worked: Optional[int] = None,
) -> dict:
    """
    Core payroll compute engine.
    Reads Employee → EmployeeSalaryMapping → SalaryStructure → StatutoryConfig
    Returns a fully computed dict ready to save as a SalarySlip.
    """

    # 1. Employee
    employee = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found",
        )

    # 2. Salary mapping
    mapping = db.execute(
        select(EmployeeSalaryMapping).where(
            EmployeeSalaryMapping.employee_id == employee_id
        )
    ).scalar_one_or_none()
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No salary mapping for employee {employee_id}. Assign a salary structure first.",
        )

    # 3. Salary structure
    structure = db.execute(
        select(SalaryStructure).where(SalaryStructure.id == mapping.salary_structure_id)
    ).scalar_one_or_none()
    if not structure:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Salary structure not found. Reconfigure employee mapping.",
        )

    # 4. Statutory config
    stat = db.execute(
        select(StatutoryConfig).where(StatutoryConfig.config_name == "default")
    ).scalar_one_or_none()
    if not stat:
        stat = StatutoryConfig()   # safe defaults

    # 5. Attendance
    days_in_month = calendar.monthrange(slip_year, slip_month)[1]
    lop = max(0, int(lop_days or 0))
    if days_worked is None:
        days_worked = days_in_month - lop
    days_worked = max(0, min(days_worked, days_in_month))
    days_absent = days_in_month - days_worked

    lop_ratio = (
        Decimal(str((days_in_month - lop) / days_in_month))
        if lop > 0 and days_in_month > 0
        else Decimal("1.0")
    )

    # 6. Earnings
    monthly_ctc = Decimal(str(mapping.annual_ctc)) / Decimal("12")
    basic   = _round2(float(monthly_ctc) * (structure.basic_percent / 100)             * float(lop_ratio))
    hra     = _round2(float(monthly_ctc) * (structure.hra_percent / 100)               * float(lop_ratio))
    special = _round2(float(monthly_ctc) * (structure.special_allowance_percent / 100) * float(lop_ratio))
    gross   = basic + hra + special

    # 7. PF
    pf_wage    = min(basic, Decimal(str(stat.pf_wage_limit or 15000)))
    pf_emp     = _round2(float(pf_wage) * (float(stat.pf_employee_rate or 12.0) / 100))
    pf_er      = _round2(float(pf_wage) * (float(stat.pf_employer_rate or 12.0) / 100))

    # 8. ESI
    esi_limit  = Decimal(str(stat.esi_wage_limit or 21000))
    esi_eligible = gross <= esi_limit
    esi_emp    = _round2(float(gross) * (float(stat.esi_employee_rate or 0.75) / 100)) if esi_eligible else Decimal("0.00")
    esi_er     = _round2(float(gross) * (float(stat.esi_employer_rate or 3.25) / 100)) if esi_eligible else Decimal("0.00")

    # 9. Professional Tax
    pt         = _round2(float(structure.professional_tax_monthly or 200))

    # 10. TDS
    tds        = _round2(float(gross) * (float(structure.tds_percent or 0.0) / 100))

    # 11. LWF
    lwf        = _round2(float(stat.lwf_employee or 25))

    # 12. Totals
    total_deductions = pf_emp + esi_emp + pt + tds + lwf
    net_pay          = gross - total_deductions

    # 13. Components
    sort = 0
    def comp(ctype, name, code, amount, statutory=False):
        nonlocal sort
        sort += 1
        return dict(component_type=ctype, component_name=name,
                    component_code=code, amount=amount,
                    is_statutory=statutory, sort_order=sort)

    components = [
        comp("earning",   "Basic Salary",              "BASIC",    basic),
        comp("earning",   "House Rent Allowance",       "HRA",      hra),
        comp("earning",   "Special Allowance",          "SPEC_ALL", special),
        comp("deduction", "Provident Fund (Employee)",  "PF_EMP",   pf_emp,  True),
        comp("deduction", "ESI (Employee)",             "ESI_EMP",  esi_emp, True),
        comp("deduction", "Professional Tax",           "PT",       pt,      True),
        comp("deduction", "TDS",                        "TDS",      tds,     True),
        comp("deduction", "Labour Welfare Fund",        "LWF",      lwf,     True),
    ]

    full_name = f"{employee.first_name} {employee.last_name or ''}".strip()

    return dict(
        employee_id      = employee_id,
        employee_code    = employee.employee_code,
        employee_name    = full_name,
        department       = employee.department,
        designation      = employee.designation,
        official_email   = employee.official_email,
        pan_number       = None,
        uan_number       = None,
        bank_account     = None,
        bank_name        = None,
        slip_month       = slip_month,
        slip_year        = slip_year,
        days_in_month    = days_in_month,
        days_worked      = days_worked,
        days_absent      = days_absent,
        lop_days         = lop,
        gross_salary     = gross,
        total_earnings   = gross,
        total_deductions = total_deductions,
        net_pay          = net_pay,
        components       = components,
        _pf_employer     = pf_er,
        _esi_employer    = esi_er,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ORIGINAL CRUD  (kept as-is for backward compatibility)
# ─────────────────────────────────────────────────────────────────────────────

def create_salary_slip(db: Session, payload: SalarySlipCreate) -> SalarySlip:
    """Create a new salary slip (manual). Use generate_salary_slip for auto-compute."""
    data = payload.model_dump(exclude={"components"})
    obj  = SalarySlip(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_salary_slips(
    db: Session,
    employee_id:  Optional[int]  = None,
    slip_month:   Optional[int]  = None,
    slip_year:    Optional[int]  = None,
    is_published: Optional[bool] = None,
    skip:  int = 0,
    limit: int = 100,
) -> List[SalarySlip]:
    stmt = select(SalarySlip).where(SalarySlip.is_deleted == False)
    if employee_id is not None:
        stmt = stmt.where(SalarySlip.employee_id == employee_id)
    if slip_month is not None:
        stmt = stmt.where(SalarySlip.slip_month == slip_month)
    if slip_year is not None:
        stmt = stmt.where(SalarySlip.slip_year == slip_year)
    if is_published is not None:
        stmt = stmt.where(SalarySlip.is_published == is_published)
    stmt = stmt.order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_salary_slip(db: Session, slip_id: int) -> SalarySlip:
    return _get_slip_or_404(db, slip_id)


def get_slips_by_employee(db: Session, employee_id: int) -> List[SalarySlip]:
    return db.execute(
        select(SalarySlip)
        .where(SalarySlip.employee_id == employee_id, SalarySlip.is_deleted == False)
        .order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())
    ).scalars().all()


def update_salary_slip(db: Session, slip_id: int, payload: SalarySlipUpdate) -> SalarySlip:
    obj = _get_slip_or_404(db, slip_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_salary_slip(db: Session, slip_id: int) -> None:
    """Soft delete — sets is_deleted=True."""
    obj = _get_slip_or_404(db, slip_id)
    obj.is_deleted = True
    db.commit()


def publish_salary_slip(db: Session, slip_id: int) -> SalarySlip:
    obj = _get_slip_or_404(db, slip_id)
    obj.is_published = True
    db.commit()
    db.refresh(obj)
    return obj


def unpublish_salary_slip(db: Session, slip_id: int) -> SalarySlip:
    obj = _get_slip_or_404(db, slip_id)
    obj.is_published = False
    db.commit()
    db.refresh(obj)
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# GENERATE  (new — auto-compute from CTC + structure)
# ─────────────────────────────────────────────────────────────────────────────

def generate_salary_slip(
    db: Session,
    req: SalarySlipGenerateRequest,
    generated_by: Optional[str] = None,
) -> SalarySlip:
    """
    Compute and persist a salary slip for one employee.
    Regenerates (upsert) if a slip already exists for the same period.
    """
    computed = _compute_salary(
        db, req.employee_id, req.slip_month, req.slip_year
    )

    # Upsert check
    existing = db.execute(
        select(SalarySlip).where(
            SalarySlip.employee_id == req.employee_id,
            SalarySlip.slip_month  == req.slip_month,
            SalarySlip.slip_year   == req.slip_year,
            SalarySlip.is_deleted  == False,
        )
    ).scalar_one_or_none()

    if existing:
        for key, val in computed.items():
            if key.startswith("_") or key == "components":
                continue
            if hasattr(existing, key):
                setattr(existing, key, val)
        existing.payroll_run_id = req.payroll_run_id
        existing.generated_by   = generated_by
        existing.is_published    = False
        db.flush()
        _save_components(db, existing.id, computed["components"])
        db.commit()
        db.refresh(existing)
        return existing

    slip = SalarySlip(
        employee_id      = computed["employee_id"],
        payroll_run_id   = req.payroll_run_id,
        slip_month       = computed["slip_month"],
        slip_year        = computed["slip_year"],
        employee_code    = computed["employee_code"],
        employee_name    = computed["employee_name"],
        department       = computed["department"],
        designation      = computed["designation"],
        official_email   = computed["official_email"],
        pan_number       = computed["pan_number"],
        uan_number       = computed["uan_number"],
        bank_account     = computed["bank_account"],
        bank_name        = computed["bank_name"],
        days_in_month    = computed["days_in_month"],
        days_worked      = computed["days_worked"],
        days_absent      = computed["days_absent"],
        lop_days         = computed["lop_days"],
        gross_salary     = computed["gross_salary"],
        total_earnings   = computed["total_earnings"],
        total_deductions = computed["total_deductions"],
        net_pay          = computed["net_pay"],
        generated_by     = generated_by,
    )
    db.add(slip)
    db.flush()
    _save_components(db, slip.id, computed["components"])
    db.commit()
    db.refresh(slip)
    return slip


def bulk_generate_salary_slips(
    db: Session,
    req: SalarySlipBulkGenerateRequest,
    generated_by: Optional[str] = None,
) -> tuple:
    """Generate salary slips for all active employees for a period."""
    employees = db.execute(
        select(Employee).where(Employee.is_active == True)
    ).scalars().all()

    results, errors = [], []
    for emp in employees:
        try:
            single = SalarySlipGenerateRequest(
                employee_id    = emp.id,
                slip_month     = req.slip_month,
                slip_year      = req.slip_year,
                payroll_run_id = req.payroll_run_id,
            )
            results.append(generate_salary_slip(db, single, generated_by))
        except HTTPException as e:
            errors.append({"employee_id": emp.id, "error": e.detail})
        except Exception as e:
            errors.append({"employee_id": emp.id, "error": str(e)})

    return results, errors


def preview_salary_slip(
    db: Session,
    employee_id: int,
    slip_month: int,
    slip_year: int,
) -> dict:
    """Compute without saving — for the Show Preview button."""
    data = _compute_salary(db, employee_id, slip_month, slip_year)
    data.pop("_pf_employer",  None)
    data.pop("_esi_employer", None)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

def get_components(db: Session, slip_id: int) -> List[SalarySlipComponent]:
    return db.execute(
        select(SalarySlipComponent)
        .where(SalarySlipComponent.salary_slip_id == slip_id)
        .order_by(SalarySlipComponent.sort_order)
    ).scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# KPI
# ─────────────────────────────────────────────────────────────────────────────

def get_kpi_summary(
    db: Session,
    slip_month: Optional[int] = None,
    slip_year:  Optional[int] = None,
) -> SalarySlipKPIResponse:
    stmt = select(SalarySlip).where(SalarySlip.is_deleted == False)
    if slip_month:
        stmt = stmt.where(SalarySlip.slip_month == slip_month)
    if slip_year:
        stmt = stmt.where(SalarySlip.slip_year == slip_year)

    slips          = db.execute(stmt).scalars().all()
    total_slips    = len(slips)
    distributed    = sum(1 for s in slips if s.is_emailed or s.is_published)
    total_payout   = sum(Decimal(str(s.net_pay)) for s in slips)
    active_employees = db.execute(
        select(func.count(Employee.id)).where(Employee.is_active == True)
    ).scalar() or 0

    return SalarySlipKPIResponse(
        total_slips_generated = total_slips,
        active_employees      = active_employees,
        distributed_slips     = distributed,
        total_payout          = total_payout,
        slip_month            = slip_month,
        slip_year             = slip_year,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS  (was in slip_pdf_service — merged here)
# ─────────────────────────────────────────────────────────────────────────────

def get_slip_settings(db: Session) -> SlipSettings:
    settings = db.execute(select(SlipSettings)).scalar_one_or_none()
    if not settings:
        settings = SlipSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_slip_settings(db: Session, payload) -> SlipSettings:
    settings = get_slip_settings(db)
    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, val)
    db.commit()
    db.refresh(settings)
    return settings


# ─────────────────────────────────────────────────────────────────────────────
# DISTRIBUTION LOG
# ─────────────────────────────────────────────────────────────────────────────

def log_distribution(
    db: Session,
    slip_id: int,
    employee_id: int,
    method: str,
    sent_by: Optional[str] = None,
    recipient_email: Optional[str] = None,
    log_status: str = "sent",
    error_message: Optional[str] = None,
) -> SlipDistributionLog:
    log = SlipDistributionLog(
        salary_slip_id      = slip_id,
        employee_id         = employee_id,
        distribution_method = method,
        recipient_email     = recipient_email,
        sent_by             = sent_by,
        status              = log_status,
        error_message       = error_message,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_distribution_logs(
    db: Session,
    slip_month:  Optional[int] = None,
    slip_year:   Optional[int] = None,
    employee_id: Optional[int] = None,
    skip:  int = 0,
    limit: int = 100,
) -> List[SlipDistributionLog]:
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
