from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from model.models import Candidate, OnboardingDocument as Document
from core.database import SessionLocal, engine 


router = APIRouter(prefix="/candidates", tags=["Candidates"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def create_candidate(name: str, email: str, db: Session = Depends(get_db)):
    existing = db.query(Candidate).filter(Candidate.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Candidate already exists")

    candidate = Candidate(name=name, email=email)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    # Seed required documents
    for doc_name in ["ID", "Tax", "Certificate"]:
        db.add(Document(name=doc_name, candidate_id=candidate.id))
    db.commit()

    return {"id": candidate.id, "name": candidate.name, "email": candidate.email}

@router.get("/")
def get_candidates(
    choice: str = Query(..., description="Enter 'all' to get all candidates or an ID number to get a specific candidate"),
    db: Session = Depends(get_db)
):
    if choice.lower() == "all":
        candidates = db.query(Candidate).all()
        return [{"id": c.id, "name": c.name, "email": c.email} for c in candidates]
    
    # If not "all", treat it as candidate ID
    try:
        candidate_id = int(choice)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid candidate ID")

    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    return {"id": candidate.id, "name": candidate.name, "email": candidate.email}

