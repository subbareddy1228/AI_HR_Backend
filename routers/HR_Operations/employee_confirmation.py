from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from core.database import get_db
from model.HR_Operations.hr_helpdesk import HRHelpdesk
from schema.HR_Operations.hr_helpdesk import (
    HRHelpdeskCreate,
    HRHelpdeskUpdate,
    HRHelpdeskResponse,
)

router = APIRouter(
    prefix="/api/hr-operations/helpdesk",
    tags=["HR Operations - HR Helpdesk"],
)


# ──────────────────────────────────────────────
# CREATE Ticket
# ──────────────────────────────────────────────
@router.post("/", response_model=HRHelpdeskResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: HRHelpdeskCreate, db: Session = Depends(get_db)):
    """Raise a helpdesk ticket for an employee."""
    valid_categories = {"PAYROLL", "LEAVE", "POLICY", "ONBOARDING", "OTHER"}
    if payload.category.upper() not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Allowed: {valid_categories}",
        )

    valid_priorities = {"LOW", "MEDIUM", "HIGH", "URGENT"}
    if payload.priority and payload.priority.upper() not in valid_priorities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid priority. Allowed: {valid_priorities}",
        )

    ticket = HRHelpdesk(**payload.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


# ──────────────────────────────────────────────
# LIST ALL Tickets
# ──────────────────────────────────────────────
@router.get("/", response_model=List[HRHelpdeskResponse])
def list_tickets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Retrieve all helpdesk tickets, newest first."""
    tickets = (
        db.query(HRHelpdesk)
        .order_by(HRHelpdesk.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return tickets


# ──────────────────────────────────────────────
# GET Tickets by Employee ID
# ──────────────────────────────────────────────
@router.get("/employee/{employee_id}", response_model=List[HRHelpdeskResponse])
def get_tickets_by_employee(employee_id: int, db: Session = Depends(get_db)):
    """Retrieve all tickets raised by a specific employee."""
    tickets = (
        db.query(HRHelpdesk)
        .filter(HRHelpdesk.employee_id == employee_id)
        .order_by(HRHelpdesk.created_at.desc())
        .all()
    )
    return tickets


# ──────────────────────────────────────────────
# GET Open / Pending Tickets (for HR dashboard)
# ──────────────────────────────────────────────
@router.get("/open", response_model=List[HRHelpdeskResponse])
def get_open_tickets(db: Session = Depends(get_db)):
    """Retrieve all tickets with OPEN or IN_PROGRESS status."""
    tickets = (
        db.query(HRHelpdesk)
        .filter(HRHelpdesk.status.in_(["OPEN", "IN_PROGRESS"]))
        .order_by(HRHelpdesk.created_at.asc())
        .all()
    )
    return tickets


# ──────────────────────────────────────────────
# GET Ticket by ID
# ──────────────────────────────────────────────
@router.get("/{ticket_id}", response_model=HRHelpdeskResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Retrieve a single helpdesk ticket by ID."""
    ticket = db.query(HRHelpdesk).filter(HRHelpdesk.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


# ──────────────────────────────────────────────
# UPDATE Ticket (assign / resolve / close)
# ──────────────────────────────────────────────
@router.patch("/{ticket_id}", response_model=HRHelpdeskResponse)
def update_ticket(
    ticket_id: int,
    payload: HRHelpdeskUpdate,
    db: Session = Depends(get_db),
):
    """Update ticket status, assignee, priority or resolution."""
    ticket = db.query(HRHelpdesk).filter(HRHelpdesk.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    valid_statuses = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}
    if payload.status and payload.status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {valid_statuses}",
        )

    valid_priorities = {"LOW", "MEDIUM", "HIGH", "URGENT"}
    if payload.priority and payload.priority.upper() not in valid_priorities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid priority. Allowed: {valid_priorities}",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)

    # Auto-set resolved_at when status changes to RESOLVED
    if payload.status and payload.status.upper() == "RESOLVED" and not ticket.resolved_at:
        ticket.resolved_at = datetime.utcnow()

    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return ticket


# ──────────────────────────────────────────────
# DELETE Ticket
# ──────────────────────────────────────────────
@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Delete a helpdesk ticket (only if OPEN)."""
    ticket = db.query(HRHelpdesk).filter(HRHelpdesk.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status != "OPEN":
        raise HTTPException(
            status_code=400,
            detail="Only OPEN tickets can be deleted",
        )
    db.delete(ticket)
    db.commit()