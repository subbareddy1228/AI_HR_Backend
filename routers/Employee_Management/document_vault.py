from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from schema.Employee_Management.employee_document import (
    EmployeeDocumentCreate,
    EmployeeDocumentUpdate,
    EmployeeDocumentResponse,
    VerifyRequest,
)
from services.Employee_Management.employee_document_service import (
    upload_document,
    list_employee_documents,
    get_document,
    update_document,
    verify_document,
    delete_document,
)

router = APIRouter(prefix="/documents", tags=["Employee Management"])


@router.post("/", response_model=EmployeeDocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document_route(payload: EmployeeDocumentCreate, db: Session = Depends(get_db)):
    return upload_document(db, payload)


@router.get("/{employee_id}", response_model=list[EmployeeDocumentResponse])
def list_employee_documents_route(employee_id: int, db: Session = Depends(get_db)):
    return list_employee_documents(db, employee_id)


@router.get("/detail/{doc_id}", response_model=EmployeeDocumentResponse)
def get_document_route(doc_id: int, db: Session = Depends(get_db)):
    return get_document(db, doc_id)


@router.put("/{doc_id}", response_model=EmployeeDocumentResponse)
def update_document_route(doc_id: int, payload: EmployeeDocumentUpdate, db: Session = Depends(get_db)):
    return update_document(db, doc_id, payload)


@router.patch("/{doc_id}/verify", response_model=EmployeeDocumentResponse)
def verify_document_route(doc_id: int, payload: VerifyRequest, db: Session = Depends(get_db)):
    return verify_document(db, doc_id, payload.verified_by)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_route(doc_id: int, db: Session = Depends(get_db)):
    delete_document(db, doc_id)