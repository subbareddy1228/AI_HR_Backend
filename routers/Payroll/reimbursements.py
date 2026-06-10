from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_, cast, String
from datetime import datetime, timezone

from core.database import get_db
from model.Payroll.reimbursement import Reimbursement
from schema.Payroll.reimbursement import (
    ReimbursementCreate,
    ReimbursementUpdate,
    ReimbursementResponse
)

router = APIRouter(
    prefix="/reimbursements",
    tags=["Reimbursements"]
)


# Create reimbursement claim
@router.post(
    "/",
    response_model=ReimbursementResponse,
    status_code=status.HTTP_201_CREATED
)
def create_reimbursement(
    payload: ReimbursementCreate,
    db: Session = Depends(get_db)
):
    reimbursement = Reimbursement(
        **payload.model_dump()
    )

    db.add(reimbursement)
    db.commit()
    db.refresh(reimbursement)

    return reimbursement


# Get all reimbursements
@router.get(
    "/",
    response_model=List[ReimbursementResponse]
)
def get_all_reimbursements(
    db: Session = Depends(get_db)
):
    reimbursements = (
        db.query(Reimbursement)
        .order_by(Reimbursement.id.desc())
        .all()
    )

    return reimbursements


# ── FIX: /employee, /filter, /reports, /export must come BEFORE /{reimbursement_id}
#         otherwise FastAPI tries to cast e.g. "filter" as int → 422 Unprocessable Entity


# Employee reimbursement history
@router.get(
    "/employee/{employee_id}",
    response_model=List[ReimbursementResponse]
)
def employee_reimbursements(
    employee_id: int,
    db: Session = Depends(get_db)
):
    reimbursements = (
        db.query(Reimbursement)
        .filter(
            Reimbursement.employee_id == employee_id
        )
        .order_by(Reimbursement.id.desc())
        .all()
    )

    return reimbursements


# Search & Filter reimbursements
@router.get("/filter")
def filter_reimbursements(
    status: Optional[str] = None,
    claim_type: Optional[str] = None,
    employee_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Reimbursement)

    if status:
        # ── FIX: normalise to uppercase so "pending" and "PENDING" both match
        query = query.filter(
            Reimbursement.status == status.upper()
        )

    if claim_type:
        query = query.filter(
            Reimbursement.claim_type == claim_type
        )

    if employee_id:
        query = query.filter(
            Reimbursement.employee_id == employee_id
        )

    if search:
        query = query.filter(
            or_(
                cast(
                    Reimbursement.employee_id,
                    String
                ).ilike(f"%{search}%"),

                Reimbursement.claim_type.ilike(
                    f"%{search}%"
                ),

                cast(
                    Reimbursement.amount,
                    String
                ).ilike(f"%{search}%"),

                Reimbursement.status.ilike(
                    f"%{search}%"
                )
            )
        )

    return query.order_by(
        Reimbursement.id.desc()
    ).all()


# Dashboard reports
@router.get("/reports")
def reimbursement_reports(
    db: Session = Depends(get_db)
):
    reimbursements = (
        db.query(Reimbursement)
        .all()
    )

    total_claims = len(reimbursements)

    approved = len([
        r for r in reimbursements
        if r.status == "APPROVED"
    ])

    rejected = len([
        r for r in reimbursements
        if r.status == "REJECTED"
    ])

    # ── FIX: single consistent uppercase check
    pending = len([
        r for r in reimbursements
        if r.status == "PENDING"
    ])

    paid = len([
        r for r in reimbursements
        if r.status == "PAID"
    ])

    total_amount = round(sum([
        float(r.amount)
        for r in reimbursements
    ]), 2)

    return {
        "total_claims": total_claims,
        "approved":     approved,
        "pending":      pending,
        "rejected":     rejected,
        "paid":         paid,
        "total_amount": total_amount
    }


# Export reimbursements
@router.get("/export")
def export_reimbursements():
    return {
        "message":
        "Export feature coming soon"
    }


