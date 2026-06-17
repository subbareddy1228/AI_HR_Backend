
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func
from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime
from decimal import Decimal
from calendar import month_name
import json

from model.Payroll.salary_slip import (
    SalarySlip, SalarySlipConfig, DistributionSettings,
    SalarySlipDistribution, SlipStatus, DistributionStatus,
    DistributionMethod,
)
from model.Payroll.payroll_run import PayrollRunDetail, PayrollRun
from model.onboarding.employee import Employee

from schema.Payroll.salary_slip import (
    SalarySlipCreate, SalarySlipUpdate,
    SalarySlipConfigCreate, SalarySlipConfigUpdate,
    DistributionSettingsCreate, DistributionSettingsUpdate,
    GenerateSlipRequest, GenerateAllRequest, GenerateSlipResponse,
    DistributeSlipRequest, BulkDistributeRequest,
    SalarySlipDashboard, SlipHistoryRow, SlipHistoryResponse,
    ExportRequest,
)


def get_dashboard(db: Session) -> SalarySlipDashboard:

    total_slips = db.execute(
        select(func.count()).select_from(SalarySlip)
    ).scalar_one()

    active_employees = db.execute(
        select(func.count()).select_from(Employee)
        .where(Employee.is_active == True)
    ).scalar_one()

    distributed = db.execute(
        select(func.count()).select_from(SalarySlip)
        .where(SalarySlip.status == SlipStatus.DISTRIBUTED)
    ).scalar_one()

    total_payout = db.execute(
        select(func.coalesce(func.sum(SalarySlip.net_pay), 0))
    ).scalar_one()

    return SalarySlipDashboard(
        total_slips_generated=total_slips,
        active_employees=active_employees,
        distributed_slips=distributed,
        total_payout=Decimal(str(total_payout)),
    )


def generate_slip(db: Session, req: GenerateSlipRequest) -> SalarySlip:

    employee = _get_employee(db, req.employee_id)

    run_detail = db.execute(
        select(PayrollRunDetail)
        .join(PayrollRun, PayrollRunDetail.payroll_run_id == PayrollRun.id)
        .where(
            PayrollRunDetail.employee_id == req.employee_id,
            PayrollRun.run_month == req.pay_period_month,
            PayrollRun.run_year == req.pay_period_year,
        )
    ).scalar_one_or_none()

    if not run_detail:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No payroll run found for employee {req.employee_id} "
                f"for {req.pay_period_month}/{req.pay_period_year}. "
                "Run payroll processing first."
            ),
        )

    # Check for existing slip — respect revision rules
    existing = _get_existing_slip(db, req.employee_id, req.pay_period_month, req.pay_period_year)
    if existing:
        config = _get_or_create_config(db)
        if not config.allow_salary_slip_revisions:
            raise HTTPException(
                status_code=409,
                detail="Salary slip already exists and revisions are disabled.",
            )
        existing.revision_count += 1
        existing.revised_at = datetime.utcnow()
        _populate_slip_from_detail(existing, run_detail, req.distribution_method,
                                   req.protect_with_dob)
        db.commit()
        db.refresh(existing)
        return existing

    slip = SalarySlip(
        employee_id=req.employee_id,
        payroll_run_id=run_detail.payroll_run_id,
        slip_month=req.pay_period_month,
        slip_year=req.pay_period_year,
        employee_code=employee.employee_code,
        employee_name=f"{employee.first_name} {employee.last_name or ''}".strip(),
        department=employee.department,
        designation=employee.designation,
        gross_salary=run_detail.gross_salary,
        total_deductions=run_detail.total_deductions,
        net_pay=run_detail.net_pay,
        earnings_json=_build_earnings_json(run_detail),
        deductions_json=_build_deductions_json(run_detail),
        distribution_method=req.distribution_method,
        is_password_protected=req.protect_with_dob,
        status=SlipStatus.GENERATED,
        slip_code=_generate_slip_code(req.pay_period_year, req.pay_period_month),
    )
    db.add(slip)
    db.commit()
    db.refresh(slip)

    # Auto-send if configured
    cfg = _get_or_create_config(db)
    dist_settings = _get_or_create_distribution_settings(db)
    if cfg.auto_send_on_generation and dist_settings.send_automatic_email:
        _create_distribution_record(db, slip, dist_settings)

    return slip


