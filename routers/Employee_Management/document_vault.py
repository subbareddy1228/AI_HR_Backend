
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from schema.Employee_Management.employee_document import (
    EmployeeDocumentCreate,
    EmployeeDocumentUpdate,
    EmployeeDocumentResponse,
    BulkUploadRequest,
    BulkUploadResponse,
    ReviewRequest,
    VerifyRequest,
    DocumentVaultStats,
    EmployeeChecklist,
    DocumentFilter,
    DocumentCategory,
    DocumentStatus,
)
from services.Employee_Management.employee_document_service import (
    upload_document,
    bulk_upload_documents,
    list_all_documents,
    list_employee_documents,
    get_document,
    update_document,
    bump_version,
    review_document,
    verify_document,
    delete_document,
    get_vault_stats,
    get_employee_checklist,
)

router = APIRouter(prefix="/documents", tags=["Document Vault"])



@router.get("/stats", response_model=DocumentVaultStats)
def vault_stats(db: Session = Depends(get_db)):
   
    return get_vault_stats(db)


@router.get("/checklist/{employee_id}", response_model=EmployeeChecklist)
def employee_checklist(employee_id: int, db: Session = Depends(get_db)):
   
    return get_employee_checklist(db, employee_id)


@router.post("/", response_model=EmployeeDocumentResponse, status_code=201)
def upload_document_route(
    payload: EmployeeDocumentCreate,
    db: Session = Depends(get_db),
):
    
    return upload_document(db, payload)


@router.post("/bulk-upload", response_model=BulkUploadResponse)
def bulk_upload_route(
    payload: BulkUploadRequest,
    db: Session = Depends(get_db),
):
    
    return bulk_upload_documents(db, payload)

@router.get("/", response_model=List[EmployeeDocumentResponse])
def list_documents(
    category     : Optional[DocumentCategory] = Query(None, description="All Categories dropdown"),
    status       : Optional[DocumentStatus]   = Query(None, description="All Status dropdown"),
    employee_type: Optional[str]              = Query(None, description="All Employee Types dropdown"),
    search       : Optional[str]              = Query(None, description="Search by name / type / employee"),
    db           : Session                    = Depends(get_db),
):
    
    filters = DocumentFilter(
        category=category,
        status=status,
        employee_type=employee_type,
        search=search,
    )
    return list_all_documents(db, filters)


@router.get("/employee/{employee_id}", response_model=List[EmployeeDocumentResponse])
def list_by_employee(employee_id: int, db: Session = Depends(get_db)):
   
    return list_employee_documents(db, employee_id)


@router.get("/detail/{doc_id}", response_model=EmployeeDocumentResponse)
def get_document_route(doc_id: int, db: Session = Depends(get_db)):
   
    return get_document(db, doc_id)


@router.patch("/{doc_id}", response_model=EmployeeDocumentResponse)
def update_document_route(
    doc_id : int,
    payload: EmployeeDocumentUpdate,
    db     : Session = Depends(get_db),
):
    
    return update_document(db, doc_id, payload)


@router.post("/{doc_id}/new-version", response_model=EmployeeDocumentResponse)
def new_version_route(
    doc_id      : int,
    file_path   : str = Body(..., embed=True),
    version_notes: Optional[str] = Body(None, embed=True),
    db          : Session = Depends(get_db),
):
    
    return bump_version(db, doc_id, file_path, version_notes)


@router.patch("/{doc_id}/review", response_model=EmployeeDocumentResponse)
def review_document_route(
    doc_id : int,
    payload: ReviewRequest,
    db     : Session = Depends(get_db),
):
    
    return review_document(db, doc_id, payload)


@router.patch("/{doc_id}/verify", response_model=EmployeeDocumentResponse)
def verify_document_route(
    doc_id : int,
    payload: VerifyRequest,
    db     : Session = Depends(get_db),
):
    
    return verify_document(db, doc_id, payload.verified_by)


@router.get("/{doc_id}/download")
def download_document_route(doc_id: int, db: Session = Depends(get_db)):
   
    doc = get_document(db, doc_id)
    return {"doc_id": doc.id, "file_path": doc.file_path, "file_format": doc.file_format}


@router.delete("/{doc_id}", status_code=204)
def delete_document_route(doc_id: int, db: Session = Depends(get_db)):
    
    delete_document(db, doc_id)
