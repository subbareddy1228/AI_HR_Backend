from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from schema.Payroll.payroll_processing import (
    PayrollConfigUpdate,
    PayrollConfigResponse,
    PayrollLockRequest,
    SalaryComponentCreate,
    SalaryComponentUpdate,
    SalaryComponentResponse,
    PayrollFullConfigResponse,
)
#import services.Payroll.payroll_processing as svc

router = APIRouter(
    prefix="/payroll-processing",
    tags=["Payroll Processing"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  PAYROLL CONFIG
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/config",
    response_model=PayrollConfigResponse,
    summary="Get payroll cycle configuration & settings",
)
def get_config(db: Session = Depends(get_db)):
    return svc.get_config(db)


@router.put(
    "/config",
    response_model=PayrollConfigResponse,
    summary="Update payroll cycle configuration & settings",
)
def update_config(
    payload: PayrollConfigUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_config(db, payload)


# ── Lock / Unlock ─────────────────────────────────────────────────────────────

@router.put(
    "/config/lock",
    summary="Lock payroll — disables all processing functions",
)
def lock_payroll(
    payload: PayrollLockRequest,
    db: Session = Depends(get_db),
):
    config, error = svc.lock_payroll(db, reason=payload.reason)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Payroll locked successfully", "payroll_status": "LOCKED"}


@router.put(
    "/config/unlock",
    summary="Unlock payroll — re-enables all processing functions",
)
def unlock_payroll(db: Session = Depends(get_db)):
    config, error = svc.unlock_payroll(db)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Payroll unlocked successfully", "payroll_status": "ACTIVE"}


# ── Export Config ─────────────────────────────────────────────────────────────

@router.get(
    "/config/export",
    response_model=PayrollFullConfigResponse,
    summary="Export full payroll configuration including salary components",
)
def export_config(db: Session = Depends(get_db)):
    return svc.export_config(db)


# ══════════════════════════════════════════════════════════════════════════════
#  SALARY COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/components",
    response_model=List[SalaryComponentResponse],
    summary="List salary components (earnings & deductions)",
)
def get_all_components(
    component_type: Optional[str] = None,   # earnings | deductions
    is_active: Optional[bool]     = True,
    db: Session = Depends(get_db),
):
    return svc.get_all_components(db, component_type=component_type, is_active=is_active)


@router.post(
    "/components",
    response_model=SalaryComponentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new salary component",
)
def create_component(
    payload: SalaryComponentCreate,
    db: Session = Depends(get_db),
):
    return svc.create_component(db, payload)


@router.get(
    "/components/{component_id}",
    response_model=SalaryComponentResponse,
    summary="Get a single salary component by ID",
)
def get_component(component_id: int, db: Session = Depends(get_db)):
    component = svc.get_component_by_id(db, component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Salary component not found")
    return component


@router.put(
    "/components/{component_id}",
    response_model=SalaryComponentResponse,
    summary="Edit a salary component (Edit button on UI)",
)
def update_component(
    component_id: int,
    payload: SalaryComponentUpdate,
    db: Session = Depends(get_db),
):
    component = svc.update_component(db, component_id, payload)
    if not component:
        raise HTTPException(status_code=404, detail="Salary component not found")
    return component


@router.delete(
    "/components/{component_id}",
    summary="Delete a salary component (Delete button on UI)",
)
def delete_component(component_id: int, db: Session = Depends(get_db)):
    if not svc.delete_component(db, component_id):
        raise HTTPException(status_code=404, detail="Salary component not found")
    return {"message": "Salary component deleted successfully"}


# ── Seed defaults ─────────────────────────────────────────────────────────────

@router.post(
    "/components/seed-defaults",
    response_model=List[SalaryComponentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Seed default salary components from UI (Basic Salary, HRA, PF etc.)",
)
def seed_defaults(db: Session = Depends(get_db)):
    return svc.seed_default_components(db)