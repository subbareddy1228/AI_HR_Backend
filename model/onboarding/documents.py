from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from core.database import Base

class OnboardingDocuments(Base):
    __tablename__ = "onboarding_documents"

    id = Column(Integer, primary_key=True)

    # Required documents (*)
    pan_card = Column(String, nullable=False)
    aadhaar_card = Column(String, nullable=False)
    highest_education_proof = Column(String, nullable=False)

    # Optional documents
    esi_card = Column(String)
    driving_license = Column(String)
    passport = Column(String)
    last_relieving_letter = Column(String)
    last_salary_slip = Column(String)
    latest_bank_statement = Column(String)

    created_at = Column(DateTime, server_default=func.now())
