from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.database import get_db
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from model.Forms_Workflows.request import HRRequest
from schema.Forms_Workflows.request import (
    HRRequestCreate,
    HRRequestUpdate,
    HRRequestResponse,
)

router = APIRouter(prefix="/requests", tags=["Forms & Workflows"])


class ResolvePayload(BaseModel):
    response: str


@router.post("/", response_model=HRRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(payload: HRRequestCreate, db: Session = Depends(get_db)):
    req = HRRequest(**payload.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/", response_model=list[HRRequestResponse])
def list_requests(
    status: Optional[str] = Query(None),
    request_type: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(HRRequest)
    if status:
        query = query.where(HRRequest.status == status)
    if request_type:
        query = query.where(HRRequest.request_type == request_type)
    if employee_id:
        query = query.where(HRRequest.employee_id == employee_id)
    return db.execute(query).scalars().all()


@router.get("/employee/{employee_id}", response_model=list[HRRequestResponse])
def requests_by_employee(employee_id: int, db: Session = Depends(get_db)):
    return db.execute(
        select(HRRequest).where(HRRequest.employee_id == employee_id)
    ).scalars().all()


@router.get("/{request_id}", response_model=HRRequestResponse)
def get_request(request_id: int, db: Session = Depends(get_db)):
    req = db.execute(select(HRRequest).where(HRRequest.id == request_id)).scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="HR request not found")
    return req


@router.put("/{request_id}", response_model=HRRequestResponse)
def update_request(request_id: int, payload: HRRequestUpdate, db: Session = Depends(get_db)):
    req = db.execute(select(HRRequest).where(HRRequest.id == request_id)).scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="HR request not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(req, field, value)
    req.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    return req


@router.patch("/{request_id}/resolve", response_model=HRRequestResponse)
def resolve_request(request_id: int, payload: ResolvePayload, db: Session = Depends(get_db)):
    req = db.execute(select(HRRequest).where(HRRequest.id == request_id)).scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="HR request not found")
    req.status = "Resolved"
    req.response = payload.response
    req.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    return req


@router.patch("/{request_id}/close", response_model=HRRequestResponse)
def close_request(request_id: int, db: Session = Depends(get_db)):
    req = db.execute(select(HRRequest).where(HRRequest.id == request_id)).scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="HR request not found")
    req.status = "Closed"
    req.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    return req


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(request_id: int, db: Session = Depends(get_db)):
    req = db.execute(select(HRRequest).where(HRRequest.id == request_id)).scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="HR request not found")
    db.delete(req)
    db.commit()
