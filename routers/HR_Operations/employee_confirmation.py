from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from core.database import get_db
from model.HR_Operations.employee_confirmation import EmployeeConfirmation
from schema.HR_Operations.employee_confirmation import (
    EmployeeConfirmationCreate,
    EmployeeConfirmationUpdate,
    EmployeeConfirmationResponse,
)

router = APIRouter(
    prefix="/api/hr-operations/employee-confirmations",
    tags=["HR Operations - Employee Confirmation"],
)


# ──────────────────────────────────────────────
# CREATE Employee Confirmation (start probation)
# ──────────────────────────────────────────────
@router.post("/", response_model=EmployeeConfirmationResponse, status_code=status.HTTP_201_CREATED)
def create_confirmation(payload: EmployeeConfirmationCreate, db: Session = Depends(get_db)):
    """Create a probation / confirmation record for an employee."""
    if payload.probation_end_date <= payload.probation_start_date:
        raise HTTPException(
            status_code=400,
            detail="probation_end_date must be after probation_start_date",
        )

    # Prevent duplicate active confirmation for same employee
    existing = (
        db.query(EmployeeConfirmation)
        .filter(
            EmployeeConfirmation.employee_id == payload.employee_id,
            EmployeeConfirmation.status == "PENDING",
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An active probation record already exists for this employee",
        )

    confirmation = EmployeeConfirmation(**payload.model_dump())
    db.add(confirmation)
    db.commit()
    db.refresh(confirmation)
    return confirmation


# ──────────────────────────────────────────────
# LIST ALL Confirmations
# ──────────────────────────────────────────────
@router.get("/", response_model=List[EmployeeConfirmationResponse])
def list_confirmations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Retrieve all employee confirmation records, newest first."""
    records = (
        db.query(EmployeeConfirmation)
        .order_by(EmployeeConfirmation.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return records


# ──────────────────────────────────────────────
# GET Confirmation by Employee ID
# ──────────────────────────────────────────────
@router.get("/employee/{employee_id}", response_model=List[EmployeeConfirmationResponse])
def get_by_employee(employee_id: int, db: Session = Depends(get_db)):
    """Retrieve all confirmation records for a specific employee."""
    records = (
        db.query(EmployeeConfirmation)
        .filter(EmployeeConfirmation.employee_id == employee_id)
        .order_by(EmployeeConfirmation.created_at.desc())
        .all()
    )
    return records


# ──────────────────────────────────────────────
# GET Confirmation by ID
# ──────────────────────────────────────────────
@router.get("/{confirmation_id}", response_model=EmployeeConfirmationResponse)
def get_confirmation(confirmation_id: int, db: Session = Depends(get_db)):
    """Retrieve a single confirmation record by ID."""
    record = (
        db.query(EmployeeConfirmation)
        .filter(EmployeeConfirmation.id == confirmation_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Confirmation record not found")
    return record


# ──────────────────────────────────────────────
# UPDATE Confirmation (confirm / extend / terminate)
# ──────────────────────────────────────────────
@router.patch("/{confirmation_id}", response_model=EmployeeConfirmationResponse)
def update_confirmation(
    confirmation_id: int,
    payload: EmployeeConfirmationUpdate,
    db: Session = Depends(get_db),
):
    """Update confirmation status, rating, extended date or remarks."""
    record = (
        db.query(EmployeeConfirmation)
        .filter(EmployeeConfirmation.id == confirmation_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Confirmation record not found")

    valid_statuses = {"PENDING", "CONFIRMED", "EXTENDED", "TERMINATED"}
    if payload.status and payload.status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {valid_statuses}",
        )

    valid_ratings = {"EXCELLENT", "GOOD", "SATISFACTORY", "POOR"}
    if payload.performance_rating and payload.performance_rating.upper() not in valid_ratings:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid performance_rating. Allowed: {valid_ratings}",
        )

    # If status is EXTENDED, extended_till is required
    if payload.status == "EXTENDED" and not payload.extended_till:
        raise HTTPException(
            status_code=400,
            detail="extended_till date is required when status is EXTENDED",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)

    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


# ──────────────────────────────────────────────
# DELETE Confirmation
# ──────────────────────────────────────────────
@router.delete("/{confirmation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_confirmation(confirmation_id: int, db: Session = Depends(get_db)):
    """Delete a confirmation record (only if still PENDING)."""
    record = (
        db.query(EmployeeConfirmation)
        .filter(EmployeeConfirmation.id == confirmation_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Confirmation record not found")
    if record.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Only PENDING confirmation records can be deleted",
        )
    db.delete(record)
    db.commit()