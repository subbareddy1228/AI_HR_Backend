from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status, UploadFile
from datetime import datetime, date
from typing import Optional, List

from fastapi_mail import FastMail, MessageSchema, MessageType
from core.mail import mail_config
from utils.file_upload import save_file

from model.onboarding.background_verification import (
    BGVRequest, BGVDocument, BGVEducation,
    BGVGuardian, BGVAddress,
    BGVStatus, BGVDocumentStatus, BGVDocumentType,
)
from schema.onboarding.background_verification import (
    BGVRequestCreate, BGVRequestUpdate,
    BGVEducationCreate, BGVGuardianCreate, BGVAddressCreate,
)



DEFAULT_DOCUMENTS = [
    {"document_name": "Aadhar Card",           "document_type": BGVDocumentType.required},
    {"document_name": "PAN Card",              "document_type": BGVDocumentType.required},
    {"document_name": "Passport",              "document_type": BGVDocumentType.optional},
    {"document_name": "Driving License",       "document_type": BGVDocumentType.optional},
    {"document_name": "Education Certificates","document_type": BGVDocumentType.required},
    {"document_name": "Address Proof",         "document_type": BGVDocumentType.required},
    {"document_name": "Bank Statement",        "document_type": BGVDocumentType.optional},
    {"document_name": "Passport Size Photo",   "document_type": BGVDocumentType.required},
    {"document_name": "InterShip Certificates","document_type": BGVDocumentType.optional},
]




def get_bgv_kpi(db: Session) -> dict:
    """4 KPI counts — Total, Pending, In Progress, Completed."""
    total       = db.query(func.count(BGVRequest.id)).scalar() or 0
    pending     = db.query(func.count(BGVRequest.id)).filter(BGVRequest.status == BGVStatus.pending).scalar() or 0
    in_progress = db.query(func.count(BGVRequest.id)).filter(BGVRequest.status == BGVStatus.in_progress).scalar() or 0
    completed   = db.query(func.count(BGVRequest.id)).filter(BGVRequest.status == BGVStatus.completed).scalar() or 0

    return {
        "totalEmployees": total,
        "pending":        pending,
        "inProgress":     in_progress,
        "completed":      completed,
    }




def list_bgv_requests(
    db:     Session,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    skip:   int = 0,
    limit:  int = 50,
) -> List[dict]:
    
    q = db.query(BGVRequest)

    if search:
        q = q.filter(
            BGVRequest.name.ilike(f"%{search}%")        |
            BGVRequest.email.ilike(f"%{search}%")       |
            BGVRequest.employee_id.ilike(f"%{search}%")
        )
    if status_filter and status_filter.lower() != "all":
        q = q.filter(BGVRequest.status == status_filter)

    requests = q.order_by(BGVRequest.created_at.desc()).offset(skip).limit(limit).all()

    return [_request_to_list_dict(r) for r in requests]


def _request_to_list_dict(r: BGVRequest) -> dict:
    return {
        "id":          r.id,
        "name":        r.name,
        "employeeId":  r.employee_id,
        "email":       r.email,
        "phoneNumber": r.phone_number,
        "department":  r.department,
        "designation": r.designation,
        "joiningDate": str(r.joining_date) if r.joining_date else None,
        "status":      r.status.value,
        "progress":    r.progress,
        "createdAt":   str(r.created_at),
    }




def get_bgv_request(db: Session, bgv_id: int) -> dict:
    
    r = db.execute(
        select(BGVRequest).where(BGVRequest.id == bgv_id)
    ).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="BGV request not found")

    docs      = db.execute(select(BGVDocument).where(BGVDocument.bgv_request_id == bgv_id, BGVDocument.is_active == True)).scalars().all()
    education = db.execute(select(BGVEducation).where(BGVEducation.bgv_request_id == bgv_id, BGVEducation.is_active == True)).scalars().all()
    guardian  = db.execute(select(BGVGuardian).where(BGVGuardian.bgv_request_id == bgv_id, BGVGuardian.is_active == True)).scalars().first()
    addresses = db.execute(select(BGVAddress).where(BGVAddress.bgv_request_id == bgv_id, BGVAddress.is_active == True)).scalars().all()

    return {
        **_request_to_list_dict(r),
        "gender":         r.gender,
        "maritalStatus":  r.marital_status,
        "dateOfBirth":    str(r.date_of_birth) if r.date_of_birth else None,
        "ccEmails":       r.cc_emails,
        "bccEmails":      r.bcc_emails,
        "subject":        r.subject,
        "emailTemplate":  r.email_template,
        "emailMethod":    r.email_method,
        "isFresher":      r.is_fresher,
        "createdBy":      r.created_by,
        "documents":  [_doc_to_dict(d)  for d in docs],
        "education":  [_edu_to_dict(e)  for e in education],
        "guardian":   _guardian_to_dict(guardian) if guardian else None,
        "addresses":  [_addr_to_dict(a) for a in addresses],
    }




