# FILE 5 of 12 | schema/Employee_Management/employee_document.py
# Schemas: EmployeeDocumentBase, EmployeeDocumentCreate, EmployeeDocumentUpdate, EmployeeDocumentResponse

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class EmployeeDocumentBase(BaseModel):
    employee_id: int
    document_type: str  # Aadhaar/PAN/Passport/Offer Letter/Relieving Letter/Payslip/Other
    document_name: str
    file_path: str
    is_verified: Optional[bool] = False
    verified_by: Optional[str] = None
    notes: Optional[str] = None


class EmployeeDocumentCreate(EmployeeDocumentBase):
    pass


class EmployeeDocumentUpdate(BaseModel):
    document_type: Optional[str] = None
    document_name: Optional[str] = None
    file_path: Optional[str] = None
    is_verified: Optional[bool] = None
    verified_by: Optional[str] = None
    notes: Optional[str] = None


class EmployeeDocumentResponse(EmployeeDocumentBase):
    id: int
    uploaded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class VerifyRequest(BaseModel):
    verified_by: str