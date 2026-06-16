

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime, date
from decimal import Decimal

from model.Payroll.statutory_compliance import (
    StatutoryConfig, PFEligibilityRule,
    PFStatement, PFRemittanceSummary,
    ECRRecord, VPFRecord, UANRecord,
    PFStatementStatus, RemittanceStatus, ECRStatus,
)
from model.Payroll.payroll_run import PayrollRunDetail
from model.onboarding.employee import Employee   # adjust import path if needed

from schema.Payroll.statutory_compliance import (
    StatutoryConfigCreate, StatutoryConfigUpdate,
    PFEligibilityRuleCreate, PFEligibilityRuleUpdate,
    PFStatementCreate, PFStatementUpdate,
    PFRemittanceSummaryCreate, PFRemittanceSummaryUpdate,
    ECRRecordCreate, ECRRecordUpdate,
    VPFRecordCreate, VPFRecordUpdate,
    UANRecordCreate, UANRecordUpdate,
    StatutoryDashboard, StatutoryCompliancePageResponse,
)


def get_statutory_dashboard(db: Session, month: int, year: int) -> StatutoryDashboard:

    total_pf = db.execute(
        select(func.coalesce(func.sum(PFStatement.total_pf), 0))
        .where(PFStatement.month == month, PFStatement.year == year)
    ).scalar_one()

    esi_sum = db.execute(
        select(func.coalesce(func.sum(PayrollRunDetail.esi_employee), 0))
        .where(
            PayrollRunDetail.payroll_run_id.in_(
                select(func.distinct(PayrollRunDetail.payroll_run_id))
            )
        )
    ).scalar_one()

    tds_sum = db.execute(
        select(func.coalesce(func.sum(PayrollRunDetail.tds), 0))
    ).scalar_one()

    total_employees = db.execute(
        select(func.count()).select_from(Employee).where(Employee.is_active == True)
    ).scalar_one()

    active_uan_count = db.execute(
        select(func.count()).select_from(UANRecord).where(UANRecord.status == "active")
    ).scalar_one()

    pending_declarations = max(0, total_employees - active_uan_count)

    return StatutoryDashboard(
        total_pf_contribution=Decimal(str(total_pf)),
        total_esi_contribution=Decimal(str(esi_sum)),
        total_tds_deduction=Decimal(str(tds_sum)),
        pending_declarations=pending_declarations,
        current_month=month,
        current_year=year,
    )



def get_compliance_page(db: Session, month: int, year: int) -> StatutoryCompliancePageResponse:
    """Single call that populates every section of the Statutory Compliance Engine page."""
    config = _get_or_create_config(db)
    rule   = db.execute(
        select(PFEligibilityRule).where(PFEligibilityRule.config_id == config.id)
    ).scalar_one_or_none()

    pf_stmts   = _enrich_pf_statements(db, month, year)
    vpf_recs   = _enrich_vpf_records(db, month, year)
    uan_recs   = _enrich_uan_records(db)

    remittance = db.execute(
        select(PFRemittanceSummary)
        .where(PFRemittanceSummary.month == month, PFRemittanceSummary.year == year)
        .order_by(PFRemittanceSummary.year.desc(), PFRemittanceSummary.month.desc())
    ).scalars().all()

    ecr = db.execute(
        select(ECRRecord)
        .where(ECRRecord.month == month, ECRRecord.year == year)
        .order_by(ECRRecord.year.desc(), ECRRecord.month.desc())
    ).scalars().all()

    return StatutoryCompliancePageResponse(
        dashboard=get_statutory_dashboard(db, month, year),
        config=config,
        eligibility_rule=rule,
        pf_statements=pf_stmts,
        remittance_summary=remittance,
        ecr_records=ecr,
        vpf_records=vpf_recs,
        uan_records=uan_recs,
    )


def get_statutory_config(db: Session) -> StatutoryConfig:
    return _get_or_create_config(db)