def create_bgv_request(db: Session, payload: BGVRequestCreate) -> dict:
   
    
    r = BGVRequest(
        name=payload.name,
        employee_id=payload.employee_id,
        email=payload.email,
        phone_number=payload.phone_number,
        department=payload.department,
        designation=payload.designation,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        marital_status=payload.marital_status,
        joining_date=payload.joining_date,
        cc_emails=payload.cc_emails,
        bcc_emails=payload.bcc_emails,
        subject=payload.subject,
        email_template=payload.email_template,
        email_method=payload.email_method,
        is_fresher=payload.is_fresher,
        created_by=payload.created_by,
        status=BGVStatus.pending,
        progress="Not Started",
    )
    db.add(r)
    db.flush()  

    
    for doc in DEFAULT_DOCUMENTS:
        status_val = (
            BGVDocumentStatus.optional
            if doc["document_type"] == BGVDocumentType.optional
            else BGVDocumentStatus.pending
        )
        db.add(BGVDocument(
            bgv_request_id=r.id,
            document_name=doc["document_name"],
            document_type=doc["document_type"],
            upload_status=status_val,
        ))

    
    for edu in payload.education:
        db.add(BGVEducation(bgv_request_id=r.id, **edu.model_dump()))

    
    if payload.guardian:
        db.add(BGVGuardian(bgv_request_id=r.id, **payload.guardian.model_dump()))

    
    if payload.current_address:
        db.add(BGVAddress(bgv_request_id=r.id, **payload.current_address.model_dump()))
    if payload.permanent_address and not (payload.permanent_address.same_as_current):
        db.add(BGVAddress(bgv_request_id=r.id, **payload.permanent_address.model_dump()))

    db.commit()
    db.refresh(r)
    return get_bgv_request(db, r.id)




def update_bgv_request(db: Session, bgv_id: int, payload: BGVRequestUpdate) -> dict:
    r = db.execute(
        select(BGVRequest).where(BGVRequest.id == bgv_id)
    ).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="BGV request not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(r, field, value)

    db.commit()
    db.refresh(r)
    return get_bgv_request(db, r.id)




def delete_bgv_request(db: Session, bgv_id: int) -> dict:
    r = db.execute(
        select(BGVRequest).where(BGVRequest.id == bgv_id)
    ).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="BGV request not found")

    db.delete(r)
    db.commit()
    return {"message": f"BGV request for '{r.name}' deleted", "id": bgv_id}




def upload_bgv_document(
    db:         Session,
    bgv_id:     int,
    doc_id:     int,
    file:       UploadFile,
) -> dict:
   
    doc = db.execute(
        select(BGVDocument).where(
            BGVDocument.id             == doc_id,
            BGVDocument.bgv_request_id == bgv_id,
        )
    ).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document record not found")

    
    file_path       = save_file(file, f"bgv_{bgv_id}_{doc_id}")
    doc.file_path   = file_path
    doc.upload_status = BGVDocumentStatus.uploaded
    doc.uploaded_at   = datetime.utcnow()

    
    _update_request_progress(db, bgv_id)

    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


def _update_request_progress(db: Session, bgv_id: int):
    
    docs = db.execute(
        select(BGVDocument).where(
            BGVDocument.bgv_request_id == bgv_id,
            BGVDocument.is_active      == True,
        )
    ).scalars().all()

    required = [d for d in docs if d.document_type == BGVDocumentType.required]
    uploaded = [d for d in required if d.upload_status == BGVDocumentStatus.uploaded]

    r = db.execute(select(BGVRequest).where(BGVRequest.id == bgv_id)).scalars().first()
    if not r:
        return

    if len(uploaded) == 0:
        r.progress = "Not Started"
        r.status   = BGVStatus.pending
    elif len(uploaded) < len(required):
        r.progress = f"{len(uploaded)}/{len(required)} docs uploaded"
        r.status   = BGVStatus.in_progress
    else:
        r.progress = "Completed"
        r.status   = BGVStatus.completed




def add_education(db: Session, bgv_id: int, payload: BGVEducationCreate) -> dict:
    
    _check_request(db, bgv_id)
    edu = BGVEducation(bgv_request_id=bgv_id, **payload.model_dump())
    db.add(edu)
    db.commit()
    db.refresh(edu)
    return _edu_to_dict(edu)


def delete_education(db: Session, bgv_id: int, edu_id: int) -> dict:
    edu = db.execute(
        select(BGVEducation).where(
            BGVEducation.id == edu_id,
            BGVEducation.bgv_request_id == bgv_id,
        )
    ).scalars().first()
    if not edu:
        raise HTTPException(status_code=404, detail="Education record not found")
    edu.is_active = False
    db.commit()
    return {"message": "Education record deleted", "id": edu_id}




