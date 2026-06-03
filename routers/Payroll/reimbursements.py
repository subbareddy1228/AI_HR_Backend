from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

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


# Create reimbursement
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
        .all()
    )

    return reimbursements


# Get reimbursement by ID
@router.get(
    "/{reimbursement_id}",
    response_model=ReimbursementResponse
)
def get_reimbursement(
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

    reimbursement.status = "APPROVED"

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

    reimbursement.status = "REJECTED"

    db.commit()
    db.refresh(reimbursement)

    return {
        "message":
        "Reimbursement rejected successfully"
    }


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
        .all()
    )

    return reimbursements


# Filter reimbursements
@router.get("/filter")
def filter_reimbursements(
    status: Optional[str] = None,
    claim_type: Optional[str] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Reimbursement)

    if status:
        query = query.filter(
            Reimbursement.status == status
        )

    if claim_type:
        query = query.filter(
            Reimbursement.claim_type == claim_type
        )

    if employee_id:
        query = query.filter(
            Reimbursement.employee_id ==
            employee_id
        )

    return query.all()


# Reimbursement reports
@router.get("/reports")
def reimbursement_reports(
    db: Session = Depends(get_db)
):
    claims = (
        db.query(Reimbursement)
        .all()
    )

    total_claims = len(claims)

    approved = len([
        c for c in claims
        if c.status == "APPROVED"
    ])

    rejected = len([
        c for c in claims
        if c.status == "REJECTED"
    ])

    pending = len([
        c for c in claims
        if c.status == "PENDING"
    ])

    total_amount = sum([
        c.amount for c in claims
    ])

    return {
        "total_claims": total_claims,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "total_amount": total_amount
    }


# Download receipt
@router.get("/receipt/{claim_id}")
def download_receipt(
    claim_id: int,
    db: Session = Depends(get_db)
):
    claim = (
        db.query(Reimbursement)
        .filter(
            Reimbursement.id == claim_id
        )
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    if not claim.receipt_path:
        raise HTTPException(
            status_code=404,
            detail="Receipt not found"
        )

    return FileResponse(
        claim.receipt_path
    )