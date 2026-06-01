# FILE 17 of 18 | routers/Payroll/final_settlement.py
# Router: Final Settlement — prefix: /final-settlements  (mounted under /api/payroll in main.py)
# Endpoints:
#   POST   /final-settlements/                         — create
#   GET    /final-settlements/                         — list all
#   GET    /final-settlements/employee/{employee_id}   — by employee
#   GET    /final-settlements/{id}                     — get one
#   PUT    /final-settlements/{id}                     — update
#   DELETE /final-settlements/{id}                     — delete
#   PATCH  /final-settlements/{id}/approve             — set status Approved
#   PATCH  /final-settlements/{id}/mark-paid           — set status Paid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from core.database import get_db
from model.Payroll.final_settlement import FinalSettlement
from schema.Payroll.final_settlement import (
    FinalSettlementCreate,
    FinalSettlementUpdate,
    FinalSettlementResponse,
)

router = APIRouter(prefix="/final-settlements", tags=["Payroll"])


class SettlementApprovalPayload(BaseModel):
    approved_by: Optional[str] = None
    remarks: Optional[str] = None


@router.post("/", response_model=FinalSettlementResponse, status_code=status.HTTP_201_CREATED)
def create_final_settlement(payload: FinalSettlementCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(FinalSettlement).where(FinalSettlement.employee_id == payload.employee_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Final settlement already exists for employee_id {payload.employee_id}",
        )
    obj = FinalSettlement(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/", response_model=list[FinalSettlementResponse])
def list_final_settlements(db: Session = Depends(get_db)):
    return db.execute(select(FinalSettlement)).scalars().all()


@router.get("/employee/{employee_id}", response_model=FinalSettlementResponse)
def get_settlement_by_employee(employee_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(FinalSettlement).where(FinalSettlement.employee_id == employee_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Final settlement not found for this employee")
    return obj


@router.get("/{settlement_id}", response_model=FinalSettlementResponse)
def get_final_settlement(settlement_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(FinalSettlement).where(FinalSettlement.id == settlement_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Final settlement not found")
    return obj


@router.put("/{settlement_id}", response_model=FinalSettlementResponse)
def update_final_settlement(
    settlement_id: int, payload: FinalSettlementUpdate, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(FinalSettlement).where(FinalSettlement.id == settlement_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Final settlement not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{settlement_id}/approve", response_model=FinalSettlementResponse)
def approve_final_settlement(
    settlement_id: int, payload: SettlementApprovalPayload, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(FinalSettlement).where(FinalSettlement.id == settlement_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Final settlement not found")
    obj.settlement_status = "Approved"
    if payload.approved_by:
        obj.approved_by = payload.approved_by
    if payload.remarks:
        obj.remarks = payload.remarks
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{settlement_id}/mark-paid", response_model=FinalSettlementResponse)
def mark_settlement_paid(
    settlement_id: int, payload: SettlementApprovalPayload, db: Session = Depends(get_db)
):
    obj = db.execute(
        select(FinalSettlement).where(FinalSettlement.id == settlement_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Final settlement not found")
    obj.settlement_status = "Paid"
    if payload.remarks:
        obj.remarks = payload.remarks
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{settlement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_final_settlement(settlement_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(FinalSettlement).where(FinalSettlement.id == settlement_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Final settlement not found")
    db.delete(obj)
    db.commit()
