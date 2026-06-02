from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from model.models import Candidate, Document, DocStatus, SessionLocal

router = APIRouter(prefix="/documents", tags=["Documents"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{candidate_id}")
def list_documents(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return [
        {"id": d.id, "name": d.name, "status": d.status.value, "filename": d.filename}
        for d in candidate.documents
    ]

@router.get("/status/{candidate_id}/{doc_id}")
def document_status(candidate_id: int, doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.candidate_id == candidate_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"id": doc.id, "name": doc.name, "status": doc.status.value, "filename": doc.filename}
