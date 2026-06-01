# model/onboarding/profile.py
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from core.database import Base

class OnboardingProfile(Base):
    __tablename__ = "onboarding_profiles"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("onboarding_candidates.id"))

    # BASIC DETAILS
    first_name = Column(String)
    middle_name = Column(String)
    last_name = Column(String)
    gender = Column(String)
    date_of_birth = Column(Date)

    # CONTACT
    personal_email = Column(String)
    home_phone = Column(String)
    emergency_contact = Column(String)

    # PERSONAL INFO
    blood_group = Column(String)
    passport_number = Column(String)
    driving_license = Column(String)

    # FAMILY
    marital_status = Column(String)
    father_name = Column(String)
    father_phone = Column(String)
    mother_name = Column(String)
    mother_phone = Column(String)

    # ADDRESSES
    present_address = Column(String)
    permanent_address = Column(String)

    # BANK
    bank_name = Column(String)
    ifsc_code = Column(String)
    account_number = Column(String)
    account_holder_name = Column(String)

    # DOCUMENT PATHS
    pan_card = Column(String)
    aadhaar_card = Column(String)
