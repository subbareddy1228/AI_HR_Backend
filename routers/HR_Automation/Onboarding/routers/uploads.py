from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import os, shutil, uuid
from model.models import Candidate, OnboardingDocument as Document, DocStatus, UPLOAD_DIR
from core.database import SessionLocal


router = APIRouter(prefix="/upload", tags=["Uploads"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# GET: show document slots
@router.get("/{candidate_id}")
def get_document_slots(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    docs = db.query(Document).filter(Document.candidate_id == candidate_id).all()
    return [{"name": doc.name, "status": doc.status.value, "filename": doc.filename} for doc in docs]

# POST: upload documents
@router.post("/{candidate_id}")
async def upload_documents(candidate_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Cannot upload more than 3 documents at a time")

    allowed_exts = [".pdf", ".jpg", ".png"]
    valid_doc_names = ["ID", "Tax", "Certificate"]
    uploaded_files = []
    errors = []

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        doc_name = file.filename.split("_")[0]

        if ext not in allowed_exts:
            errors.append({"filename": file.filename, "error": "Invalid file format"})
            continue

        if doc_name not in valid_doc_names:
            errors.append({"filename": file.filename, "error": f"Document '{doc_name}' not valid"})
            continue

        doc = db.query(Document).filter(Document.name == doc_name, Document.candidate_id == candidate_id).first()
        if not doc:
            errors.append({"filename": file.filename, "error": f"Document '{doc_name}' not assigned to this candidate"})
            continue

        if doc.status == DocStatus.completed:
            errors.append({"filename": file.filename, "error": f"Document '{doc_name}' has already been uploaded"})
            continue

        unique_filename = f"{doc.name}_{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        doc.filename = unique_filename
        doc.status = DocStatus.completed
        db.commit()

        uploaded_files.append({"name": doc.name, "filename": unique_filename, "status": doc.status.value})

    response = {"uploaded": uploaded_files}
    if errors:
        response["errors"] = errors

    return response

    