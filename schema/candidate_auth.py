# schema/candidate_auth.py
# Pydantic schemas for Candidate authentication and onboarding
 
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
 
 
class CandidateTokenVerify(BaseModel):
    """Request body for verifying an invite token."""
    invite_token: str
 
 
class CandidateTokenResponse(BaseModel):
    """Returned after a valid token verification."""
    id: int
    full_name: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    status: str
    token_expires_at: datetime
 
    model_config = ConfigDict(from_attributes=True)
 
 
class CandidateFormSubmit(BaseModel):
    """Request body for submitting onboarding form data."""
    invite_token: str
    form_data: Dict[str, Any]
 
 
class CandidateStatusUpdate(BaseModel):
    """Request body for HR to update candidate status."""
    status: str  # SENT | IN_PROGRESS | SUBMITTED | APPROVED | REJECTED
 
 
class CandidateResponse(BaseModel):
    """Full candidate record returned to HR."""
    id: int
    full_name: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    invite_token: str
    token_expires_at: datetime
    status: str
    form_data: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime
 
    model_config = ConfigDict(from_attributes=True)