# Get reimbursement by ID
@router.get(
    "/{reimbursement_id}",
    response_model=ReimbursementResponse
)
def get_reimbursement_by_id(
    reimbursement_id: int,
    db: Session = Depends(get_db)
):
    reimbursement = (
        db.query(Reimbursement)
        .filter(
            Reimbursement.id == reimbursement_id
        )
        .first()
    )

    if not reimbursement:
        raise HTTPException(
            status_code=404,
            detail="Reimbursement not found"
        )

    return reimbursement


# Update reimbursement
@router.put(
    "/{reimbursement_id}",
    response_model=ReimbursementResponse
)
def update_reimbursement(
    reimbursement_id: int,
    payload: ReimbursementUpdate,
    db: Session = Depends(get_db)
):
    reimbursement = (
        db.query(Reimbursement)
        .filter(
            Reimbursement.id == reimbursement_id
        )
        .first()
    )

    if not reimbursement:
        raise HTTPException(
            status_code=404,
            detail="Reimbursement not found"
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(reimbursement, key, value)

    db.commit()
    db.refresh(reimbursement)

    return reimbursement


# Delete reimbursement
@router.delete("/{reimbursement_id}")
def delete_reimbursement(
    reimbursement_id: int,
    db: Session = Depends(get_db)
):
    reimbursement = (
        db.query(Reimbursement)
        .filter(
            Reimbursement.id == reimbursement_id
        )
        .first()
    )

    if not reimbursement:
        raise HTTPException(
            status_code=404,
            detail="Reimbursement not found"
        )

    db.delete(reimbursement)
    db.commit()

    return {
        "message":
        "Reimbursement deleted successfully"
    }


# Approve reimbursement
@router.put("/{reimbursement_id}/approve")
def approve_reimbursement(
    reimbursement_id: int,
    approved_by: Optional[str] = None,
    remarks: Optional[str] = None,
    db: Session = Depends(get_db)
):
    reimbursement = (
        db.query(Reimbursement)
        .filter(
            Reimbursement.id == reimbursement_id
        )
        .first()
    )

    if not reimbursement:
        raise HTTPException(
            status_code=404,
            detail="Reimbursement not found"
        )

    # ── FIX: guard against double-approving
    if reimbursement.status == "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="Reimbursement is already approved"
        )

    reimbursement.status = "APPROVED"
    reimbursement.approved_by = approved_by
    reimbursement.remarks = remarks

    db.commit()
    db.refresh(reimbursement)

    return {
        "message":
        "Reimbursement approved successfully"
    }


# Reject reimbursement
@router.put("/{reimbursement_id}/reject")
def reject_reimbursement(
    reimbursement_id: int,
    approved_by: Optional[str] = None,
    remarks: Optional[str] = None,
    db: Session = Depends(get_db)
):
    reimbursement = (
        db.query(Reimbursement)
        .filter(
            Reimbursement.id == reimbursement_id
        )
        .first()
    )

    if not reimbursement:
        raise HTTPException(
            status_code=404,
            detail="Reimbursement not found"
        )

    # ── FIX: guard against double-rejecting
    if reimbursement.status == "REJECTED":
        raise HTTPException(
            status_code=400,
            detail="Reimbursement is already rejected"
        )

    reimbursement.status = "REJECTED"
    reimbursement.approved_by = approved_by
    reimbursement.remarks = remarks

    db.commit()
    db.refresh(reimbursement)

    return {
        "message":
        "Reimbursement rejected successfully"
    }


# Mark reimbursement as paid
@router.put("/{reimbursement_id}/pay")
def pay_reimbursement(
    reimbursement_id: int,
    payment_mode: Optional[str] = None,
    payment_reference: Optional[str] = None,
    db: Session = Depends(get_db)
):
    reimbursement = (
        db.query(Reimbursement)
        .filter(
            Reimbursement.id == reimbursement_id
        )
        .first()
    )

    if not reimbursement:
        raise HTTPException(
            status_code=404,
            detail="Reimbursement not found"
        )

    if reimbursement.status != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="Only approved reimbursements can be marked as paid"
        )

    reimbursement.status            = "PAID"
    reimbursement.payment_mode      = payment_mode
    reimbursement.payment_reference = payment_reference
    reimbursement.paid_at           = datetime.now(timezone.utc)

    db.commit()
    db.refresh(reimbursement)

    return {
        "message":
        "Reimbursement marked as paid successfully"
    }