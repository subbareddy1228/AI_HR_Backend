from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from datetime import datetime
from core.database import Base


class Candidate(Base):
    __tablename__ = "onboarding_forms_candidates"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String, nullable=False)
    email    = Column(String, nullable=True)
    mobile   = Column(String(10), nullable=True)

    invite_token     = Column(String, unique=True, index=True, nullable=False)
    token_expires_at = Column(DateTime, nullable=False)

   
    status = Column(String, default="SENT")

    verification_options = Column(JSON, default=[])

  
    credits_used = Column(Integer, default=0)

    
    form_data = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )