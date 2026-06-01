from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from model.HR_Operations.exit_management import ExitManagement
from schema.HR_Operations.exit_management import (
    ExitManagementCreate,
    ExitManagementUpdate,
    ExitManagementResponse,
)

router = APIRouter(prefix="/exit-management", tags=["Exit Management"])


@router.post("/", response_model=ExitManagementResponse)
def create_exit(payload: ExitManagementCreate, db: Session = Depends(get_db)):
    record = ExitManagement(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[ExitManagementResponse])
def list_exits(db: Session = Depends(get_db)):
    return db.query(ExitManagement).order_by(ExitManagement.created_at.desc()).all()


@router.get("/{exit_id}", response_model=ExitManagementResponse)
def get_exit(exit_id: int, db: Session = Depends(get_db)):
    record = db.query(ExitManagement).filter(ExitManagement.id == exit_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Exit record not found")
    return record


@router.patch("/{exit_id}", response_model=ExitManagementResponse)
def update_exit(exit_id: int, payload: ExitManagementUpdate, db: Session = Depends(get_db)):
    record = db.query(ExitManagement).filter(ExitManagement.id == exit_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Exit record not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{exit_id}")
def delete_exit(exit_id: int, db: Session = Depends(get_db)):
    record = db.query(ExitManagement).filter(ExitManagement.id == exit_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Exit record not found")
    db.delete(record)
    db.commit()
    return {"message": "Exit record deleted successfully"}