def generate_all_slips(db: Session, req: GenerateAllRequest) -> GenerateSlipResponse:

    if req.employee_ids:
        employees = db.execute(
            select(Employee).where(Employee.id.in_(req.employee_ids))
        ).scalars().all()
    else:
        employees = db.execute(
            select(Employee).where(Employee.is_active == True)
        ).scalars().all()

    generated = []
    skipped = 0
    failed = 0

    for emp in employees:
        try:
            single_req = GenerateSlipRequest(
                employee_id=emp.id,
                pay_period_month=req.pay_period_month,
                pay_period_year=req.pay_period_year,
                distribution_method=req.distribution_method,
                protect_with_dob=req.protect_with_dob,
            )
            slip = generate_slip(db, single_req)
            generated.append(slip)
        except HTTPException as e:
            if e.status_code == 409:
                skipped += 1
            else:
                failed += 1

    total_payout = sum(s.net_pay for s in generated) or Decimal("0")

    return GenerateSlipResponse(
        generated=generated,
        skipped=skipped,
        failed=failed,
        total_payout=Decimal(str(total_payout)),
    )


def get_slip_preview(db: Session, employee_id: int, month: int, year: int) -> dict:

    employee = _get_employee(db, employee_id)
    run_detail = db.execute(
        select(PayrollRunDetail)
        .join(PayrollRun, PayrollRunDetail.payroll_run_id == PayrollRun.id)
        .where(
            PayrollRunDetail.employee_id == employee_id,
            PayrollRun.run_month == month,
            PayrollRun.run_year == year,
        )
    ).scalar_one_or_none()

    config = _get_or_create_config(db)

    return {
        "employee": {
            "id": employee.id,
            "code": employee.employee_code,
            "name": f"{employee.first_name} {employee.last_name or ''}".strip(),
            "designation": employee.designation,
            "department": employee.department,
            "email": employee.official_email or employee.personal_email,
            "phone": employee.mobile_number,
        },
        "pay_period": f"{month_name[month]} {year}",
        "payroll_detail": {
            "basic": float(run_detail.basic) if run_detail else 0,
            "hra": float(run_detail.hra) if run_detail else 0,
            "special_allowance": float(run_detail.special_allowance) if run_detail else 0,
            "gross_salary": float(run_detail.gross_salary) if run_detail else 0,
            "pf_employee": float(run_detail.pf_employee) if run_detail else 0,
            "esi_employee": float(run_detail.esi_employee) if run_detail else 0,
            "professional_tax": float(run_detail.professional_tax) if run_detail else 0,
            "tds": float(run_detail.tds) if run_detail else 0,
            "total_deductions": float(run_detail.total_deductions) if run_detail else 0,
            "net_pay": float(run_detail.net_pay) if run_detail else 0,
            "days_worked": run_detail.days_worked if run_detail else None,
            "days_absent": run_detail.days_absent if run_detail else None,
        } if run_detail else None,
        "company": {
            "name": config.company_name,
            "address": config.company_address,
            "signatory": config.authorized_signatory,
            "logo_url": config.logo_url,
        },
    }


