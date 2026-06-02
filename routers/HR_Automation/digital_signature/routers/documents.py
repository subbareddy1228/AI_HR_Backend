from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from model.models import OnboardingDocument as DocumentModel, OnboardingCandidate as CandidateModel
import shutil, os
from schema.schemas import Document as DocumentSchema


router = APIRouter(prefix="/documents")

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=DocumentSchema)
async def upload_document(title: str = Form(...), file: UploadFile = ..., db: Session = Depends(get_db)):
    try:
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)

        db_doc = DocumentModel(title=title, filename=file.filename, file_path=file_location)
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        return db_doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all", response_model=list[DocumentSchema])
def get_documents(db: Session = Depends(get_db)):
    docs = db.query(DocumentModel).all()
    return docs
