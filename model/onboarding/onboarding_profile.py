from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from datetime import datetime
from core.database import Base

class OnboardingProfile(Base):
    __tablename__ = "onboarding_profiles"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("onboarding_Forms.id"), unique=True)

    data = Column(JSON, nullable=False)  # stores all steps
    progress = Column(Integer, default=0)  # 0–100 %

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
