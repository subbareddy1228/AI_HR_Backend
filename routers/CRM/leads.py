# routers/leads.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlmodel import Session

from schema.lead import LeadCreate, LeadRead, LeadUpdate
import crud_ops
from core.database import get_db

router = APIRouter()


@router.get("/", response_model=List[LeadRead])
def read_leads(
    skip: int = 0,
    limit: int = Query(100, le=1000),
    status: str | None = Query(default=None),
    company: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    session: Session = Depends(get_db)
):
    return crud_ops.get_leads(
        session,
        skip=skip,
        limit=limit,
        status=status,
        company=company,
        owner=owner,
    )


@router.get("/{lead_id}", response_model=LeadRead)
def read_lead(lead_id: int, session: Session = Depends(get_db)):
    lead = crud_ops.get_lead(session, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.post("/", response_model=LeadRead, status_code=201)
def create_lead(lead_in: LeadCreate, session: Session = Depends(get_db)):
    return crud_ops.create_lead(session, lead_in)


@router.put("/{lead_id}", response_model=LeadRead)
def update_lead(lead_id: int, lead_in: LeadUpdate, session: Session = Depends(get_db)):
    lead = crud_ops.update_lead(session, lead_id, lead_in)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, session: Session = Depends(get_db)):
    if not crud_ops.delete_lead(session, lead_id):
        raise HTTPException(404, "Lead not found")
