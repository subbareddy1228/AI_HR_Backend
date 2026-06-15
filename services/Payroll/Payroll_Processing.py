"""
Payroll Processing Module — Service Layer
All business logic is isolated here; routers stay thin.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from model.Payroll.Payroll_Processing import (
    CommissionConfig,
    LockAction,
    PayrollComponent,
    PayrollConfig,
    PayrollLockLog,
    PayrollStatus,
    StatutorySettings,
)
from schema.Payroll.Payrol_Processing import (
    CommissionConfigCreate,
    CommissionConfigUpdate,
    PayrollComponentCreate,
    PayrollComponentUpdate,
    PayrollConfigCreate,
    PayrollConfigUpdate,
    LockPayrollRequest,
    StatutorySettingsCreate,
    StatutorySettingsUpdate,
    ComponentsTableResponse,
    PayrollProcessingPageResponse,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_or_404(db: Session, model, record_id: int):
    obj = db.get(model, record_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} with id={record_id} not found.",
        )
    return obj


def _get_singleton(db: Session, model):
    """Return the first (and only) config row, or None."""
    return db.execute(select(model)).scalars().first()


def _require_unlocked(config: Optional[PayrollConfig]) -> None:
    """Raise 423 Locked if payroll is currently locked."""
    if config and config.payroll_status == PayrollStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=(
                "Payroll is currently LOCKED. Unlock it first before making changes. "
                f"Locked reason: {config.lock_reason or 'N/A'}"
            ),
        )


# ===========================================================================
# Payroll Config Service
# ===========================================================================

class PayrollConfigService:

    @staticmethod
    def get(db: Session) -> Optional[PayrollConfig]:
        return _get_singleton(db, PayrollConfig)

    @staticmethod
    def upsert(db: Session, payload: PayrollConfigCreate) -> PayrollConfig:
        config = _get_singleton(db, PayrollConfig)
        data = payload.model_dump(exclude_unset=True)

        if config is None:
            config = PayrollConfig(**data)
            db.add(config)
        else:
            for key, val in data.items():
                setattr(config, key, val)
            config.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def update(db: Session, payload: PayrollConfigUpdate) -> PayrollConfig:
        config = _get_singleton(db, PayrollConfig)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll configuration has not been set up yet.",
            )
        _require_unlocked(config)
        for key, val in payload.model_dump(exclude_unset=True).items():
            setattr(config, key, val)
        config.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(config)
        return config

    # ---- Lock / Unlock ----

    @staticmethod
    def lock(db: Session, payload: LockPayrollRequest) -> PayrollConfig:
        config = _get_singleton(db, PayrollConfig)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll configuration has not been set up yet.",
            )
        if config.payroll_status == PayrollStatus.LOCKED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payroll is already locked.",
            )

        prev_status = config.payroll_status.value
        config.payroll_status = PayrollStatus.LOCKED
        config.locked_by      = payload.actioned_by
        config.locked_at      = datetime.utcnow()
        config.lock_reason    = payload.reason
        config.updated_at     = datetime.utcnow()

        # Audit
        log = PayrollLockLog(
            action          = LockAction.LOCK,
            reason          = payload.reason,
            actioned_by     = payload.actioned_by,
            previous_status = prev_status,
            new_status      = PayrollStatus.LOCKED.value,
        )
        db.add(log)
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def unlock(db: Session, payload: LockPayrollRequest) -> PayrollConfig:
        config = _get_singleton(db, PayrollConfig)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll configuration has not been set up yet.",
            )
        if config.payroll_status == PayrollStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payroll is already active (not locked).",
            )

        prev_status = config.payroll_status.value
        config.payroll_status = PayrollStatus.ACTIVE
        config.locked_by      = None
        config.locked_at      = None
        config.lock_reason    = None
        config.updated_at     = datetime.utcnow()

        log = PayrollLockLog(
            action          = LockAction.UNLOCK,
            reason          = payload.reason,
            actioned_by     = payload.actioned_by,
            previous_status = prev_status,
            new_status      = PayrollStatus.ACTIVE.value,
        )
        db.add(log)
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def get_lock_logs(db: Session, limit: int = 50) -> list[PayrollLockLog]:
        return (
            db.execute(
                select(PayrollLockLog)
                .order_by(PayrollLockLog.actioned_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )


# ===========================================================================
# Commission Config Service
# ===========================================================================

class CommissionConfigService:

    @staticmethod
    def get(db: Session) -> Optional[CommissionConfig]:
        return _get_singleton(db, CommissionConfig)

    @staticmethod
    def upsert(db: Session, payload: CommissionConfigCreate) -> CommissionConfig:
        obj = _get_singleton(db, CommissionConfig)
        data = payload.model_dump(exclude_unset=True)

        if obj is None:
            obj = CommissionConfig(**data)
            db.add(obj)
        else:
            for key, val in data.items():
                setattr(obj, key, val)
            obj.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(db: Session, payload: CommissionConfigUpdate) -> CommissionConfig:
        obj = _get_singleton(db, CommissionConfig)
        if obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commission configuration has not been set up yet.",
            )
        for key, val in payload.model_dump(exclude_unset=True).items():
            setattr(obj, key, val)
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj


# ===========================================================================
# Statutory Settings Service
# ===========================================================================

class StatutorySettingsService:

    @staticmethod
    def get(db: Session) -> Optional[StatutorySettings]:
        return _get_singleton(db, StatutorySettings)

    @staticmethod
    def upsert(db: Session, payload: StatutorySettingsCreate) -> StatutorySettings:
        obj = _get_singleton(db, StatutorySettings)
        data = payload.model_dump(exclude_unset=True)

        if obj is None:
            obj = StatutorySettings(**data)
            db.add(obj)
        else:
            for key, val in data.items():
                setattr(obj, key, val)
            obj.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(db: Session, payload: StatutorySettingsUpdate) -> StatutorySettings:
        obj = _get_singleton(db, StatutorySettings)
        if obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Statutory settings have not been configured yet.",
            )
        for key, val in payload.model_dump(exclude_unset=True).items():
            setattr(obj, key, val)
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj


# ===========================================================================
# Payroll Component Service  (Salary Component Configuration table)
# ===========================================================================

class PayrollComponentService:

    @staticmethod
    def list_all(db: Session, active_only: bool = True) -> list[PayrollComponent]:
        stmt = select(PayrollComponent)
        if active_only:
            stmt = stmt.where(PayrollComponent.is_active == True)
        stmt = stmt.order_by(PayrollComponent.component_type, PayrollComponent.display_order)
        return db.execute(stmt).scalars().all()

    @staticmethod
    def list_grouped(db: Session, active_only: bool = True) -> ComponentsTableResponse:
        components = PayrollComponentService.list_all(db, active_only)
        from model.Payroll.Payroll_Processing import ComponentType as CT
        earnings   = [c for c in components if c.component_type == CT.EARNINGS]
        deductions = [c for c in components if c.component_type == CT.DEDUCTIONS]
        return ComponentsTableResponse(
            earnings=earnings,
            deductions=deductions,
            total=len(components),
        )

    @staticmethod
    def get(db: Session, component_id: int) -> PayrollComponent:
        return _get_or_404(db, PayrollComponent, component_id)

    @staticmethod
    def create(db: Session, payload: PayrollComponentCreate) -> PayrollComponent:
        # Check duplicate name (active components)
        existing = db.execute(
            select(PayrollComponent).where(
                PayrollComponent.component_name == payload.component_name,
                PayrollComponent.is_active == True,
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A component named '{payload.component_name}' already exists.",
            )

        obj = PayrollComponent(**payload.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(
        db: Session, component_id: int, payload: PayrollComponentUpdate
    ) -> PayrollComponent:
        obj = _get_or_404(db, PayrollComponent, component_id)

        # Name uniqueness check (skip if name unchanged or not provided)
        if payload.component_name and payload.component_name != obj.component_name:
            duplicate = db.execute(
                select(PayrollComponent).where(
                    PayrollComponent.component_name == payload.component_name,
                    PayrollComponent.is_active == True,
                    PayrollComponent.id != component_id,
                )
            ).scalar_one_or_none()
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A component named '{payload.component_name}' already exists.",
                )

        for key, val in payload.model_dump(exclude_unset=True).items():
            setattr(obj, key, val)
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, component_id: int) -> None:
        obj = _get_or_404(db, PayrollComponent, component_id)
        # Soft delete — keeps history intact
        obj.is_active  = False
        obj.updated_at = datetime.utcnow()
        db.commit()


# ===========================================================================
# Full Page Service  (single query to hydrate entire page)
# ===========================================================================

class PayrollProcessingPageService:

    @staticmethod
    def get_full_page(db: Session) -> PayrollProcessingPageResponse:
        config     = PayrollConfigService.get(db)
        commission = CommissionConfigService.get(db)
        statutory  = StatutorySettingsService.get(db)
        components = PayrollComponentService.list_grouped(db)

        return PayrollProcessingPageResponse(
            config     = config,
            commission = commission,
            statutory  = statutory,
            components = components,
        )