# schema/onboarding/profile.py
from pydantic import BaseModel
from typing import Optional
from datetime import date

class OnboardingSubmit(BaseModel):
    first_name: str
    middle_name: Optional[str]
    last_name: str
    gender: str
    date_of_birth: date

    personal_email: str
    home_phone: Optional[str]
    emergency_contact: str

    blood_group: Optional[str]
    passport_number: Optional[str]
    driving_license: Optional[str]

    marital_status: str
    father_name: Optional[str]
    father_phone: Optional[str]
    mother_name: Optional[str]
    mother_phone: Optional[str]

    present_address: str
    permanent_address: str

    bank_name: str
    ifsc_code: str
    account_number: str
    account_holder_name: str