def get_slip_history(
    db: Session,
    search: Optional[str] = None,
    slip_month: Optional[int] = None,
    slip_year: Optional[int] = None,
    slip_status: Optional[str] = None,
    employee_id: Optional[int] = None,
) -> SlipHistoryResponse:

    q = select(SalarySlip)

    if employee_id:
        q = q.where(SalarySlip.employee_id == employee_id)
    if slip_month:
        q = q.where(SalarySlip.slip_month == slip_month)
    if slip_year:
        q = q.where(SalarySlip.slip_year == slip_year)
    if slip_status:
        q = q.where(SalarySlip.status == slip_status)
    if search:
        like = f"%{search}%"
        q = q.where(
            SalarySlip.employee_name.ilike(like)
            | SalarySlip.employee_code.ilike(like)
            | SalarySlip.slip_code.ilike(like)
        )

    q = q.order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())
    slips = db.execute(q).scalars().all()

    rows = [
        SlipHistoryRow(
            id=s.id,
            slip_code=s.slip_code,
            employee_id=s.employee_id,
            employee_code=s.employee_code,
            employee_name=s.employee_name,
            department=s.department,
            designation=s.designation,
            pay_period=f"{month_name[s.slip_month]} {s.slip_year}",
            net_pay=s.net_pay,
            gross_salary=s.gross_salary,
            status=s.status,
            date_generated=s.generated_at,
            distributed_at=s.distributed_at,
        )
        for s in slips
    ]

    total_payout = sum(r.net_pay for r in rows) or Decimal("0")

    return SlipHistoryResponse(
        total=len(rows),
        slips=rows,
        total_payout=Decimal(str(total_payout)),
    )


def bulk_download(db: Session, slip_ids: Optional[List[int]] = None) -> List[SalarySlip]:
   
    q = select(SalarySlip)
    if slip_ids:
        q = q.where(SalarySlip.id.in_(slip_ids))
    return db.execute(q).scalars().all()


def delete_slips_bulk(db: Session, slip_ids: List[int]) -> int:

    slips = db.execute(
        select(SalarySlip).where(SalarySlip.id.in_(slip_ids))
    ).scalars().all()
    for s in slips:
        db.delete(s)
    db.commit()
    return len(slips)


def export_slips(db: Session, req: ExportRequest) -> dict:

    q = select(SalarySlip)
    if req.slip_ids:
        q = q.where(SalarySlip.id.in_(req.slip_ids))
    elif req.pay_period_month and req.pay_period_year:
        q = q.where(
            SalarySlip.slip_month == req.pay_period_month,
            SalarySlip.slip_year == req.pay_period_year,
        )
    slips = db.execute(q).scalars().all()

    rows = []
    for s in slips:
        rows.append({
            "Slip ID": s.slip_code or str(s.id),
            "Employee Code": s.employee_code,
            "Employee Name": s.employee_name,
            "Department": s.department,
            "Pay Period": f"{month_name[s.slip_month]} {s.slip_year}",
            "Gross Salary": float(s.gross_salary),
            "Total Deductions": float(s.total_deductions),
            "Net Pay": float(s.net_pay),
            "Status": s.status.value,
            "Date Generated": str(s.generated_at.date()) if s.generated_at else "",
        })

    return {
        "format": req.format,
        "total_records": len(rows),
        "rows": rows,
        "exported_at": datetime.utcnow().isoformat(),
    }


def distribute_slip(db: Session, req: DistributeSlipRequest) -> SalarySlipDistribution:
   
    slip = _get_slip(db, req.slip_id)

    if not req.recipient_email:
        emp = db.get(Employee, slip.employee_id)
        if emp:
            req.recipient_email = emp.official_email or emp.personal_email

    dist = SalarySlipDistribution(
        slip_id=req.slip_id,
        method=req.method,
        recipient_email=req.recipient_email,
        recipient_phone=req.recipient_phone,
        status=DistributionStatus.SENT,
        sent_at=datetime.utcnow(),
    )
    db.add(dist)


    slip.status        = SlipStatus.DISTRIBUTED
    slip.distributed_at = datetime.utcnow()
    slip.is_published   = True

    db.commit()
    db.refresh(dist)
    return dist


