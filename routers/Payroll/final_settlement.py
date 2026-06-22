from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from schema.Payroll.final_settlement import (
    FinalSettlementCreate,
    FinalSettlementUpdate,
    FinalSettlementResponse,
    FinalSettlementDetailResponse,
    FinalSettlementDashboard,
    FinalSettlementReport,
    SettlementAdditionCreate,
    SettlementAdditionUpdate,
    SettlementAdditionResponse,
    SettlementDeductionCreate,
    SettlementDeductionUpdate,
    SettlementDeductionResponse,
    SettlementApproveRequest,
    SettlementRejectRequest,
    SettlementPayRequest,
)
import services.Payroll.final_settlement_service as svc

router = APIRouter(
    prefix="/final-settlement",
    tags=["Payroll - Final Settlement"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  STATIC ROUTES — before /{settlement_id} to avoid FastAPI int-cast errors
# ══════════════════════════════════════════════════════════════════════════════

# ── Filter by employee ────────────────────────────────────────────────────────

@router.get(
    "/employee/{employee_id}",
    response_model=FinalSettlementDetailResponse,
    summary="Get latest settlement for an employee",
)
def get_by_employee(employee_id: int, db: Session = Depends(get_db)):
    settlement = svc.get_by_employee(db, employee_id)
    if not settlement:
        raise HTTPException(status_code=404, detail="No settlement found for this employee")
    return settlement


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/export", summary="Export all settlements")
def export_settlements():
    return {"message": "Export feature coming soon"}


# ══════════════════════════════════════════════════════════════════════════════
#  CORE CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/",
    response_model=List[FinalSettlementResponse],
    summary="List all settlements",
)
def get_all(
    status: Optional[str]      = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return svc.get_all(db, status=status, employee_id=employee_id)


@router.post(
    "/",
    response_model=FinalSettlementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new final settlement",
)
def create_settlement(
    payload: FinalSettlementCreate,
    db: Session = Depends(get_db),
):
    return svc.create(db, payload)


@router.get(
    "/{settlement_id}",
    response_model=FinalSettlementDetailResponse,
    summary="Get full settlement detail with additions & deductions",
)
def get_settlement(settlement_id: int, db: Session = Depends(get_db)):
    settlement = svc.get_by_id(db, settlement_id)
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return settlement


@router.put(
    "/{settlement_id}",
    response_model=FinalSettlementResponse,
    summary="Update settlement details",
)
def update_settlement(
    settlement_id: int,
    payload: FinalSettlementUpdate,
    db: Session = Depends(get_db),
):
    settlement = svc.update(db, settlement_id, payload)
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return settlement


@router.delete(
    "/{settlement_id}",
    summary="Delete a settlement",
)
def delete_settlement(settlement_id: int, db: Session = Depends(get_db)):
    if not svc.delete(db, settlement_id):
        raise HTTPException(status_code=404, detail="Settlement not found")
    return {"message": "Settlement deleted successfully"}


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD (4 cards — Current Settlement, Total Additions,
#             Total Deductions, Approval Status)
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{settlement_id}/dashboard",
    response_model=FinalSettlementDashboard,
    summary="Get dashboard summary cards for a settlement",
)
def get_dashboard(settlement_id: int, db: Session = Depends(get_db)):
    data = svc.get_dashboard(db, settlement_id)
    if not data:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return data


# ══════════════════════════════════════════════════════════════════════════════
#  QUICK ACTIONS
# ══════════════════════════════════════════════════════════════════════════════

# ── Recalculate (Recalculate button) ─────────────────────────────────────────

@router.put(
    "/{settlement_id}/recalculate",
    response_model=FinalSettlementResponse,
    summary="Recalculate settlement totals from line items",
)
def recalculate(settlement_id: int, db: Session = Depends(get_db)):
    settlement, error = svc.recalculate(db, settlement_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return settlement


# ── Approve (Approve button) ──────────────────────────────────────────────────

@router.put(
    "/{settlement_id}/approve",
    summary="Approve a settlement",
)
def approve(
    settlement_id: int,
    payload: SettlementApproveRequest,
    db: Session = Depends(get_db),
):
    settlement, error = svc.approve(db, settlement_id, payload)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Settlement approved successfully"}


# ── Reject ────────────────────────────────────────────────────────────────────

@router.put(
    "/{settlement_id}/reject",
    summary="Reject a settlement",
)
def reject(
    settlement_id: int,
    payload: SettlementRejectRequest,
    db: Session = Depends(get_db),
):
    settlement, error = svc.reject(db, settlement_id, payload)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Settlement rejected"}


# ── Mark as Paid ──────────────────────────────────────────────────────────────

@router.put(
    "/{settlement_id}/pay",
    summary="Mark settlement as paid — fills Payment Processing date",
)
def mark_paid(
    settlement_id: int,
    payload: SettlementPayRequest,
    db: Session = Depends(get_db),
):
    settlement, error = svc.mark_paid(db, settlement_id, payload)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Settlement marked as paid successfully"}


# ── Generate Report (Generate Report button) ──────────────────────────────────

@router.get(
    "/{settlement_id}/report",
    response_model=FinalSettlementReport,
    summary="Generate full settlement report",
)
def generate_report(settlement_id: int, db: Session = Depends(get_db)):
    settlement, error = svc.generate_report(db, settlement_id)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return settlement


# ══════════════════════════════════════════════════════════════════════════════
#  ADDITIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{settlement_id}/additions",
    response_model=List[SettlementAdditionResponse],
    summary="List all additions for a settlement",
)
def get_additions(settlement_id: int, db: Session = Depends(get_db)):
    return svc.get_additions(db, settlement_id)


@router.post(
    "/{settlement_id}/additions",
    response_model=SettlementAdditionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an addition line item (Leave Encashment, Gratuity, Bonus etc.)",
)
def add_addition(
    settlement_id: int,
    payload: SettlementAdditionCreate,
    db: Session = Depends(get_db),
):
    addition, error = svc.add_addition(db, settlement_id, payload)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return addition


@router.put(
    "/{settlement_id}/additions/{addition_id}",
    response_model=SettlementAdditionResponse,
    summary="Update an addition line item",
)
def update_addition(
    settlement_id: int,
    addition_id: int,
    payload: SettlementAdditionUpdate,
    db: Session = Depends(get_db),
):
    addition = svc.update_addition(db, addition_id, payload)
    if not addition:
        raise HTTPException(status_code=404, detail="Addition not found")
    return addition


@router.delete(
    "/{settlement_id}/additions/{addition_id}",
    summary="Delete an addition line item",
)
def delete_addition(
    settlement_id: int,
    addition_id: int,
    db: Session = Depends(get_db),
):
    if not svc.delete_addition(db, addition_id):
        raise HTTPException(status_code=404, detail="Addition not found")
    return {"message": "Addition deleted successfully"}


# ══════════════════════════════════════════════════════════════════════════════
#  DEDUCTIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{settlement_id}/deductions",
    response_model=List[SettlementDeductionResponse],
    summary="List all deductions for a settlement",
)
def get_deductions(settlement_id: int, db: Session = Depends(get_db)):
    return svc.get_deductions(db, settlement_id)


@router.post(
    "/{settlement_id}/deductions",
    response_model=SettlementDeductionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a deduction line item (Loan Recovery, TDS, Notice Shortfall etc.)",
)
def add_deduction(
    settlement_id: int,
    payload: SettlementDeductionCreate,
    db: Session = Depends(get_db),
):
    deduction, error = svc.add_deduction(db, settlement_id, payload)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return deduction


@router.put(
    "/{settlement_id}/deductions/{deduction_id}",
    response_model=SettlementDeductionResponse,
    summary="Update a deduction line item",
)
def update_deduction(
    settlement_id: int,
    deduction_id: int,
    payload: SettlementDeductionUpdate,
    db: Session = Depends(get_db),
):
    deduction = svc.update_deduction(db, deduction_id, payload)
    if not deduction:
        raise HTTPException(status_code=404, detail="Deduction not found")
    return deduction


@router.delete(
    "/{settlement_id}/deductions/{deduction_id}",
    summary="Delete a deduction line item",
)
def delete_deduction(
    settlement_id: int,
    deduction_id: int,
    db: Session = Depends(get_db),
):
    if not svc.delete_deduction(db, deduction_id):
        raise HTTPException(status_code=404, detail="Deduction not found")
    return {"message": "Deduction deleted successfully"}