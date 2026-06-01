from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from model.HR_Operations.transfer import Transfer
from schema.HR_Operations.transfer import (
    TransferCreate,
    TransferUpdate,
    TransferResponse,
)

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post("/", response_model=TransferResponse)
def create_transfer(payload: TransferCreate, db: Session = Depends(get_db)):
    record = Transfer(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[TransferResponse])
def list_transfers(db: Session = Depends(get_db)):
    return db.query(Transfer).order_by(Transfer.created_at.desc()).all()


@router.get("/{transfer_id}", response_model=TransferResponse)
def get_transfer(transfer_id: int, db: Session = Depends(get_db)):
    record = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Transfer record not found")
    return record


@router.patch("/{transfer_id}", response_model=TransferResponse)
def update_transfer(transfer_id: int, payload: TransferUpdate, db: Session = Depends(get_db)):
    record = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Transfer record not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{transfer_id}")
def delete_transfer(transfer_id: int, db: Session = Depends(get_db)):
    record = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Transfer record not found")
    db.delete(record)
    db.commit()
    return {"message": "Transfer record deleted successfully"}
