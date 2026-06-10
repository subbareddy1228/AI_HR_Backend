
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
 
 
class CandidateTokenVerify(BaseModel):
    
    invite_token: str
 
 
class CandidateTokenResponse(BaseModel):
  
    id: int
    full_name: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    status: str
    token_expires_at: datetime
 
    model_config = ConfigDict(from_attributes=True)
 
 
class CandidateFormSubmit(BaseModel):
    
    invite_token: str
    form_data: Dict[str, Any]
 
 
class CandidateStatusUpdate(BaseModel):
 
    status: str  
 
 
class CandidateResponse(BaseModel):

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