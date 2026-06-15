"""
Payroll Processing Module — Router Layer
All endpoints for the Payroll Processing configuration page.

Mount in main.py:
    from routers.Payroll import payroll_processing
    app.include_router(payroll_processing.router, prefix="/api/payroll", tags=["Payroll"])

Full endpoint map:
─────────────────────────────────────────────────────────────────
  GET    /api/payroll/processing                 → full page data
  ─── Payroll Config ──────────────────────────────────────────
  GET    /api/payroll/processing/config          → get config
  POST   /api/payroll/processing/config          → create/upsert
  PATCH  /api/payroll/processing/config          → update fields
  POST   /api/payroll/processing/config/lock     → lock payroll
  POST   /api/payroll/processing/config/unlock   → unlock payroll
  GET    /api/payroll/processing/config/lock-logs → audit trail
  ─── Commission Config ───────────────────────────────────────
  GET    /api/payroll/processing/commission      → get
  POST   /api/payroll/processing/commission      → upsert
  PATCH  /api/payroll/processing/commission      → update
  ─── Statutory Settings ──────────────────────────────────────
  GET    /api/payroll/processing/statutory       → get
  POST   /api/payroll/processing/statutory       → upsert
  PATCH  /api/payroll/processing/statutory       → update
  ─── Components ──────────────────────────────────────────────
  GET    /api/payroll/processing/components              → grouped list
  GET    /api/payroll/processing/components/all          → flat list
  POST   /api/payroll/processing/components              → add component
  PATCH  /api/payroll/processing/components/{id}         → edit component
  DELETE /api/payroll/processing/components/{id}         → soft-delete
─────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from schema.Payroll.Payrol_Processing import (
    CommissionConfigCreate,
    CommissionConfigResponse,
    CommissionConfigUpdate,
    ComponentsTableResponse,
    LockPayrollRequest,
    PayrollComponentCreate,
    PayrollComponentResponse,
    PayrollComponentUpdate,
    PayrollConfigCreate,
    PayrollConfigResponse,
    PayrollConfigUpdate,
    PayrollLockLogResponse,
    PayrollLockResponse,
    PayrollProcessingPageResponse,
    StatutorySettingsCreate,
    StatutorySettingsResponse,
    StatutorySettingsUpdate,
)
from services.Payroll.Payroll_Processing import (
    CommissionConfigService,
    PayrollComponentService,
    PayrollConfigService,
    PayrollProcessingPageService,
    StatutorySettingsService,
)

router = APIRouter(prefix="/processing", tags=["Payroll Processing"])


# ===========================================================================
# Full page endpoint — single GET to hydrate the entire page
# ===========================================================================

@router.get(
    "",
    response_model=PayrollProcessingPageResponse,
    summary="Get full Payroll Processing page config",
    description=(
        "Returns payroll cycle config, commission settings, statutory settings, "
        "and salary component table in one response — eliminates multiple round-trips."
    ),
)
def get_full_processing_page(db: Session = Depends(get_db)) -> PayrollProcessingPageResponse:
    return PayrollProcessingPageService.get_full_page(db)


# ===========================================================================
# Payroll Config endpoints
# ===========================================================================

@router.get(
    "/config",
    response_model=Optional[PayrollConfigResponse],
    summary="Get payroll cycle configuration",
)
def get_payroll_config(db: Session = Depends(get_db)):
    return PayrollConfigService.get(db)


@router.post(
    "/config",
    response_model=PayrollConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or replace payroll cycle configuration (upsert)",
)
def upsert_payroll_config(
    payload: PayrollConfigCreate, db: Session = Depends(get_db)
) -> PayrollConfigResponse:
    return PayrollConfigService.upsert(db, payload)


@router.patch(
    "/config",
    response_model=PayrollConfigResponse,
    summary="Partially update payroll cycle configuration",
)
def update_payroll_config(
    payload: PayrollConfigUpdate, db: Session = Depends(get_db)
) -> PayrollConfigResponse:
    return PayrollConfigService.update(db, payload)


# ── Lock / Unlock ──────────────────────────────────────────────────────────

@router.post(
    "/config/lock",
    response_model=PayrollLockResponse,
    summary="Lock payroll — prevents further changes until unlocked",
)
def lock_payroll(
    payload: LockPayrollRequest, db: Session = Depends(get_db)
) -> PayrollLockResponse:
    config = PayrollConfigService.lock(db, payload)
    return PayrollLockResponse(
        payroll_status=config.payroll_status,
        locked_by=config.locked_by,
        locked_at=config.locked_at,
        lock_reason=config.lock_reason,
        message="Payroll has been locked successfully.",
    )


@router.post(
    "/config/unlock",
    response_model=PayrollLockResponse,
    summary="Unlock payroll — re-enables editing",
)
def unlock_payroll(
    payload: LockPayrollRequest, db: Session = Depends(get_db)
) -> PayrollLockResponse:
    config = PayrollConfigService.unlock(db, payload)
    return PayrollLockResponse(
        payroll_status=config.payroll_status,
        locked_by=None,
        locked_at=None,
        lock_reason=None,
        message="Payroll has been unlocked successfully.",
    )


@router.get(
    "/config/lock-logs",
    response_model=list[PayrollLockLogResponse],
    summary="Audit log of all lock / unlock actions",
)
def get_lock_audit_log(
    limit: int = Query(50, ge=1, le=500, description="Max rows to return"),
    db: Session = Depends(get_db),
) -> list[PayrollLockLogResponse]:
    return PayrollConfigService.get_lock_logs(db, limit)


# ===========================================================================
# Commission Config endpoints
# ===========================================================================

@router.get(
    "/commission",
    response_model=Optional[CommissionConfigResponse],
    summary="Get Sales / Commission configuration",
)
def get_commission_config(db: Session = Depends(get_db)):
    return CommissionConfigService.get(db)


@router.post(
    "/commission",
    response_model=CommissionConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or replace Sales / Commission configuration (upsert)",
)
def upsert_commission_config(
    payload: CommissionConfigCreate, db: Session = Depends(get_db)
) -> CommissionConfigResponse:
    return CommissionConfigService.upsert(db, payload)


@router.patch(
    "/commission",
    response_model=CommissionConfigResponse,
    summary="Partially update Sales / Commission configuration",
)
def update_commission_config(
    payload: CommissionConfigUpdate, db: Session = Depends(get_db)
) -> CommissionConfigResponse:
    return CommissionConfigService.update(db, payload)


# ===========================================================================
# Statutory Settings endpoints
# ===========================================================================

@router.get(
    "/statutory",
    response_model=Optional[StatutorySettingsResponse],
    summary="Get Statutory Compliance Settings",
)
def get_statutory_settings(db: Session = Depends(get_db)):
    return StatutorySettingsService.get(db)


@router.post(
    "/statutory",
    response_model=StatutorySettingsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or replace Statutory Compliance Settings (upsert)",
)
def upsert_statutory_settings(
    payload: StatutorySettingsCreate, db: Session = Depends(get_db)
) -> StatutorySettingsResponse:
    return StatutorySettingsService.upsert(db, payload)


@router.patch(
    "/statutory",
    response_model=StatutorySettingsResponse,
    summary="Partially update Statutory Compliance Settings",
)
def update_statutory_settings(
    payload: StatutorySettingsUpdate, db: Session = Depends(get_db)
) -> StatutorySettingsResponse:
    return StatutorySettingsService.update(db, payload)


# ===========================================================================
# Payroll Components endpoints  (Salary Component Configuration table)
# ===========================================================================

@router.get(
    "/components",
    response_model=ComponentsTableResponse,
    summary="Get salary components grouped by type (mirrors the UI table)",
)
def get_components_grouped(
    active_only: bool = Query(True, description="Filter to active components only"),
    db: Session = Depends(get_db),
) -> ComponentsTableResponse:
    return PayrollComponentService.list_grouped(db, active_only)


@router.get(
    "/components/all",
    response_model=list[PayrollComponentResponse],
    summary="Get flat list of all salary components",
)
def list_all_components(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
) -> list[PayrollComponentResponse]:
    return PayrollComponentService.list_all(db, active_only)


@router.post(
    "/components",
    response_model=PayrollComponentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new salary component (+ Add Component button)",
)
def create_component(
    payload: PayrollComponentCreate, db: Session = Depends(get_db)
) -> PayrollComponentResponse:
    return PayrollComponentService.create(db, payload)


@router.patch(
    "/components/{component_id}",
    response_model=PayrollComponentResponse,
    summary="Edit a salary component (Edit button in table)",
)
def update_component(
    component_id: int,
    payload: PayrollComponentUpdate,
    db: Session = Depends(get_db),
) -> PayrollComponentResponse:
    return PayrollComponentService.update(db, component_id, payload)


@router.delete(
    "/components/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a salary component (Delete button in table)",
)
def delete_component(
    component_id: int,
    db: Session = Depends(get_db),
) -> None:
    PayrollComponentService.delete(db, component_id)