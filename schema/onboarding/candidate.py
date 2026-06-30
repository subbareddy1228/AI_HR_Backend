from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime



VERIFICATION_CREDITS: dict[str, int] = {
    "mobile":  0,   
    "pan":     5,
    "bank":    5,
    "aadhaar": 10,
}


def compute_credits(options: List[str]) -> int:
    return sum(VERIFICATION_CREDITS.get(opt, 0) for opt in options)




class CandidateCreate(BaseModel):
    
    full_name: str
    email:  Optional[EmailStr] = None
    mobile: Optional[str] = Field(default=None, pattern=r"^[0-9]{10}$")
    verification_options: List[str] = Field(
        default=[],
        description="Subset of ['mobile','pan','bank','aadhaar']",
    )


class CandidateUpdate(BaseModel):
   
    full_name: Optional[str]                = None
    email:     Optional[EmailStr]           = None
    mobile:    Optional[str]                = Field(default=None, pattern=r"^[0-9]{10}$")
    verification_options: Optional[List[str]] = None




class CandidateOut(BaseModel):
    id:           int
    full_name:    str
    email:        Optional[str]
    mobile:       Optional[str]
    status:       str
    verification_options: List[str]
    credits_used: int
    created_at:   datetime
    updated_at:   datetime

    class Config:
        from_attributes = True


class PaginatedCandidates(BaseModel):
    total:   int
    page:    int
    per_page: int
    results: List[CandidateOut]