from pydantic import BaseModel
from typing import Optional
from utils.enums import BloodGroupEnum

class PersonalInfoCreate(BaseModel):
    user_id: int
    blood_group: BloodGroupEnum
    passport_number: Optional[str]
    driving_license_number: Optional[str]