def bulk_distribute(db: Session, req: BulkDistributeRequest) -> dict:

    slips = db.execute(
        select(SalarySlip).where(
            SalarySlip.slip_month == req.pay_period_month,
            SalarySlip.slip_year == req.pay_period_year,
            SalarySlip.status == SlipStatus.GENERATED,
        )
    ).scalars().all()

    sent = 0
    failed = 0
    for slip in slips:
        try:
            distribute_slip(db, DistributeSlipRequest(
                slip_id=slip.id,
                method=req.method,
            ))
            sent += 1
        except Exception:
            failed += 1

    return {
        "sent": sent,
        "failed": failed,
        "total": len(slips),
        "pay_period": f"{month_name[req.pay_period_month]} {req.pay_period_year}",
    }


def get_distribution_settings(db: Session) -> DistributionSettings:
    return _get_or_create_distribution_settings(db)


def update_distribution_settings(
    db: Session, payload: DistributionSettingsUpdate
) -> DistributionSettings:
    obj = _get_or_create_distribution_settings(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def reset_distribution_settings(db: Session) -> DistributionSettings:
    """Reset to Default button."""
    obj = _get_or_create_distribution_settings(db)
    obj.send_automatic_email   = True
    obj.cc_hr_department       = True
    obj.bcc_accounts_department = False
    obj.email_subject          = "Your Salary Slip for [Month Year]"
    obj.email_template         = (
        "Dear [Employee Name],\n\n"
        "Your salary slip for [Month Year] has been generated.\n\n"
        "Net Salary: [Net Amount]\nPayment Date: [Payment Date]\n\n"
        "You can download your salary slip from the employee portal "
        "or it is attached to this email."
    )
    obj.send_sms_notification        = True
    obj.enable_employee_portal_access = True
    obj.auto_send_time               = "09:00"
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def reset_email_template(db: Session) -> DistributionSettings:

    obj = _get_or_create_distribution_settings(db)
    obj.email_template = (
        "Dear [Employee Name],\n\n"
        "Your salary slip for [Month Year] has been generated.\n\n"
        "Net Salary: [Net Amount]\nPayment Date: [Payment Date]\n\n"
        "You can download your salary slip from the employee portal "
        "or it is attached to this email."
    )
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def get_slip_config(db: Session) -> SalarySlipConfig:
    return _get_or_create_config(db)


def create_slip_config(db: Session, payload: SalarySlipConfigCreate) -> SalarySlipConfig:
    existing = db.execute(
        select(SalarySlipConfig).where(SalarySlipConfig.config_name == payload.config_name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Config already exists. Use PUT.")
    obj = SalarySlipConfig(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_slip_config(db: Session, payload: SalarySlipConfigUpdate) -> SalarySlipConfig:

    obj = _get_or_create_config(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def reset_slip_config(db: Session) -> SalarySlipConfig:

    obj = _get_or_create_config(db)
    obj.footer_text          = "Generated by HRMS Salary Slip System v2.0"
    obj.confidentiality_text = (
        "This document is confidential and intended only for the employee. "
        "Unauthorized distribution is prohibited."
    )
    obj.retention_period_months    = 12
    obj.allow_salary_slip_revisions = True
    obj.revision_allowed_days      = 7
    obj.auto_send_on_generation    = True
    obj.auto_send_time             = "09:00"
    obj.password_strength          = "employee_id"
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def create_salary_slip(db: Session, payload: SalarySlipCreate) -> SalarySlip:
    obj = SalarySlip(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_salary_slips(
    db: Session,
    employee_id: Optional[int] = None,
    slip_month: Optional[int] = None,
    slip_year: Optional[int] = None,
) -> List[SalarySlip]:
    stmt = select(SalarySlip)
    if employee_id:
        stmt = stmt.where(SalarySlip.employee_id == employee_id)
    if slip_month:
        stmt = stmt.where(SalarySlip.slip_month == slip_month)
    if slip_year:
        stmt = stmt.where(SalarySlip.slip_year == slip_year)
    return db.execute(stmt).scalars().all()


def get_salary_slip(db: Session, slip_id: int) -> SalarySlip:
    return _get_slip(db, slip_id)


def get_slips_by_employee(db: Session, employee_id: int) -> List[SalarySlip]:
    return db.execute(
        select(SalarySlip)
        .where(SalarySlip.employee_id == employee_id)
        .order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())
    ).scalars().all()


def publish_salary_slip(db: Session, slip_id: int) -> SalarySlip:
    obj = _get_slip(db, slip_id)
    obj.is_published = True
    obj.status = SlipStatus.DISTRIBUTED
    obj.distributed_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def update_salary_slip(db: Session, slip_id: int, payload: SalarySlipUpdate) -> SalarySlip:
    obj = _get_slip(db, slip_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_salary_slip(db: Session, slip_id: int) -> None:
    obj = _get_slip(db, slip_id)
    db.delete(obj)
    db.commit()


def _get_slip(db: Session, slip_id: int) -> SalarySlip:
    obj = db.get(SalarySlip, slip_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Salary slip not found")
    return obj


def _get_employee(db: Session, employee_id: int) -> Employee:
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    return emp


def _get_existing_slip(
    db: Session, employee_id: int, month: int, year: int
) -> Optional[SalarySlip]:
    return db.execute(
        select(SalarySlip).where(
            SalarySlip.employee_id == employee_id,
            SalarySlip.slip_month == month,
            SalarySlip.slip_year == year,
        )
    ).scalar_one_or_none()


def _get_or_create_config(db: Session) -> SalarySlipConfig:
    obj = db.execute(
        select(SalarySlipConfig).where(SalarySlipConfig.config_name == "default")
    ).scalar_one_or_none()
    if not obj:
        obj = SalarySlipConfig(config_name="default")
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj


def _get_or_create_distribution_settings(db: Session) -> DistributionSettings:
    obj = db.execute(
        select(DistributionSettings).where(DistributionSettings.config_name == "default")
    ).scalar_one_or_none()
    if not obj:
        obj = DistributionSettings(config_name="default")
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj


def _generate_slip_code(year: int, month: int) -> str:

    import random
    seq = random.randint(1, 999)
    return f"SS{year}{month:02d}{seq:03d}"


def _build_earnings_json(detail: PayrollRunDetail) -> str:
    earnings = {
        "Basic Salary": float(detail.basic),
        "HRA": float(detail.hra),
        "Special Allowance": float(detail.special_allowance),
    }
    return json.dumps(earnings)


def _build_deductions_json(detail: PayrollRunDetail) -> str:
    deductions = {
        "PF (Employee)": float(detail.pf_employee),
        "ESI (Employee)": float(detail.esi_employee),
        "Professional Tax": float(detail.professional_tax),
        "TDS": float(detail.tds),
    }
    return json.dumps(deductions)


def _populate_slip_from_detail(
    slip: SalarySlip,
    detail: PayrollRunDetail,
    method: DistributionMethod,
    protect: bool,
) -> None:
    slip.gross_salary      = detail.gross_salary
    slip.total_deductions  = detail.total_deductions
    slip.net_pay           = detail.net_pay
    slip.earnings_json     = _build_earnings_json(detail)
    slip.deductions_json   = _build_deductions_json(detail)
    slip.distribution_method = method
    slip.is_password_protected = protect
    slip.status            = SlipStatus.GENERATED


def _create_distribution_record(
    db: Session, slip: SalarySlip, dist_settings: DistributionSettings
) -> None:
   
    emp = db.get(Employee, slip.employee_id)
    dist = SalarySlipDistribution(
        slip_id=slip.id,
        method=DistributionMethod.EMAIL,
        recipient_email=emp.official_email or emp.personal_email if emp else None,
        status=DistributionStatus.PENDING,
    )
    db.add(dist)
    db.flush()