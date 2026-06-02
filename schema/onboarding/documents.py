from pydantic import BaseModel
from typing import Dict

class UploadResponse(BaseModel):
    

    # exactly same names as model
    pan_card: bool
    aadhaar_card: bool
    highest_education_proof: bool

    esi_card: bool
    driving_license: bool
    passport: bool
    last_relieving_letter: bool
    last_salary_slip: bool
    latest_bank_statement: bool

    required_completed: bool
