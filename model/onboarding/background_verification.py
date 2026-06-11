from sqlalchemy import (
    Column, Integer, String, Date, DateTime,
    Boolean, Text, ForeignKey, Enum as SAEnum
)
from core.database import Base
from datetime import datetime
import enum


class BGVStatus(str, enum.Enum):
    pending     = "Pending"
    in_progress = "In Progress"
    completed   = "Completed"
    rejected    = "Rejected"


class BGVDocumentStatus(str, enum.Enum):
    pending  = "Pending"
    uploaded = "Uploaded"
    verified = "Verified"
    optional = "Optional"


class BGVDocumentType(str, enum.Enum):
    required = "Required"
    optional = "Optional"



class BGVRequest(Base):
    __tablename__ = "bgv_requests"

    id              = Column(Integer, primary_key=True, index=True)

    
    name            = Column(String(255), nullable=False)
    employee_id     = Column(String(50),  nullable=True)    # EMP001, CAND001 etc
    email           = Column(String(255), nullable=False)
    phone_number    = Column(String(20),  nullable=True)
    department      = Column(String(100), nullable=True)
    designation     = Column(String(100), nullable=True)
    date_of_birth   = Column(Date,        nullable=True)
    gender          = Column(String(20),  nullable=True)
    marital_status  = Column(String(20),  nullable=True)
    joining_date    = Column(Date,        nullable=True)

    
    cc_emails       = Column(String(500), nullable=True)    # comma separated
    bcc_emails      = Column(String(500), nullable=True)
    subject         = Column(String(500), nullable=True,
                             default="Background Verification - Document Request")
    email_template  = Column(Text,        nullable=True)
    email_method    = Column(String(50),  nullable=True,
                             default="API")                 # API | Clipboard | Mailto
    is_fresher      = Column(Boolean,     default=False)

    
    status          = Column(
                          SAEnum(BGVStatus, name="bgv_status_enum"),
                          default=BGVStatus.pending,
                          nullable=False,
                      )
    progress        = Column(String(50), default="Not Started")  # Not Started | In Progress | Completed

    # Meta
    created_by      = Column(String(100), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class BGVDocument(Base):
    __tablename__ = "bgv_documents"

    id              = Column(Integer, primary_key=True, index=True)
    bgv_request_id  = Column(Integer, ForeignKey("bgv_requests.id"), nullable=False, index=True)
    document_name   = Column(String(255), nullable=False)   # "Aadhar Card", "PAN Card" etc
    document_type   = Column(
                          SAEnum(BGVDocumentType, name="bgv_doc_type_enum"),
                          nullable=False,
                      )
    upload_status   = Column(
                          SAEnum(BGVDocumentStatus, name="bgv_doc_status_enum"),
                          default=BGVDocumentStatus.pending,
                      )
    file_path       = Column(String(500), nullable=True)
    uploaded_at     = Column(DateTime,    nullable=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)




class BGVEducation(Base):
    __tablename__ = "bgv_education"

    id              = Column(Integer, primary_key=True, index=True)
    bgv_request_id  = Column(Integer, ForeignKey("bgv_requests.id"), nullable=False, index=True)
    degree          = Column(String(100), nullable=False)   # B.Tech, MBA etc
    institution     = Column(String(255), nullable=False)
    board_university= Column(String(255), nullable=True)
    year_of_passing = Column(Integer,     nullable=True)
    percentage      = Column(String(20),  nullable=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


class BGVGuardian(Base):
    __tablename__ = "bgv_guardians"

    id                  = Column(Integer, primary_key=True, index=True)
    bgv_request_id      = Column(Integer, ForeignKey("bgv_requests.id"), nullable=False, index=True)
    guardian_name       = Column(String(255), nullable=False)
    relationship        = Column(String(50),  nullable=False)   # Father | Mother | Spouse | Guardian
    phone_number        = Column(String(20),  nullable=False)
    employment_status   = Column(String(50),  nullable=True)
    organization        = Column(String(255), nullable=True)
    designation         = Column(String(100), nullable=True)
    is_legal_guardian   = Column(Boolean, default=False)
    is_active           = Column(Boolean, default=True)
    created_at          = Column(DateTime, default=datetime.utcnow)




class BGVAddress(Base):
    __tablename__ = "bgv_addresses"

    id                      = Column(Integer, primary_key=True, index=True)
    bgv_request_id          = Column(Integer, ForeignKey("bgv_requests.id"), nullable=False, index=True)
    address_type            = Column(String(20), nullable=False)  # current | permanent

    address_line_1          = Column(String(255), nullable=False)
    address_line_2          = Column(String(255), nullable=True)
    country                 = Column(String(100), nullable=False)
    state                   = Column(String(100), nullable=False)
    district                = Column(String(100), nullable=False)
    city                    = Column(String(100), nullable=False)
    pincode                 = Column(String(20),  nullable=False)
    nationality             = Column(String(100), nullable=True)
    same_as_current         = Column(Boolean, default=False)    # "Same as Current Address" checkbox
    is_active               = Column(Boolean, default=True)
    created_at              = Column(DateTime, default=datetime.utcnow)