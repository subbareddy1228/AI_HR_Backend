from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from model.HR_Operations.employee_confirmation import EmployeeConfirmation
from schema.HR_Operations.employee_confirmation import (
    EmployeeConfirmationCreate,
    EmployeeConfirmationUpdate,
    EmployeeConfirmationResponse,
)

router = APIRouter(prefix="/confirmations", tags=["Employee Confirmations"])


@router.post("/", response_model=EmployeeConfirmationResponse)
def create_confirmation(payload: EmployeeConfirmationCreate, db: Session = Depends(get_db)):
    record = EmployeeConfirmation(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[EmployeeConfirmationResponse])
def list_confirmations(db: Session = Depends(get_db)):
    return db.query(EmployeeConfirmation).order_by(EmployeeConfirmation.created_at.desc()).all()


@router.get("/{confirmation_id}", response_model=EmployeeConfirmationResponse)
def get_confirmation(confirmation_id: int, db: Session = Depends(get_db)):
    record = db.query(EmployeeConfirmation).filter(EmployeeConfirmation.id == confirmation_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Confirmation record not found")
    return record


@router.patch("/{confirmation_id}", response_model=EmployeeConfirmationResponse)
def update_confirmation(confirmation_id: int, payload: EmployeeConfirmationUpdate, db: Session = Depends(get_db)):
    record = db.query(EmployeeConfirmation).filter(EmployeeConfirmation.id == confirmation_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Confirmation record not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{confirmation_id}")
def delete_confirmation(confirmation_id: int, db: Session = Depends(get_db)):
    record = db.query(EmployeeConfirmation).filter(EmployeeConfirmation.id == confirmation_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Confirmation record not found")
    db.delete(record)
    db.commit()
    return {"message": "Confirmation record deleted successfully"}
