from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime
from model.onboarding.background_verification import BGVStatus, BGVDocumentType, BGVDocumentStatus




class BGVDocumentBase(BaseModel):
    document_name: str
    document_type: BGVDocumentType
    upload_status: BGVDocumentStatus = BGVDocumentStatus.pending


class BGVDocumentResponse(BGVDocumentBase):
    id:             int
    bgv_request_id: int
    file_path:      Optional[str]  = None
    uploaded_at:    Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)



class BGVEducationCreate(BaseModel):
    degree:           str
    institution:      str
    board_university: Optional[str] = None
    year_of_passing:  Optional[int] = None
    percentage:       Optional[str] = None


class BGVEducationResponse(BGVEducationCreate):
    id:             int
    bgv_request_id: int

    model_config = ConfigDict(from_attributes=True)



class BGVGuardianCreate(BaseModel):
    guardian_name:     str
    relationship:      str           
    phone_number:      str
    employment_status: Optional[str] = None
    organization:      Optional[str] = None
    designation:       Optional[str] = None
    is_legal_guardian: bool          = False


class BGVGuardianResponse(BGVGuardianCreate):
    id:             int
    bgv_request_id: int

    model_config = ConfigDict(from_attributes=True)



class BGVAddressCreate(BaseModel):
    address_type:   str              
    address_line_1: str
    address_line_2: Optional[str] = None
    country:        str
    state:          str
    district:       str
    city:           str
    pincode:        str
    nationality:    Optional[str] = None
    same_as_current:bool         = False


class BGVAddressResponse(BGVAddressCreate):
    id:             int
    bgv_request_id: int

    model_config = ConfigDict(from_attributes=True)



class BGVRequestCreate(BaseModel):
    
    name:           str
    employee_id:    Optional[str]      = None
    email:          EmailStr
    phone_number:   Optional[str]      = None
    department:     Optional[str]      = None
    designation:    Optional[str]      = None
    date_of_birth:  Optional[date]     = None
    gender:         Optional[str]      = None
    marital_status: Optional[str]      = None
    joining_date:   Optional[date]     = None

    
    cc_emails:      Optional[str]      = None
    bcc_emails:     Optional[str]      = None
    subject:        Optional[str]      = "Background Verification - Document Request"
    email_template: Optional[str]      = None
    email_method:   Optional[str]      = "API"   
    is_fresher:     bool               = False
    created_by:     Optional[str]      = None

   
    education:      List[BGVEducationCreate] = []
    guardian:       Optional[BGVGuardianCreate] = None
    current_address:Optional[BGVAddressCreate]  = None
    permanent_address:Optional[BGVAddressCreate] = None


class BGVRequestUpdate(BaseModel):
    name:           Optional[str]  = None
    phone_number:   Optional[str]  = None
    department:     Optional[str]  = None
    designation:    Optional[str]  = None
    date_of_birth:  Optional[date] = None
    gender:         Optional[str]  = None
    marital_status: Optional[str]  = None
    status:         Optional[BGVStatus] = None
    progress:       Optional[str]  = None
    cc_emails:      Optional[str]  = None
    bcc_emails:     Optional[str]  = None
    subject:        Optional[str]  = None
    email_template: Optional[str]  = None
    is_fresher:     Optional[bool] = None


class BGVRequestResponse(BaseModel):
    id:             int
    name:           str
    employee_id:    Optional[str]
    email:          str
    phone_number:   Optional[str]
    department:     Optional[str]
    designation:    Optional[str]
    date_of_birth:  Optional[date]
    gender:         Optional[str]
    marital_status: Optional[str]
    joining_date:   Optional[date]
    cc_emails:      Optional[str]
    bcc_emails:     Optional[str]
    subject:        Optional[str]
    email_template: Optional[str]
    email_method:   Optional[str]
    is_fresher:     bool
    status:         BGVStatus
    progress:       Optional[str]
    created_by:     Optional[str]
    created_at:     datetime
    updated_at:     datetime

    
    documents:  List[BGVDocumentResponse]  = []
    education:  List[BGVEducationResponse] = []
    guardian:   Optional[BGVGuardianResponse]  = None
    addresses:  List[BGVAddressResponse]   = []

    model_config = ConfigDict(from_attributes=True)




class BGVKPISchema(BaseModel):
    totalEmployees: int
    pending:        int
    inProgress:     int
    completed:      int




class BGVSendEmailSchema(BaseModel):
    bgv_request_id: int
    method:         str = "API"     