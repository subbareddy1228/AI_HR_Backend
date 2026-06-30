
from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from model.Employee_Management.employee_document import EmployeeDocument
from schema.Employee_Management.employee_document import (
    EmployeeDocumentCreate,
    EmployeeDocumentUpdate,
    BulkUploadRequest,
    BulkUploadResponse,
    ReviewRequest,
    DocumentVaultStats,
    ChecklistItem,
    EmployeeChecklist,
    DocumentFilter,
    DocumentStatus,
)


def _get_or_404(db: Session, doc_id: int) -> EmployeeDocument:
    
    obj = db.execute(
        select(EmployeeDocument).where(EmployeeDocument.id == doc_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id={doc_id} not found",
        )
    return obj


def upload_document(
    db: Session,
    payload: EmployeeDocumentCreate,
) -> EmployeeDocument:
    
    obj = EmployeeDocument(**payload.model_dump())
    if obj.upload_date is None:
        obj.upload_date = date.today()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def bulk_upload_documents(
    db: Session,
    payload: BulkUploadRequest,
) -> BulkUploadResponse:
   
    succeeded = 0
    errors: List[str] = []

    for idx, item in enumerate(payload.documents, start=1):
        try:
            obj = EmployeeDocument(**item.model_dump())
            if obj.upload_date is None:
                obj.upload_date = date.today()
            db.add(obj)
            db.commit()
            db.refresh(obj)
            succeeded += 1
        except Exception as exc: 
            db.rollback()
            errors.append(f"Row {idx} ({item.document_name}): {exc}")

    return BulkUploadResponse(
        total=len(payload.documents),
        succeeded=succeeded,
        failed=len(payload.documents) - succeeded,
        errors=errors,
    )


def list_all_documents(
    db: Session,
    filters: Optional[DocumentFilter] = None,
) -> List[EmployeeDocument]:

    stmt = select(EmployeeDocument)

    if filters:
        conditions = []

        if filters.category:
            conditions.append(EmployeeDocument.category == filters.category.value)

        if filters.status:
            conditions.append(EmployeeDocument.status == filters.status.value)

        if filters.search:
            term = f"%{filters.search}%"
            conditions.append(
                or_(
                    EmployeeDocument.document_name.ilike(term),
                    EmployeeDocument.document_type.ilike(term),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

    stmt = stmt.order_by(EmployeeDocument.created_at.desc())
    return db.execute(stmt).scalars().all()


def list_employee_documents(
    db: Session,
    employee_id: int,
) -> List[EmployeeDocument]:

    return db.execute(
        select(EmployeeDocument)
        .where(EmployeeDocument.employee_id == employee_id)
        .order_by(EmployeeDocument.created_at.desc())
    ).scalars().all()


def get_document(db: Session, doc_id: int) -> EmployeeDocument:
    """Single document by ID."""
    return _get_or_404(db, doc_id)


def update_document(
    db: Session,
    doc_id: int,
    payload: EmployeeDocumentUpdate,
) -> EmployeeDocument:
  
    obj = _get_or_404(db, doc_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def bump_version(
    db: Session,
    doc_id: int,
    new_file_path: str,
    version_notes: Optional[str] = None,
) -> EmployeeDocument:

    obj = _get_or_404(db, doc_id)


    raw = obj.version.lstrip("v")
    parts = raw.split(".")
    try:
        major = int(parts[0]) + 1
        new_version = f"v{major}.0"
    except (ValueError, IndexError):
        new_version = "v2.0"

    obj.file_path     = new_file_path
    obj.version       = new_version
    obj.version_notes = version_notes
    obj.upload_date   = date.today()
    obj.status        = DocumentStatus.PENDING  
    obj.updated_at    = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def review_document(
    db: Session,
    doc_id: int,
    payload: ReviewRequest,
) -> EmployeeDocument:
   
    obj = _get_or_404(db, doc_id)

    obj.status       = payload.status.value
    obj.reviewed_by  = payload.reviewed_by
    obj.reviewed_at  = datetime.utcnow()
    obj.review_notes = payload.review_notes

    if payload.status == DocumentStatus.APPROVED:
        obj.is_verified = True

    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def verify_document(
    db: Session,
    doc_id: int,
    verified_by: str,
) -> EmployeeDocument:
    
    obj = _get_or_404(db, doc_id)
    obj.is_verified  = True
    obj.verified_by  = verified_by
    obj.status       = DocumentStatus.APPROVED
    obj.reviewed_at  = datetime.utcnow()
    obj.updated_at   = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def delete_document(db: Session, doc_id: int) -> None:
 
    obj = _get_or_404(db, doc_id)
    db.delete(obj)
    db.commit()


def get_vault_stats(db: Session) -> DocumentVaultStats:
   
    today         = date.today()
    expiry_cutoff = today + timedelta(days=30)

    total = db.execute(
        select(func.count()).select_from(EmployeeDocument)
    ).scalar_one()

    approved = db.execute(
        select(func.count()).select_from(EmployeeDocument)
        .where(EmployeeDocument.status == DocumentStatus.APPROVED)
    ).scalar_one()

    pending = db.execute(
        select(func.count()).select_from(EmployeeDocument)
        .where(EmployeeDocument.status == DocumentStatus.PENDING)
    ).scalar_one()

    expiring = db.execute(
        select(func.count()).select_from(EmployeeDocument)
        .where(
            and_(
                EmployeeDocument.expiry_date.is_not(None),
                EmployeeDocument.expiry_date >= today,
                EmployeeDocument.expiry_date <= expiry_cutoff,
            )
        )
    ).scalar_one()

    return DocumentVaultStats(
        total_documents=total,
        approved=approved,
        pending_review=pending,
        expiring_soon=expiring,
    )



REQUIRED_DOCUMENT_TYPES = [
    {"document_type": "Aadhaar",              "category": "KYC",         "is_mandatory": True},
    {"document_type": "PAN",                  "category": "KYC",         "is_mandatory": True},
    {"document_type": "Passport",             "category": "KYC",         "is_mandatory": False},
    {"document_type": "Graduation Certificate","category": "Educational", "is_mandatory": True},
    {"document_type": "Employment Contract",  "category": "Employment",  "is_mandatory": True},
    {"document_type": "Offer Letter",         "category": "Employment",  "is_mandatory": True},
    {"document_type": "Relieving Letter",     "category": "Employment",  "is_mandatory": False},
    {"document_type": "Payslip",              "category": "Employment",  "is_mandatory": False},
]


def get_employee_checklist(db: Session, employee_id: int) -> EmployeeChecklist:

    uploaded: List[EmployeeDocument] = db.execute(
        select(EmployeeDocument)
        .where(EmployeeDocument.employee_id == employee_id)
    ).scalars().all()

    uploaded_map: dict[str, EmployeeDocument] = {}
    for doc in uploaded:
        dt = doc.document_type.lower()
        existing = uploaded_map.get(dt)
        if existing is None or doc.created_at > existing.created_at:
            uploaded_map[dt] = doc

    items: List[ChecklistItem] = []
    completed = pending = missing = 0

    for req in REQUIRED_DOCUMENT_TYPES:
        key  = req["document_type"].lower()
        doc  = uploaded_map.get(key)

        if doc is None:
            item_status = "MISSING"
            missing += 1
        elif doc.status == DocumentStatus.APPROVED:
            item_status = "APPROVED"
            completed += 1
        else:
            item_status = doc.status
            pending += 1

        items.append(ChecklistItem(
            document_type = req["document_type"],
            category      = req["category"],
            is_mandatory  = req["is_mandatory"],
            status        = item_status,
            document_id   = doc.id if doc else None,
            document_name = doc.document_name if doc else None,
            expiry_date   = doc.expiry_date if doc else None,
        ))

    return EmployeeChecklist(
        employee_id    = employee_id,
        total_required = len(REQUIRED_DOCUMENT_TYPES),
        completed      = completed,
        pending        = pending,
        missing        = missing,
        items          = items,
    )
