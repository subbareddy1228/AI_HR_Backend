from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException
from sqlalchemy.orm import Session
import shutil, os
from core.database import get_db
from model.models import Signature

router = APIRouter(prefix="/signatures")

SIG_DIR = "uploaded_signatures"
os.makedirs(SIG_DIR, exist_ok=True)

# Upload signature
@router.post("/upload")
async def upload_signature(name: str = Form(...), file: UploadFile = ..., db: Session = Depends(get_db)):
    try:
        file_location = os.path.join(SIG_DIR, file.filename)
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        db_sig = Signature(name=name, filename=file.filename, file_path=file_location)
        db.add(db_sig)
        db.commit()
        db.refresh(db_sig)
        return {"id": db_sig.id, "name": db_sig.name, "filename": db_sig.filename, "file_path": db_sig.file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List all signatures
@router.get("/all")
def get_signatures(db: Session = Depends(get_db)):
    sigs = db.query(Signature).all()
    return [{"id": s.id, "name": s.name, "filename": s.filename, "file_path": s.file_path} for s in sigs]
