from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from core.database import get_db
from model.HR_Operations.transfer import Transfer
from schema.HR_Operations.transfer import (
    TransferCreate,
    TransferUpdate,
    TransferResponse,
)

router = APIRouter(prefix="/api/hr-operations/transfers", tags=["HR Operations - Transfers"])


# ──────────────────────────────────────────────
# CREATE Transfer
# ──────────────────────────────────────────────
@router.post("/", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(payload: TransferCreate, db: Session = Depends(get_db)):
    """Initiate a transfer request for an employee."""
    valid_types = {"INTER_DEPARTMENT", "INTER_LOCATION", "INTER_COMPANY"}
    if payload.transfer_type.upper() not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transfer_type. Allowed: {valid_types}",
        )

    transfer = Transfer(**payload.model_dump())
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return transfer


# ──────────────────────────────────────────────
# LIST ALL Transfers
# ──────────────────────────────────────────────
@router.get("/", response_model=List[TransferResponse])
def list_transfers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Retrieve all transfer records, newest first."""
    transfers = (
        db.query(Transfer)
        .order_by(Transfer.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return transfers


# ──────────────────────────────────────────────
# GET Transfers by Employee ID
# ──────────────────────────────────────────────
@router.get("/employee/{employee_id}", response_model=List[TransferResponse])
def get_transfers_by_employee(employee_id: int, db: Session = Depends(get_db)):
    """Retrieve all transfers for a specific employee."""
    transfers = (
        db.query(Transfer)
        .filter(Transfer.employee_id == employee_id)
        .order_by(Transfer.created_at.desc())
        .all()
    )
    return transfers


# ──────────────────────────────────────────────
# GET Transfer by ID
# ──────────────────────────────────────────────
@router.get("/{transfer_id}", response_model=TransferResponse)
def get_transfer(transfer_id: int, db: Session = Depends(get_db)):
    """Retrieve a single transfer record by ID."""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer record not found")
    return transfer


# ──────────────────────────────────────────────
# UPDATE Transfer (approve / reject / complete)
# ──────────────────────────────────────────────
@router.patch("/{transfer_id}", response_model=TransferResponse)
def update_transfer(
    transfer_id: int,
    payload: TransferUpdate,
    db: Session = Depends(get_db),
):
    """Update transfer status, approver or remarks."""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer record not found")

    valid_statuses = {"PENDING", "APPROVED", "REJECTED", "COMPLETED"}
    if payload.status and payload.status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {valid_statuses}",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(transfer, field, value)

    transfer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(transfer)
    return transfer


# ──────────────────────────────────────────────
# DELETE Transfer
# ──────────────────────────────────────────────
@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transfer(transfer_id: int, db: Session = Depends(get_db)):
    """Delete a transfer record (only if still PENDING)."""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer record not found")
    if transfer.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Only PENDING transfers can be deleted",
        )
    db.delete(transfer)
    db.commit()
