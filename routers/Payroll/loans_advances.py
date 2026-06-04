from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from model.Payroll.loan_advance import LoanAdvance
from schema.Payroll.loan_advance import (
    LoanAdvanceCreate,
    LoanAdvanceUpdate,
    LoanAdvanceResponse
)

router = APIRouter(
    prefix="/loans",
    tags=["Loans & Advances"]
)


# Create loan
@router.post(
    "/",
    response_model=LoanAdvanceResponse,
    status_code=status.HTTP_201_CREATED
)
def create_loan(
    payload: LoanAdvanceCreate,
    db: Session = Depends(get_db)
):
    loan = LoanAdvance(
        **payload.model_dump()
    )

    db.add(loan)
    db.commit()
    db.refresh(loan)

    return loan


# Get all loans
@router.get(
    "/",
    response_model=List[LoanAdvanceResponse]
)
def get_all_loans(
    db: Session = Depends(get_db)
):
    loans = (
        db.query(LoanAdvance)
        .all()
    )

    return loans


# Get loan by ID
@router.get(
    "/{loan_id}",
    response_model=LoanAdvanceResponse
)
def get_loan(
    loan_id: int,
    db: Session = Depends(get_db)
):
    loan = (
        db.query(LoanAdvance)
        .filter(
            LoanAdvance.id == loan_id
        )
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail="Loan not found"
        )

    return loan


# Update loan
@router.put(
    "/{loan_id}",
    response_model=LoanAdvanceResponse
)
def update_loan(
    loan_id: int,
    payload: LoanAdvanceUpdate,
    db: Session = Depends(get_db)
):
    loan = (
        db.query(LoanAdvance)
        .filter(
            LoanAdvance.id == loan_id
        )
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail="Loan not found"
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(loan, key, value)

    db.commit()
    db.refresh(loan)

    return loan


# Delete loan
@router.delete("/{loan_id}")
def delete_loan(
    loan_id: int,
    db: Session = Depends(get_db)
):
    loan = (
        db.query(LoanAdvance)
        .filter(
            LoanAdvance.id == loan_id
        )
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail="Loan not found"
        )

    db.delete(loan)
    db.commit()

    return {
        "message":
        "Loan deleted successfully"
    }


# Approve loan
@router.put("/{loan_id}/approve")
def approve_loan(
    loan_id: int,
    db: Session = Depends(get_db)
):
    loan = (
        db.query(LoanAdvance)
        .filter(
            LoanAdvance.id == loan_id
        )
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail="Loan not found"
        )

    loan.status = "APPROVED"

    db.commit()
    db.refresh(loan)

    return {
        "message":
        "Loan approved successfully"
    }


# Reject loan
@router.put("/{loan_id}/reject")
def reject_loan(
    loan_id: int,
    db: Session = Depends(get_db)
):
    loan = (
        db.query(LoanAdvance)
        .filter(
            LoanAdvance.id == loan_id
        )
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail="Loan not found"
        )

    loan.status = "REJECTED"

    db.commit()
    db.refresh(loan)

    return {
        "message":
        "Loan rejected successfully"
    }


# Employee loan history
@router.get(
    "/employee/{employee_id}",
    response_model=List[LoanAdvanceResponse]
)
def employee_loans(
    employee_id: int,
    db: Session = Depends(get_db)
):
    loans = (
        db.query(LoanAdvance)
        .filter(
            LoanAdvance.employee_id ==
            employee_id
        )
        .all()
    )

    return loans


# Filter loans
@router.get("/filter")
def filter_loans(
    status: Optional[str] = None,
    loan_type: Optional[str] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(LoanAdvance)

    if status:
        query = query.filter(
            LoanAdvance.status == status
        )

    if loan_type:
        query = query.filter(
            LoanAdvance.loan_type ==
            loan_type
        )

    if employee_id:
        query = query.filter(
            LoanAdvance.employee_id ==
            employee_id
        )

    return query.all()


# Loan reports
@router.get("/reports")
def loan_reports(
    db: Session = Depends(get_db)
):
    loans = (
        db.query(LoanAdvance)
        .all()
    )

    total_loans = len(loans)

    approved = len([
        l for l in loans
        if l.status == "APPROVED"
    ])

    rejected = len([
        l for l in loans
        if l.status == "REJECTED"
    ])

    pending = len([
        l for l in loans
        if l.status == "PENDING"
    ])

    total_amount = sum([
        l.amount for l in loans
    ])

    return {
        "total_loans": total_loans,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "total_amount": total_amount
    }


# EMI details
@router.get("/{loan_id}/emi")
def emi_details(
    loan_id: int,
    db: Session = Depends(get_db)
):
    loan = (
        db.query(LoanAdvance)
        .filter(
            LoanAdvance.id == loan_id
        )
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail="Loan not found"
        )

    remaining_installments = (
        loan.total_installments -
        loan.paid_installments
    )

    remaining_amount = (
        remaining_installments *
        loan.emi_amount
    )

    return {
        "loan_id": loan.id,
        "emi_amount": loan.emi_amount,
        "total_installments":
        loan.total_installments,
        "paid_installments":
        loan.paid_installments,
        "remaining_installments":
        remaining_installments,
        "remaining_amount":
        remaining_amount
    }
