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


# ─────────────────────────────────────────────────────────────────────────────
# Stats — drives the 4 summary cards at the top of the page
# GET /api/employees/documents/stats
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=DocumentVaultStats)
def vault_stats(db: Session = Depends(get_db)):
    """
    Returns totals for the 4 header cards:
    - Total Documents
    - Approved
    - Pending Review
    - Expiring Soon (next 30 days)
    """
    return get_vault_stats(db)


# ─────────────────────────────────────────────────────────────────────────────
# Checklist view
# GET /api/employees/documents/checklist/{employee_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/checklist/{employee_id}", response_model=EmployeeChecklist)
def employee_checklist(employee_id: int, db: Session = Depends(get_db)):
    """
    Returns the Checklist View for an employee:
    - Required document types vs uploaded docs
    - Status per item: APPROVED | PENDING | REJECTED | MISSING
    - Counts: completed, pending, missing
    """
    return get_employee_checklist(db, employee_id)


# ─────────────────────────────────────────────────────────────────────────────
# Upload
# POST /api/employees/documents/
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/", response_model=EmployeeDocumentResponse, status_code=201)
def upload_document_route(
    payload: EmployeeDocumentCreate,
    db: Session = Depends(get_db),
):
    """
    Upload a single document.
    Maps to the "+ Upload Document" button in the top-right of the UI.
    """
    return upload_document(db, payload)


# ─────────────────────────────────────────────────────────────────────────────
# Bulk upload
# POST /api/employees/documents/bulk-upload
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/bulk-upload", response_model=BulkUploadResponse)
def bulk_upload_route(
    payload: BulkUploadRequest,
    db: Session = Depends(get_db),
):
    """
    Upload multiple documents in one request.
    Maps to the "Bulk Upload" button in the top-right of the UI.
    Each document is committed independently — failures are reported
    per-row without blocking the rest.
    """
    return bulk_upload_documents(db, payload)


# ─────────────────────────────────────────────────────────────────────────────
# List all documents (main table)
# GET /api/employees/documents/
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[EmployeeDocumentResponse])
def list_documents(
    category     : Optional[DocumentCategory] = Query(None, description="All Categories dropdown"),
    status       : Optional[DocumentStatus]   = Query(None, description="All Status dropdown"),
    employee_type: Optional[str]              = Query(None, description="All Employee Types dropdown"),
    search       : Optional[str]              = Query(None, description="Search by name / type / employee"),
    db           : Session                    = Depends(get_db),
):
    """
    Returns all documents with optional filters.
    Drives the main document table including the 3 filter dropdowns
    (All Categories, All Status, All Employee Types) and search bar.
    """
    filters = DocumentFilter(
        category=category,
        status=status,
        employee_type=employee_type,
        search=search,
    )
    return list_all_documents(db, filters)


# ─────────────────────────────────────────────────────────────────────────────
# List documents for one employee
# GET /api/employees/documents/employee/{employee_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/employee/{employee_id}", response_model=List[EmployeeDocumentResponse])
def list_by_employee(employee_id: int, db: Session = Depends(get_db)):
    """All documents belonging to a specific employee."""
    return list_employee_documents(db, employee_id)


# ─────────────────────────────────────────────────────────────────────────────
# Get single document
# GET /api/employees/documents/detail/{doc_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/detail/{doc_id}", response_model=EmployeeDocumentResponse)
def get_document_route(doc_id: int, db: Session = Depends(get_db)):
    """
    Fetch a single document's full details.
    Maps to the 👁 View (eye icon) action button.
    """
    return get_document(db, doc_id)


# ─────────────────────────────────────────────────────────────────────────────
# Update (edit)
# PATCH /api/employees/documents/{doc_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/{doc_id}", response_model=EmployeeDocumentResponse)
def update_document_route(
    doc_id : int,
    payload: EmployeeDocumentUpdate,
    db     : Session = Depends(get_db),
):
    """
    Partial update of document metadata.
    Maps to the ✏️ Edit (pencil icon) action button.
    """
    return update_document(db, doc_id, payload)


# ─────────────────────────────────────────────────────────────────────────────
# New version (re-upload file)
# POST /api/employees/documents/{doc_id}/new-version
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{doc_id}/new-version", response_model=EmployeeDocumentResponse)
def new_version_route(
    doc_id      : int,
    file_path   : str = Body(..., embed=True),
    version_notes: Optional[str] = Body(None, embed=True),
    db          : Session = Depends(get_db),
):
    """
    Replace the file and auto-increment the version number.
    (v1.0 → v2.0, v2.1 → v3.0 …)
    Maps to the version-history clock icon in the UI.
    Re-sets status to PENDING so the new version gets re-reviewed.
    """
    return bump_version(db, doc_id, file_path, version_notes)


# ─────────────────────────────────────────────────────────────────────────────
# Review (approve / reject)
# PATCH /api/employees/documents/{doc_id}/review
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/{doc_id}/review", response_model=EmployeeDocumentResponse)
def review_document_route(
    doc_id : int,
    payload: ReviewRequest,
    db     : Session = Depends(get_db),
):
    """
    Approve or Reject a document.
    Maps to the green ✅ / red ❌ action buttons visible on Pending rows.

    Payload:
      { "status": "APPROVED" | "REJECTED", "reviewed_by": <employee_id>, "review_notes": "..." }
    """
    return review_document(db, doc_id, payload)


# ─────────────────────────────────────────────────────────────────────────────
# Legacy verify endpoint (backward compat)
# PATCH /api/employees/documents/{doc_id}/verify
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/{doc_id}/verify", response_model=EmployeeDocumentResponse)
def verify_document_route(
    doc_id : int,
    payload: VerifyRequest,
    db     : Session = Depends(get_db),
):
    """Legacy verify — sets is_verified=True and status=APPROVED."""
    return verify_document(db, doc_id, payload.verified_by)


# ─────────────────────────────────────────────────────────────────────────────
# Download URL
# GET /api/employees/documents/{doc_id}/download
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{doc_id}/download")
def download_document_route(doc_id: int, db: Session = Depends(get_db)):
    """
    Returns the file_path so the frontend can redirect to the file.
    Maps to the ⬇️ Download (arrow-down icon) action button.

    In production, replace file_path with a pre-signed S3 URL or
    stream the file using FileResponse / StreamingResponse.
    """
    doc = get_document(db, doc_id)
    return {"doc_id": doc.id, "file_path": doc.file_path, "file_format": doc.file_format}


# ─────────────────────────────────────────────────────────────────────────────
# Delete
# DELETE /api/employees/documents/{doc_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.delete("/{doc_id}", status_code=204)
def delete_document_route(doc_id: int, db: Session = Depends(get_db)):
    """
    Hard delete a document record.
    Maps to the 🗑 Delete (red trash icon) action button.
    """
    delete_document(db, doc_id)
