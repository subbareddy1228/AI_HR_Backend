
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import enum



class DocumentCategory(str, enum.Enum):
    KYC         = "KYC"
    Educational = "Educational"
    Employment  = "Employment"
    Medical     = "Medical"
    Legal       = "Legal"
    Other       = "Other"


class DocumentStatus(str, enum.Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"



class EmployeeDocumentBase(BaseModel):
    employee_id   : int
    document_name : str                          = Field(..., example="Aadhaar Card")
    document_type : str                          = Field(..., example="Aadhaar")
    category      : DocumentCategory             = DocumentCategory.Other
    is_mandatory  : bool                         = False
    file_path     : str
    file_format   : Optional[str]                = Field(None, example="PDF")
    file_size_mb  : Optional[Decimal]            = Field(None, example=2.4)
    version       : str                          = Field("v1.0", example="v1.0")
    version_notes : Optional[str]                = None
    upload_date   : Optional[date]               = None
    expiry_date   : Optional[date]               = None   # None → "No Expiry"
    notes         : Optional[str]                = None



class EmployeeDocumentCreate(EmployeeDocumentBase):
   
    pass



class BulkDocumentItem(BaseModel):
  
    employee_id   : int
    document_name : str
    document_type : str
    category      : DocumentCategory = DocumentCategory.Other
    is_mandatory  : bool             = False
    file_path     : str
    file_format   : Optional[str]    = None
    file_size_mb  : Optional[Decimal] = None
    version       : str              = "v1.0"
    upload_date   : Optional[date]   = None
    expiry_date   : Optional[date]   = None
    notes         : Optional[str]    = None


class BulkUploadRequest(BaseModel):
    
    documents: List[BulkDocumentItem] = Field(..., min_length=1)


class BulkUploadResponse(BaseModel):
    total     : int
    succeeded : int
    failed    : int
    errors    : List[str] = []



class EmployeeDocumentUpdate(BaseModel):
    
    document_name : Optional[str]              = None
    document_type : Optional[str]              = None
    category      : Optional[DocumentCategory] = None
    is_mandatory  : Optional[bool]             = None
    file_path     : Optional[str]              = None
    file_format   : Optional[str]              = None
    file_size_mb  : Optional[Decimal]          = None
    version       : Optional[str]              = None
    version_notes : Optional[str]              = None
    upload_date   : Optional[date]             = None
    expiry_date   : Optional[date]             = None
    notes         : Optional[str]              = None



class ReviewRequest(BaseModel):
   
    status       : DocumentStatus
    reviewed_by  : int   = Field(..., description="Employee ID of the reviewer")
    review_notes : Optional[str] = None



class VerifyRequest(BaseModel):
    verified_by: str



class EmployeeDocumentResponse(BaseModel):
    id            : int
    employee_id   : int
    document_name : str
    document_type : str
    category      : str
    is_mandatory  : bool
    file_path     : str
    file_format   : Optional[str]    = None
    file_size_mb  : Optional[Decimal] = None
    version       : str
    version_notes : Optional[str]    = None
    upload_date   : Optional[date]   = None
    expiry_date   : Optional[date]   = None  
    status        : str
    reviewed_by   : Optional[int]    = None
    reviewed_at   : Optional[datetime] = None
    review_notes  : Optional[str]    = None
    is_verified   : bool
    verified_by   : Optional[str]    = None
    notes         : Optional[str]    = None
    uploaded_at   : Optional[datetime] = None
    created_at    : Optional[datetime] = None
    updated_at    : Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)




class DocumentVaultStats(BaseModel):
  
    total_documents : int
    approved        : int
    pending_review  : int
    expiring_soon   : int  




class ChecklistItem(BaseModel):
   
    document_type : str
    category      : str
    is_mandatory  : bool
    status        : str    
    document_id   : Optional[int]   = None   
    document_name : Optional[str]   = None
    expiry_date   : Optional[date]  = None


class EmployeeChecklist(BaseModel):
   
    employee_id     : int
    total_required  : int
    completed       : int
    pending         : int
    missing         : int
    items           : List[ChecklistItem]



class DocumentFilter(BaseModel):
    category      : Optional[DocumentCategory] = None
    status        : Optional[DocumentStatus]   = None
    employee_type : Optional[str]              = None  
    search        : Optional[str]              = None   
