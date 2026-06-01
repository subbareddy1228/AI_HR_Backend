# FILE 16 of 18 | routers/Payroll/bank_transfer.py
# Router: Bank Transfers — prefix: /bank-transfers  (mounted under /api/payroll in main.py)
# Endpoints:
#   POST   /bank-transfers/                         — create
#   GET    /bank-transfers/                         — list all
#   GET    /bank-transfers/payroll-run/{run_id}     — all transfers for a payroll run
#   GET    /bank-transfers/{id}                     — get one
#   PUT    /bank-transfers/{id}                     — update
#   DELETE /bank-transfers/{id}                     — delete
#   PATCH  /bank-transfers/{id}/mark-success        — set status Success
#   PATCH  /bank-transfers/{id}/mark-failed         — set status Failed

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from core.database import get_db
from model.Payroll.bank_transfer import BankTransfer
from schema.Payroll.bank_transfer import BankTransferCreate, BankTransferUpdate, BankTransferResponse

router = APIRouter(prefix="/bank-transfers", tags=["Payroll"])


class TransferStatusPayload(BaseModel):
    utr_number: Optional[str] = None
    remarks: Optional[str] = None


@router.post("/", response_model=BankTransferResponse, status_code=status.HTTP_201_CREATED)
def create_bank_transfer(payload: BankTransferCreate, db: Session = Depends(get_db)):
    obj = BankTransfer(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/", response_model=list[BankTransferResponse])
def list_bank_transfers(db: Session = Depends(get_db)):
    return db.execute(select(BankTransfer)).scalars().all()


@router.get("/payroll-run/{run_id}", response_model=list[BankTransferResponse])
def get_transfers_by_run(run_id: int, db: Session = Depends(get_db)):
    return db.execute(
        select(BankTransfer).where(BankTransfer.payroll_run_id == run_id)
    ).scalars().all()


@router.get("/{transfer_id}", response_model=BankTransferResponse)
def get_bank_transfer(transfer_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(BankTransfer).where(BankTransfer.id == transfer_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Bank transfer not found")
    return obj


@router.put("/{transfer_id}", response_model=BankTransferResponse)
def update_bank_transfer(
    transfer_id: int, payload: BankTransferUpdate, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(BankTransfer).where(BankTransfer.id == transfer_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Bank transfer not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{transfer_id}/mark-success", response_model=BankTransferResponse)
def mark_transfer_success(
    transfer_id: int, payload: TransferStatusPayload, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(BankTransfer).where(BankTransfer.id == transfer_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Bank transfer not found")
    obj.status = "Success"
    if payload.utr_number:
        obj.utr_number = payload.utr_number
    if payload.remarks:
        obj.remarks = payload.remarks
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{transfer_id}/mark-failed", response_model=BankTransferResponse)
def mark_transfer_failed(
    transfer_id: int, payload: TransferStatusPayload, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(BankTransfer).where(BankTransfer.id == transfer_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Bank transfer not found")
    obj.status = "Failed"
    if payload.remarks:
        obj.remarks = payload.remarks
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bank_transfer(transfer_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(BankTransfer).where(BankTransfer.id == transfer_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Bank transfer not found")
    db.delete(obj)
    db.commit()
