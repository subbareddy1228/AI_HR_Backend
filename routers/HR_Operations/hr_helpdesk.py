from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter(prefix="/helpdesk", tags=["HR Helpdesk"])


@router.post("/", response_model=HRHelpdeskResponse)
def create_ticket(payload: HRHelpdeskCreate, db: Session = Depends(get_db)):
    record = HRHelpdesk(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[HRHelpdeskResponse])
def list_tickets(db: Session = Depends(get_db)):
    return db.query(HRHelpdesk).order_by(HRHelpdesk.created_at.desc()).all()


@router.get("/{ticket_id}", response_model=HRHelpdeskResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    record = db.query(HRHelpdesk).filter(HRHelpdesk.id == ticket_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return record


@router.patch("/{ticket_id}", response_model=HRHelpdeskResponse)
def update_ticket(ticket_id: int, payload: HRHelpdeskUpdate, db: Session = Depends(get_db)):
    record = db.query(HRHelpdesk).filter(HRHelpdesk.id == ticket_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Ticket not found")
    updates = payload.model_dump(exclude_unset=True)
    # Auto-set resolved_at when status moves to RESOLVED
    if updates.get("status") == "RESOLVED" and not record.resolved_at:
        updates["resolved_at"] = datetime.utcnow()
    for key, value in updates.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    record = db.query(HRHelpdesk).filter(HRHelpdesk.id == ticket_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.delete(record)
    db.commit()
    return {"message": "Ticket deleted successfully"}
