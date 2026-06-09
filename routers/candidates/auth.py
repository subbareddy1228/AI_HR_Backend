from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt

from core.database import get_db
from model.models import Candidate

router = APIRouter(tags=["Candidate Auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your_super_secret_key"
ALGORITHM = "HS256"

class CandidateSignup(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "candidate"

class CandidateLogin(BaseModel):
    email: EmailStr
    password: str

class CandidateTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    candidate_id: int
    name: str
    email: str

def create_candidate_token(candidate_id: int) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode({"sub": str(candidate_id), "type": "candidate", "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/signup", status_code=201)
def candidate_signup(payload: CandidateSignup, db: Session = Depends(get_db)):
    existing = db.execute(select(Candidate).where(Candidate.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    candidate = Candidate(
        name=payload.name,
        email=payload.email,
        hashed_password=pwd_context.hash(payload.password),
        role=payload.role or "candidate",
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return {"message": "Registration successful. You can now log in."}

@router.post("/login", response_model=CandidateTokenResponse)
def candidate_login(payload: CandidateLogin, db: Session = Depends(get_db)):
    candidate = db.execute(select(Candidate).where(Candidate.email == payload.email)).scalar_one_or_none()
    if not candidate or not hasattr(candidate, 'hashed_password'):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not pwd_context.verify(payload.password, candidate.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_candidate_token(candidate.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "candidate_id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
    }