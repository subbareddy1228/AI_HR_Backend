from sqlalchemy import Column, Integer, String, Date, Enum
from core.database import Base

class OnboardingForm(Base):
    __tablename__ = "onboarding_forms"

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    gender = Column(String)
    joining_date = Column(Date)
    confirmation_date = Column(Date, nullable=True)
    status = Column(Enum("DRAFT","SUBMITTED","APPROVED", name="onboarding_status"), default="DRAFT")