def create_statutory_config(db: Session, payload: StatutoryConfigCreate) -> StatutoryConfig:
    existing = db.execute(
        select(StatutoryConfig).where(
            StatutoryConfig.config_name == (payload.config_name or "default")
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Statutory config '{payload.config_name}' already exists. Use PUT to update.",
        )
    obj = StatutoryConfig(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_statutory_config(
    db: Session, config_id: int, payload: StatutoryConfigUpdate
) -> StatutoryConfig:
    obj = db.get(StatutoryConfig, config_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Statutory config not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def get_eligibility_rule(db: Session, config_id: int) -> Optional[PFEligibilityRule]:
    return db.execute(
        select(PFEligibilityRule).where(PFEligibilityRule.config_id == config_id)
    ).scalar_one_or_none()


def upsert_eligibility_rule(
    db: Session, payload: PFEligibilityRuleCreate
) -> PFEligibilityRule:
    existing = get_eligibility_rule(db, payload.config_id)
    if existing:
        for k, v in payload.model_dump(exclude={"config_id"}).items():
            setattr(existing, k, v)
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    obj = PFEligibilityRule(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_eligibility_rule(
    db: Session, rule_id: int, payload: PFEligibilityRuleUpdate
) -> PFEligibilityRule:
    obj = db.get(PFEligibilityRule, rule_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Eligibility rule not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def list_pf_statements(db: Session, month: int, year: int) -> List[PFStatement]:
    return db.execute(
        select(PFStatement)
        .where(PFStatement.month == month, PFStatement.year == year)
        .order_by(PFStatement.employee_id)
    ).scalars().all()


def create_pf_statement(db: Session, payload: PFStatementCreate) -> PFStatement:
    existing = db.execute(
        select(PFStatement).where(
            PFStatement.employee_id == payload.employee_id,
            PFStatement.month == payload.month,
            PFStatement.year == payload.year,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="PF statement for this employee/month/year already exists",
        )
    obj = PFStatement(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_pf_statement(
    db: Session, statement_id: int, payload: PFStatementUpdate
) -> PFStatement:
    obj = db.get(PFStatement, statement_id)
    if not obj:
        raise HTTPException(status_code=404, detail="PF statement not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def generate_pf_statements_from_payroll(
    db: Session, month: int, year: int
) -> List[PFStatement]:

    config = _get_or_create_config(db)
    details = db.execute(select(PayrollRunDetail)).scalars().all()

    created = []
    for d in details:
        existing = db.execute(
            select(PFStatement).where(
                PFStatement.employee_id == d.employee_id,
                PFStatement.month == month,
                PFStatement.year == year,
            )
        ).scalar_one_or_none()

        emp_contrib = Decimal(str(float(d.pf_employee)))
     
        basic = float(d.basic)
        ceiling = float(config.pf_ceiling_limit)
        calc_base = min(basic, ceiling) if config.pf_calc_on_ceiling else basic
        empr_contrib = Decimal(str(round(calc_base * config.pf_employer_rate / 100, 2)))
        eps_contrib  = Decimal(str(round(calc_base * config.eps_contribution_rate / 100, 2)))
        edli_contrib = Decimal(str(round(calc_base * config.edli_contribution_rate / 100, 2)))
        total_pf     = emp_contrib + empr_contrib


        uan_row = db.execute(
            select(UANRecord).where(UANRecord.employee_id == d.employee_id)
        ).scalar_one_or_none()

        if existing:
            existing.employee_contribution = emp_contrib
            existing.employer_contribution = empr_contrib
            existing.eps_contribution      = eps_contrib
            existing.edli_contribution     = edli_contrib
            existing.total_pf              = total_pf
            existing.uan_number            = uan_row.uan_number if uan_row else None
            existing.status                = PFStatementStatus.PENDING
            existing.updated_at            = datetime.utcnow()
            created.append(existing)
        else:
            stmt = PFStatement(
                employee_id=d.employee_id,
                month=month,
                year=year,
                uan_number=uan_row.uan_number if uan_row else None,
                employee_contribution=emp_contrib,
                employer_contribution=empr_contrib,
                eps_contribution=eps_contrib,
                edli_contribution=edli_contrib,
                total_pf=total_pf,
                status=PFStatementStatus.PENDING,
            )
            db.add(stmt)
            created.append(stmt)

    db.commit()
    return created


def list_remittance_summary(db: Session, year: Optional[int] = None) -> List[PFRemittanceSummary]:
    q = select(PFRemittanceSummary).order_by(
        PFRemittanceSummary.year.desc(), PFRemittanceSummary.month.desc()
    )
    if year:
        q = q.where(PFRemittanceSummary.year == year)
    return db.execute(q).scalars().all()


def create_remittance_summary(
    db: Session, payload: PFRemittanceSummaryCreate
) -> PFRemittanceSummary:
    existing = db.execute(
        select(PFRemittanceSummary).where(
            PFRemittanceSummary.month == payload.month,
            PFRemittanceSummary.year == payload.year,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409, detail="Remittance summary for this month/year already exists"
        )
    obj = PFRemittanceSummary(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_remittance_summary(
    db: Session, summary_id: int, payload: PFRemittanceSummaryUpdate
) -> PFRemittanceSummary:
    obj = db.get(PFRemittanceSummary, summary_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Remittance summary not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def generate_remittance_from_statements(
    db: Session, month: int, year: int
) -> PFRemittanceSummary:

    stmts = db.execute(
        select(PFStatement)
        .where(PFStatement.month == month, PFStatement.year == year)
    ).scalars().all()

    if not stmts:
        raise HTTPException(
            status_code=404,
            detail=f"No PF statements found for {month}/{year}. Generate statements first.",
        )

    emp_total  = sum(s.employee_contribution for s in stmts)
    empr_total = sum(s.employer_contribution for s in stmts)
    eps_total  = sum(s.eps_contribution for s in stmts)
    edli_total = sum(s.edli_contribution for s in stmts)
    grand_total = emp_total + empr_total

    existing = db.execute(
        select(PFRemittanceSummary).where(
            PFRemittanceSummary.month == month, PFRemittanceSummary.year == year
        )
    ).scalar_one_or_none()

    if existing:
        existing.total_contribution    = grand_total
        existing.employee_contribution = emp_total
        existing.employer_contribution = empr_total
        existing.eps_contribution      = eps_total
        existing.edli_contribution     = edli_total
        existing.updated_at            = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    obj = PFRemittanceSummary(
        month=month, year=year,
        total_contribution=grand_total,
        employee_contribution=emp_total,
        employer_contribution=empr_total,
        eps_contribution=eps_total,
        edli_contribution=edli_total,
        status=RemittanceStatus.PENDING,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def list_ecr_records(db: Session, year: Optional[int] = None) -> List[ECRRecord]:
    q = select(ECRRecord).order_by(ECRRecord.year.desc(), ECRRecord.month.desc())
    if year:
        q = q.where(ECRRecord.year == year)
    return db.execute(q).scalars().all()


def create_ecr_record(db: Session, payload: ECRRecordCreate) -> ECRRecord:
    existing = db.execute(
        select(ECRRecord).where(
            ECRRecord.month == payload.month, ECRRecord.year == payload.year
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409, detail="ECR record for this month/year already exists"
        )
    obj = ECRRecord(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_ecr_record(
    db: Session, ecr_id: int, payload: ECRRecordUpdate
) -> ECRRecord:
    obj = db.get(ECRRecord, ecr_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ECR record not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def generate_ecr_from_statements(db: Session, month: int, year: int) -> ECRRecord:

    stmts = db.execute(
        select(PFStatement)
        .where(PFStatement.month == month, PFStatement.year == year)
    ).scalars().all()

    if not stmts:
        raise HTTPException(
            status_code=404,
            detail=f"No PF statements for {month}/{year}. Generate statements first.",
        )

    config    = _get_or_create_config(db)
    total_wages  = db.execute(
        select(func.coalesce(func.sum(PayrollRunDetail.gross_salary), 0))
    ).scalar_one()
    epf_contrib  = sum(s.employee_contribution + s.employer_contribution for s in stmts)
    eps_contrib  = sum(s.eps_contribution for s in stmts)
    edli_contrib = sum(s.edli_contribution for s in stmts)
    admin        = Decimal(str(round(float(epf_contrib) * 0.005, 2)))  # 0.5% admin charges
    total_due    = epf_contrib + edli_contrib + admin

    existing = db.execute(
        select(ECRRecord).where(ECRRecord.month == month, ECRRecord.year == year)
    ).scalar_one_or_none()

    if existing:
        existing.total_employees   = len(stmts)
        existing.total_wages       = Decimal(str(total_wages))
        existing.epf_contribution  = epf_contrib
        existing.eps_contribution  = eps_contrib
        existing.edli_contribution = edli_contrib
        existing.admin_charges     = admin
        existing.total_amount_due  = total_due
        existing.updated_at        = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    obj = ECRRecord(
        month=month, year=year,
        total_employees=len(stmts),
        total_wages=Decimal(str(total_wages)),
        epf_contribution=epf_contrib,
        eps_contribution=eps_contrib,
        edli_contribution=edli_contrib,
        admin_charges=admin,
        total_amount_due=total_due,
        status=ECRStatus.PENDING,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def submit_ecr(db: Session, ecr_id: int, ack_number: Optional[str] = None) -> ECRRecord:
    obj = db.get(ECRRecord, ecr_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ECR record not found")
    obj.status         = ECRStatus.SUBMITTED
    obj.submitted_date = date.today()
    if ack_number:
        obj.ack_number = ack_number
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def list_vpf_records(db: Session, month: int, year: int) -> List[VPFRecord]:
    return db.execute(
        select(VPFRecord).where(VPFRecord.month == month, VPFRecord.year == year)
    ).scalars().all()


def create_vpf_record(db: Session, payload: VPFRecordCreate) -> VPFRecord:
    existing = db.execute(
        select(VPFRecord).where(
            VPFRecord.employee_id == payload.employee_id,
            VPFRecord.month == payload.month,
            VPFRecord.year == payload.year,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="VPF record already exists for this period")
    obj = VPFRecord(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_vpf_record(
    db: Session, vpf_id: int, payload: VPFRecordUpdate
) -> VPFRecord:
    obj = db.get(VPFRecord, vpf_id)
    if not obj:
        raise HTTPException(status_code=404, detail="VPF record not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def list_uan_records(db: Session) -> List[UANRecord]:
    return db.execute(select(UANRecord).order_by(UANRecord.employee_id)).scalars().all()


def create_uan_record(db: Session, payload: UANRecordCreate) -> UANRecord:
    existing = db.execute(
        select(UANRecord).where(UANRecord.employee_id == payload.employee_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="UAN record already exists for this employee. Use PUT to update.",
        )
    if payload.uan_number:
        dup_uan = db.execute(
            select(UANRecord).where(UANRecord.uan_number == payload.uan_number)
        ).scalar_one_or_none()
        if dup_uan:
            raise HTTPException(status_code=409, detail="UAN number already assigned to another employee")

    obj = UANRecord(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_uan_record(
    db: Session, uan_id: int, payload: UANRecordUpdate
) -> UANRecord:
    obj = db.get(UANRecord, uan_id)
    if not obj:
        raise HTTPException(status_code=404, detail="UAN record not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def activate_uan(db: Session, uan_id: int) -> UANRecord:

    obj = db.get(UANRecord, uan_id)
    if not obj:
        raise HTTPException(status_code=404, detail="UAN record not found")
    if not obj.uan_number:
        raise HTTPException(
            status_code=400, detail="Cannot activate: UAN number is not set"
        )
    obj.status          = "active"
    obj.activation_date = date.today()
    obj.updated_at      = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def _get_or_create_config(db: Session) -> StatutoryConfig:
    obj = db.execute(
        select(StatutoryConfig).where(StatutoryConfig.config_name == "default")
    ).scalar_one_or_none()
    if not obj:
        obj = StatutoryConfig(config_name="default")
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj


def _enrich_pf_statements(db: Session, month: int, year: int):

    rows = list_pf_statements(db, month, year)
    emp_ids = [r.employee_id for r in rows]
    employees = {
        e.id: f"{e.first_name} {e.last_name or ''}".strip()
        for e in db.execute(
            select(Employee).where(Employee.id.in_(emp_ids))
        ).scalars().all()
    } if emp_ids else {}

    from schema.Payroll.statutory_compliance import PFStatementResponse
    result = []
    for r in rows:
        d = PFStatementResponse.model_validate(r)
        d.employee_name = employees.get(r.employee_id)
        result.append(d)
    return result


def _enrich_vpf_records(db: Session, month: int, year: int):
    rows = list_vpf_records(db, month, year)
    emp_ids = [r.employee_id for r in rows]
    employees = {
        e.id: f"{e.first_name} {e.last_name or ''}".strip()
        for e in db.execute(
            select(Employee).where(Employee.id.in_(emp_ids))
        ).scalars().all()
    } if emp_ids else {}

    from schema.Payroll.statutory_compliance import VPFRecordResponse
    result = []
    for r in rows:
        d = VPFRecordResponse.model_validate(r)
        d.employee_name = employees.get(r.employee_id)
        result.append(d)
    return result


def _enrich_uan_records(db: Session):
    rows = list_uan_records(db)
    emp_ids = [r.employee_id for r in rows]
    employees = {
        e.id: f"{e.first_name} {e.last_name or ''}".strip()
        for e in db.execute(
            select(Employee).where(Employee.id.in_(emp_ids))
        ).scalars().all()
    } if emp_ids else {}

    from schema.Payroll.statutory_compliance import UANRecordResponse
    result = []
    for r in rows:
        d = UANRecordResponse.model_validate(r)
        d.employee_name = employees.get(r.employee_id)
        result.append(d)
    return result