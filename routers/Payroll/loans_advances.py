# FILE 14 of 18 | routers/Payroll/loans_advances.py
# Router: Loans & Advances — prefix: /loans  (mounted under /api/payroll in main.py)
# Endpoints:
#   POST   /loans/                      — create
#   GET    /loans/                      — list all
#   GET    /loans/employee/{employee_id} — by employee
#   GET    /loans/{id}                  — get one
#   PUT    /loans/{id}                  — update
#   DELETE /loans/{id}                  — delete
#   PATCH  /loans/{id}/approve          — set status Approved + Active
#   PATCH  /loans/{id}/reject           — set status Rejected

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
from decimal import Decimal
from datetime import date

from core.database import get_db
from model.Payroll.loan_advance import LoanAdvance
from schema.Payroll.loan_advance import LoanAdvanceCreate, LoanAdvanceUpdate, LoanAdvanceResponse

router = APIRouter(prefix="/loans", tags=["Payroll"])


class LoanApprovalPayload(BaseModel):
    approved_by: Optional[str] = None
    approved_amount: Optional[Decimal] = None
    emi_amount: Optional[Decimal] = None
    total_installments: Optional[int] = None
    start_date: Optional[date] = None


class LoanRejectPayload(BaseModel):
    approved_by: Optional[str] = None
    reason: Optional[str] = None


@router.post("/", response_model=LoanAdvanceResponse, status_code=status.HTTP_201_CREATED)
def create_loan(payload: LoanAdvanceCreate, db: Session = Depends(get_db)):
    obj = LoanAdvance(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/", response_model=list[LoanAdvanceResponse])
def list_loans(db: Session = Depends(get_db)):
    return db.execute(select(LoanAdvance)).scalars().all()


@router.get("/employee/{employee_id}", response_model=list[LoanAdvanceResponse])
def get_loans_by_employee(employee_id: int, db: Session = Depends(get_db)):
    return db.execute(
        select(LoanAdvance).where(LoanAdvance.employee_id == employee_id)
    ).scalars().all()


@router.get("/{loan_id}", response_model=LoanAdvanceResponse)
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    obj = db.execute(select(LoanAdvance).where(LoanAdvance.id == loan_id)).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Loan/advance not found")
    return obj


@router.put("/{loan_id}", response_model=LoanAdvanceResponse)
def update_loan(loan_id: int, payload: LoanAdvanceUpdate, db: Session = Depends(get_db)):
    obj = db.execute(select(LoanAdvance).where(LoanAdvance.id == loan_id)).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Loan/advance not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{loan_id}/approve", response_model=LoanAdvanceResponse)
def approve_loan(loan_id: int, payload: LoanApprovalPayload, db: Session = Depends(get_db)):
    obj = db.execute(select(LoanAdvance).where(LoanAdvance.id == loan_id)).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Loan/advance not found")
    obj.status = "Active"
    if payload.approved_by:
        obj.approved_by = payload.approved_by
    if payload.approved_amount is not None:
        obj.approved_amount = payload.approved_amount
    if payload.emi_amount is not None:
        obj.emi_amount = payload.emi_amount
    if payload.total_installments is not None:
        obj.total_installments = payload.total_installments
    if payload.start_date is not None:
        obj.start_date = payload.start_date
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{loan_id}/reject", response_model=LoanAdvanceResponse)
def reject_loan(loan_id: int, payload: LoanRejectPayload, db: Session = Depends(get_db)):
    obj = db.execute(select(LoanAdvance).where(LoanAdvance.id == loan_id)).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Loan/advance not found")
    obj.status = "Rejected"
    if payload.approved_by:
        obj.approved_by = payload.approved_by
    if payload.reason:
        obj.reason = payload.reason
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_loan(loan_id: int, db: Session = Depends(get_db)):
    obj = db.execute(select(LoanAdvance).where(LoanAdvance.id == loan_id)).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Loan/advance not found")
    db.delete(obj)
    db.commit()
