# FILE 9 of 12 | routers/Employee_Management/document_vault.py
# Router: Document Vault — prefix: /documents
# Endpoints: POST /  GET /{employee_id}  GET /detail/{doc_id}  PUT /{doc_id}  PATCH /{doc_id}/verify  DELETE /{doc_id}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from model.Employee_Management.employee_document import EmployeeDocument
from schema.Employee_Management.employee_document import (
    EmployeeDocumentCreate,
    EmployeeDocumentUpdate,
    EmployeeDocumentResponse,
)

router = APIRouter(prefix="/documents", tags=["Employee Management"])


class VerifyRequest(BaseModel):
    verified_by: str


@router.post("/", response_model=EmployeeDocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(payload: EmployeeDocumentCreate, db: Session = Depends(get_db)):
    obj = EmployeeDocument(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{employee_id}", response_model=list[EmployeeDocumentResponse])
def list_employee_documents(employee_id: int, db: Session = Depends(get_db)):
    docs = db.execute(
        select(EmployeeDocument).where(EmployeeDocument.employee_id == employee_id)
    ).scalars().all()
    return docs


@router.get("/detail/{doc_id}", response_model=EmployeeDocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(EmployeeDocument).where(EmployeeDocument.id == doc_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    return obj


@router.put("/{doc_id}", response_model=EmployeeDocumentResponse)
def update_document(doc_id: int, payload: EmployeeDocumentUpdate, db: Session = Depends(get_db)):
    obj = db.execute(
        select(EmployeeDocument).where(EmployeeDocument.id == doc_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{doc_id}/verify", response_model=EmployeeDocumentResponse)
def verify_document(doc_id: int, payload: VerifyRequest, db: Session = Depends(get_db)):
    obj = db.execute(
        select(EmployeeDocument).where(EmployeeDocument.id == doc_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    obj.is_verified = True
    obj.verified_by = payload.verified_by
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    obj = db.execute(
        select(EmployeeDocument).where(EmployeeDocument.id == doc_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(obj)
    db.commit()
