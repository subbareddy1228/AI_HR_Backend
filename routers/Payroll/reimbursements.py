from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from core.database import get_db
from model.Payroll.reimbursement import Reimbursement
from schema.Payroll.reimbursement import ReimbursementCreate, ReimbursementUpdate, ReimbursementResponse

from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/reimbursements", tags=["Payroll"])


class ApprovalPayload(BaseModel):
    approved_by: Optional[str] = None
    remarks: Optional[str] = None


@router.post("/", response_model=ReimbursementResponse, status_code=status.HTTP_201_CREATED)
def create_reimbursement(payload: ReimbursementCreate, db: Session = Depends(get_db)):
    obj = Reimbursement(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/", response_model=list[ReimbursementResponse])
def list_reimbursements(db: Session = Depends(get_db)):
    return db.execute(select(Reimbursement)).scalars().all()


@router.get("/employee/{employee_id}", response_model=list[ReimbursementResponse])
def get_reimbursements_by_employee(employee_id: int, db: Session = Depends(get_db)):
    return db.execute(
        select(Reimbursement).where(Reimbursement.employee_id == employee_id)
    ).scalars().all()


@router.get("/{reimbursement_id}", response_model=ReimbursementResponse)
def get_reimbursement(reimbursement_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(Reimbursement).where(Reimbursement.id == reimbursement_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Reimbursement not found")
    return obj


@router.put("/{reimbursement_id}", response_model=ReimbursementResponse)
def update_reimbursement(
    reimbursement_id: int, payload: ReimbursementUpdate, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(Reimbursement).where(Reimbursement.id == reimbursement_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Reimbursement not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{reimbursement_id}/approve", response_model=ReimbursementResponse)
def approve_reimbursement(
    reimbursement_id: int, payload: ApprovalPayload, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(Reimbursement).where(Reimbursement.id == reimbursement_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Reimbursement not found")
    obj.status = "Approved"
    if payload.approved_by:
        obj.approved_by = payload.approved_by
    if payload.remarks:
        obj.remarks = payload.remarks
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{reimbursement_id}/reject", response_model=ReimbursementResponse)
def reject_reimbursement(
    reimbursement_id: int, payload: ApprovalPayload, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(Reimbursement).where(Reimbursement.id == reimbursement_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Reimbursement not found")
    obj.status = "Rejected"
    if payload.approved_by:
        obj.approved_by = payload.approved_by
    if payload.remarks:
        obj.remarks = payload.remarks
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{reimbursement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reimbursement(reimbursement_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(Reimbursement).where(Reimbursement.id == reimbursement_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Reimbursement not found")
    db.delete(obj)
    db.commit()


@router.get("/receipts/{reimbursement_id}/download")
def download_receipt(reimbursement_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        select(Reimbursement).where(Reimbursement.id == reimbursement_id)
    )
    reimbursement = result.scalars().first()

    if not reimbursement:
        raise HTTPException(status_code=404, detail="Reimbursement not found")

    if not reimbursement.receipt_path:
        raise HTTPException(status_code=404, detail="No receipt file found for this claim")

    if not os.path.exists(reimbursement.receipt_path):
        raise HTTPException(status_code=404, detail="Receipt file not found on disk")

    return FileResponse(
        path=reimbursement.receipt_path,
        filename=os.path.basename(reimbursement.receipt_path),
        media_type="application/octet-stream"
    )