def save_guardian(db: Session, bgv_id: int, payload: BGVGuardianCreate) -> dict:
   
    _check_request(db, bgv_id)

    existing = db.execute(
        select(BGVGuardian).where(
            BGVGuardian.bgv_request_id == bgv_id,
            BGVGuardian.is_active      == True,
        )
    ).scalars().first()

    if existing:
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return _guardian_to_dict(existing)
    else:
        g = BGVGuardian(bgv_request_id=bgv_id, **payload.model_dump())
        db.add(g)
        db.commit()
        db.refresh(g)
        return _guardian_to_dict(g)




def save_address(db: Session, bgv_id: int, payload: BGVAddressCreate) -> dict:
    
    _check_request(db, bgv_id)

    existing = db.execute(
        select(BGVAddress).where(
            BGVAddress.bgv_request_id == bgv_id,
            BGVAddress.address_type   == payload.address_type,
            BGVAddress.is_active      == True,
        )
    ).scalars().first()

    if existing:
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return _addr_to_dict(existing)
    else:
        a = BGVAddress(bgv_request_id=bgv_id, **payload.model_dump())
        db.add(a)
        db.commit()
        db.refresh(a)
        return _addr_to_dict(a)




async def send_bgv_email(db: Session, bgv_id: int) -> dict:
    
    r = db.execute(
        select(BGVRequest).where(BGVRequest.id == bgv_id)
    ).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="BGV request not found")

    docs = db.execute(
        select(BGVDocument).where(
            BGVDocument.bgv_request_id == bgv_id,
            BGVDocument.is_active      == True,
        )
    ).scalars().all()

    
    doc_list_html = "".join(
        f"<li>{d.document_name} "
        f"({'<b>Required</b>' if d.document_type.value == 'Required' else 'Optional'})"
        f"</li>"
        for d in docs
    )

    
    template = r.email_template or f"""
    <p>Dear {r.name},</p>
    <p>As part of our standard background verification process, we require the following documents:</p>
    <ul>{doc_list_html}</ul>
    <p>Please submit scanned copies (PDF format) at your earliest convenience.</p>
    <p>You can upload documents through our employee portal or send them via email reply.</p>
    <p>Best regards,<br/>HR Team</p>
    """

    recipients = [r.email]
    cc  = [e.strip() for e in r.cc_emails.split(",")  if e.strip()] if r.cc_emails  else []
    bcc = [e.strip() for e in r.bcc_emails.split(",") if e.strip()] if r.bcc_emails else []

    message = MessageSchema(
        subject=r.subject or "Background Verification - Document Request",
        recipients=recipients,
        body=template,
        subtype=MessageType.html,
        cc=cc,
        bcc=bcc,
    )

    try:
        await FastMail(mail_config).send_message(message)
        r.status   = BGVStatus.in_progress
        r.progress = "Email Sent"
        db.commit()
        return {"message": "Email sent successfully", "to": r.email}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")




def _check_request(db: Session, bgv_id: int):
    r = db.execute(select(BGVRequest).where(BGVRequest.id == bgv_id)).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="BGV request not found")


def _doc_to_dict(d: BGVDocument) -> dict:
    return {
        "id":            d.id,
        "bgvRequestId":  d.bgv_request_id,
        "documentName":  d.document_name,
        "documentType":  d.document_type.value,
        "uploadStatus":  d.upload_status.value,
        "filePath":      d.file_path,
        "uploadedAt":    str(d.uploaded_at) if d.uploaded_at else None,
    }


def _edu_to_dict(e: BGVEducation) -> dict:
    return {
        "id":             e.id,
        "bgvRequestId":   e.bgv_request_id,
        "degree":         e.degree,
        "institution":    e.institution,
        "boardUniversity":e.board_university,
        "yearOfPassing":  e.year_of_passing,
        "percentage":     e.percentage,
    }


def _guardian_to_dict(g: BGVGuardian) -> dict:
    return {
        "id":               g.id,
        "bgvRequestId":     g.bgv_request_id,
        "guardianName":     g.guardian_name,
        "relationship":     g.relationship,
        "phoneNumber":      g.phone_number,
        "employmentStatus": g.employment_status,
        "organization":     g.organization,
        "designation":      g.designation,
        "isLegalGuardian":  g.is_legal_guardian,
    }


def _addr_to_dict(a: BGVAddress) -> dict:
    return {
        "id":            a.id,
        "bgvRequestId":  a.bgv_request_id,
        "addressType":   a.address_type,
        "addressLine1":  a.address_line_1,
        "addressLine2":  a.address_line_2,
        "country":       a.country,
        "state":         a.state,
        "district":      a.district,
        "city":          a.city,
        "pincode":       a.pincode,
        "nationality":   a.nationality,
        "sameAsCurrent": a.same_as_current,
    }