from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from schema.Payroll.reimbursement import (
    ReimbursementTypeCreate,
    ReimbursementTypeUpdate,
    ReimbursementTypeResponse,
    ReimbursementClaimCreate,
    ReimbursementClaimUpdate,
    ReimbursementClaimResponse,
    ReimbursementBalanceResponse,
    ReimbursementDashboard,
    ReimbursementReportsResponse,
)
#import services.Payroll.reimbursement as svc

router = APIRouter(
    prefix="/reimbursements",
    tags=["Payroll - Reimbursements"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  STATIC ROUTES — must be before /{id} routes
# ══════════════════════════════════════════════════════════════════════════════

# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=ReimbursementDashboard)
def get_dashboard(db: Session = Depends(get_db)):
    return svc.get_dashboard(db)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports")
def get_reports(db: Session = Depends(get_db)):
    return svc.get_reports(db)


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/export")
def export_reimbursements():
    return {"message": "Export feature coming soon"}


# ── Balances ──────────────────────────────────────────────────────────────────

@router.get(
    "/balances",
    response_model=List[ReimbursementBalanceResponse],
)
def get_balances(
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return svc.get_balances(db, employee_id=employee_id)


# ── Filter claims ─────────────────────────────────────────────────────────────

@router.get(
    "/claims/filter",
    response_model=List[ReimbursementClaimResponse],
)
def filter_claims(
    status: Optional[str]        = None,
    claim_type_id: Optional[int] = None,
    employee_id: Optional[int]   = None,
    search: Optional[str]        = None,
    db: Session = Depends(get_db),
):
    return svc.get_all_claims(
        db,
        status=status,
        claim_type_id=claim_type_id,
        employee_id=employee_id,
        search=search,
    )


# ── Employee claims ───────────────────────────────────────────────────────────

@router.get(
    "/claims/employee/{employee_id}",
    response_model=List[ReimbursementClaimResponse],
)
def get_employee_claims(
    employee_id: int,
    db: Session = Depends(get_db),
):
    return svc.get_all_claims(db, employee_id=employee_id)


# ══════════════════════════════════════════════════════════════════════════════
#  MASTER — Reimbursement Types
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/types",
    response_model=List[ReimbursementTypeResponse],
)
def get_all_types(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    return svc.get_all_types(db, is_active=is_active)


@router.post(
    "/types",
    response_model=ReimbursementTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_type(
    payload: ReimbursementTypeCreate,
    db: Session = Depends(get_db),
):
    return svc.create_type(db, payload)


@router.get(
    "/types/{type_id}",
    response_model=ReimbursementTypeResponse,
)
def get_type(type_id: int, db: Session = Depends(get_db)):
    rtype = svc.get_type_by_id(db, type_id)
    if not rtype:
        raise HTTPException(status_code=404, detail="Reimbursement type not found")
    return rtype


@router.put(
    "/types/{type_id}",
    response_model=ReimbursementTypeResponse,
)
def update_type(
    type_id: int,
    payload: ReimbursementTypeUpdate,
    db: Session = Depends(get_db),
):
    rtype = svc.update_type(db, type_id, payload)
    if not rtype:
        raise HTTPException(status_code=404, detail="Reimbursement type not found")
    return rtype


@router.delete("/types/{type_id}")
def delete_type(type_id: int, db: Session = Depends(get_db)):
    if not svc.delete_type(db, type_id):
        raise HTTPException(status_code=404, detail="Reimbursement type not found")
    return {"message": "Reimbursement type deleted successfully"}


# ══════════════════════════════════════════════════════════════════════════════
#  CLAIMS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/claims",
    response_model=List[ReimbursementClaimResponse],
)
def get_all_claims(db: Session = Depends(get_db)):
    return svc.get_all_claims(db)


@router.post(
    "/claims",
    response_model=ReimbursementClaimResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_claim(
    payload: ReimbursementClaimCreate,
    db: Session = Depends(get_db),
):
    claim, error = svc.create_claim(db, payload)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return claim


@router.get(
    "/claims/{claim_id}",
    response_model=ReimbursementClaimResponse,
)
def get_claim(claim_id: int, db: Session = Depends(get_db)):
    claim = svc.get_claim_by_id(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.put(
    "/claims/{claim_id}",
    response_model=ReimbursementClaimResponse,
)
def update_claim(
    claim_id: int,
    payload: ReimbursementClaimUpdate,
    db: Session = Depends(get_db),
):
    claim = svc.update_claim(db, claim_id, payload)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.delete("/claims/{claim_id}")
def delete_claim(claim_id: int, db: Session = Depends(get_db)):
    if not svc.delete_claim(db, claim_id):
        raise HTTPException(status_code=404, detail="Claim not found")
    return {"message": "Claim deleted successfully"}


# ── Manager approval ──────────────────────────────────────────────────────────

@router.put("/claims/{claim_id}/manager-approve")
def manager_approve(
    claim_id: int,
    approved_by: Optional[str] = None,
    remarks: Optional[str]     = None,
    db: Session = Depends(get_db),
):
    claim, error = svc.manager_approve(db, claim_id, approved_by, remarks)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Claim approved by manager successfully"}


@router.put("/claims/{claim_id}/manager-reject")
def manager_reject(
    claim_id: int,
    approved_by: Optional[str] = None,
    remarks: Optional[str]     = None,
    db: Session = Depends(get_db),
):
    claim, error = svc.manager_reject(db, claim_id, approved_by, remarks)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Claim rejected by manager"}


# ── Finance approval ──────────────────────────────────────────────────────────

@router.put("/claims/{claim_id}/finance-approve")
def finance_approve(
    claim_id: int,
    approved_by: Optional[str] = None,
    remarks: Optional[str]     = None,
    db: Session = Depends(get_db),
):
    claim, error = svc.finance_approve(db, claim_id, approved_by, remarks)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Claim approved by finance successfully"}


@router.put("/claims/{claim_id}/finance-reject")
def finance_reject(
    claim_id: int,
    approved_by: Optional[str] = None,
    remarks: Optional[str]     = None,
    db: Session = Depends(get_db),
):
    claim, error = svc.finance_reject(db, claim_id, approved_by, remarks)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Claim rejected by finance"}