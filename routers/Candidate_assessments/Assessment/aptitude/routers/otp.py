from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from model.models import LegacyCandidate as Candidate 
from ..schemas.candidate import CandidateCreate, OTPVerify
from ..utils import generate_otp, send_email

router = APIRouter(prefix="/otp", tags=["OTP"])

# Temporary in-memory storage for OTPs
TEMP_OTPS = {}

@router.post("/send")
def send_otp(data: CandidateCreate, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter_by(email=data.email).first()
    
    if not candidate:
        #  Do NOT include 'role', it's not in LegacyCandidate
        candidate = Candidate(
            name=data.name,
            email=data.email,
            status="Pending",
            score=0,
            verified=0,
            answers={}
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

    otp_code = generate_otp()
    TEMP_OTPS[candidate.email] = otp_code
    send_email(candidate.email, "Your OTP", f"Your OTP is: {otp_code}")

    return {"message": "OTP sent successfully"}

@router.post("/verify")
def verify_otp(data: OTPVerify, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter_by(email=data.email).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if TEMP_OTPS.get(data.email) != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # LegacyCandidate.verified is Integer, so use 1 instead of True
    candidate.verified = 1
    db.commit()
    TEMP_OTPS.pop(data.email, None)

    return {"message": "OTP verified successfully"}
