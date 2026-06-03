from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status

from model.Employee_Management.employee_document import EmployeeDocument
from schema.Employee_Management.employee_document import EmployeeDocumentCreate, EmployeeDocumentUpdate


def upload_document(db: Session, payload: EmployeeDocumentCreate) -> EmployeeDocument:
    obj = EmployeeDocument(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_employee_documents(db: Session, employee_id: int) -> list[EmployeeDocument]:
    return db.execute(
        select(EmployeeDocument).where(EmployeeDocument.employee_id == employee_id)
    ).scalars().all()


def get_document(db: Session, doc_id: int) -> EmployeeDocument:
    obj = db.execute(
        select(EmployeeDocument).where(EmployeeDocument.id == doc_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return obj


def update_document(db: Session, doc_id: int, payload: EmployeeDocumentUpdate) -> EmployeeDocument:
    obj = get_document(db, doc_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def verify_document(db: Session, doc_id: int, verified_by: str) -> EmployeeDocument:
    obj = get_document(db, doc_id)
    obj.is_verified = True
    obj.verified_by = verified_by
    db.commit()
    db.refresh(obj)
    return obj


def delete_document(db: Session, doc_id: int) -> None:
    obj = get_document(db, doc_id)
    db.delete(obj)
    db.commit()