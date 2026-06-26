from sqlalchemy.orm import Session
from typing import Optional, List

from model.Payroll.payroll_processing import PayrollConfig, SalaryComponentConfig
from schema.Payroll.payroll_processing import (
    PayrollConfigUpdate,
    SalaryComponentCreate,
    SalaryComponentUpdate,
)


# ══════════════════════════════════════════════════════════════════════════════
# Payroll Config (single-row — get or create on first access)
# ══════════════════════════════════════════════════════════════════════════════

def _get_or_create_config(db: Session) -> PayrollConfig:
    config = db.query(PayrollConfig).first()
    if not config:
        config = PayrollConfig()   # all defaults from model
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def get_config(db: Session) -> PayrollConfig:
    return _get_or_create_config(db)


def update_config(db: Session, payload: PayrollConfigUpdate) -> PayrollConfig:
    config = _get_or_create_config(db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config


def lock_payroll(db: Session, reason: Optional[str] = None) -> tuple:
    config = _get_or_create_config(db)
    if config.payroll_status == "LOCKED":
        return None, "Payroll is already locked."
    config.payroll_status = "LOCKED"
    db.commit()
    db.refresh(config)
    return config, None


def unlock_payroll(db: Session) -> tuple:
    config = _get_or_create_config(db)
    if config.payroll_status == "ACTIVE":
        return None, "Payroll is already active."
    config.payroll_status = "ACTIVE"
    db.commit()
    db.refresh(config)
    return config, None


def export_config(db: Session) -> dict:
    config = _get_or_create_config(db)
    components = get_all_components(db, is_active=None)
    return {
        "config": config,
        "salary_components": components,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Salary Components config
# ══════════════════════════════════════════════════════════════════════════════

def get_all_components(
    db: Session,
    component_type: Optional[str] = None,
    is_active: Optional[bool]     = True,
) -> List[SalaryComponentConfig]:
    q = db.query(SalaryComponentConfig)
    if component_type:
        q = q.filter(SalaryComponentConfig.component_type == component_type.lower())
    if is_active is not None:
        q = q.filter(SalaryComponentConfig.is_active == is_active)
    return q.order_by(
        SalaryComponentConfig.component_type.asc(),
        SalaryComponentConfig.display_order.asc(),
        SalaryComponentConfig.id.asc(),
    ).all()


def get_component_by_id(db: Session, component_id: int) -> Optional[SalaryComponentConfig]:
    return (
        db.query(SalaryComponentConfig)
        .filter(SalaryComponentConfig.id == component_id)
        .first()
    )


def create_component(db: Session, payload: SalaryComponentCreate) -> SalaryComponentConfig:
    component = SalaryComponentConfig(**payload.model_dump())
    db.add(component)
    db.commit()
    db.refresh(component)
    return component


def update_component(
    db: Session,
    component_id: int,
    payload: SalaryComponentUpdate,
) -> Optional[SalaryComponentConfig]:
    component = get_component_by_id(db, component_id)
    if not component:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(component, key, value)
    db.commit()
    db.refresh(component)
    return component


def delete_component(db: Session, component_id: int) -> bool:
    component = get_component_by_id(db, component_id)
    if not component:
        return False
    db.delete(component)
    db.commit()
    return True


def seed_default_components(db: Session) -> List[SalaryComponentConfig]:
    """
    Seed the default salary components visible in the UI.
    Call this once during initial setup / migration.
    """
    existing = db.query(SalaryComponentConfig).count()
    if existing > 0:
        return get_all_components(db, is_active=None)

    defaults = [
        # ── Earnings ──────────────────────────────────────────────────────────
        dict(
            component_name="Basic Salary",
            component_type="earnings",
            calculation_type="percentage",
            value=50.0,
            is_taxable=True,
            display_order=1,
        ),
        dict(
            component_name="House Rent Allowance",
            component_type="earnings",
            calculation_type="percentage",
            value=40.0,
            is_taxable=True,
            display_order=2,
        ),
        dict(
            component_name="Conveyance Allowance",
            component_type="earnings",
            calculation_type="fixed",
            value=1600.0,
            is_taxable=False,
            display_order=3,
        ),
        dict(
            component_name="Medical Allowance",
            component_type="earnings",
            calculation_type="fixed",
            value=1250.0,
            is_taxable=False,
            display_order=4,
        ),
        # ── Deductions ────────────────────────────────────────────────────────
        dict(
            component_name="Provident Fund",
            component_type="deductions",
            calculation_type="percentage",
            value=12.0,
            is_taxable=False,
            display_order=1,
        ),
        dict(
            component_name="Professional Tax",
            component_type="deductions",
            calculation_type="fixed",
            value=200.0,
            is_taxable=False,
            display_order=2,
        ),
    ]

    components = []
    for d in defaults:
        c = SalaryComponentConfig(**d)
        db.add(c)
        components.append(c)

    db.commit()
    for c in components:
        db.refresh(c)
    return components