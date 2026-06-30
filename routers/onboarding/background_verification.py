from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from schema.onboarding.background_verification import (
    BGVRequestCreate, BGVRequestUpdate,
    BGVEducationCreate, BGVGuardianCreate, BGVAddressCreate,
    BGVKPISchema,
)
from services.background_verification import (
    get_bgv_kpi,
    list_bgv_requests,
    get_bgv_request,
    create_bgv_request,
    update_bgv_request,
    delete_bgv_request,
    upload_bgv_document,
    add_education,
    delete_education,
    save_guardian,
    save_address,
    send_bgv_email,
)

router = APIRouter(
    prefix="/background-verification",
    tags=["Background Verification"],
)



@router.get("/kpi", response_model=BGVKPISchema)
def get_kpi(db: Session = Depends(get_db)):
    return get_bgv_kpi(db)


@router.get("/")
def list_requests(
    db:            Session        = Depends(get_db),
    search:        Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),   
    skip:          int            = Query(0),
    limit:         int            = Query(50),
):
    return list_bgv_requests(db, search, status_filter, skip, limit)



@router.get("/{bgv_id}")
def get_request(bgv_id: int, db: Session = Depends(get_db)):
    return get_bgv_request(db, bgv_id)



@router.post("/", status_code=201)
def create_request(payload: BGVRequestCreate, db: Session = Depends(get_db)):
    return create_bgv_request(db, payload)



@router.patch("/{bgv_id}")
def update_request(
    bgv_id:  int,
    payload: BGVRequestUpdate,
    db:      Session = Depends(get_db),
):
    return update_bgv_request(db, bgv_id, payload)



@router.delete("/{bgv_id}")
def delete_request(bgv_id: int, db: Session = Depends(get_db)):
    return delete_bgv_request(db, bgv_id)


@router.post("/{bgv_id}/documents/{doc_id}/upload")
def upload_document(
    bgv_id: int,
    doc_id: int,
    file:   UploadFile = File(...),
    db:     Session    = Depends(get_db),
):
    return upload_bgv_document(db, bgv_id, doc_id, file)



@router.post("/{bgv_id}/education", status_code=201)
def add_education_record(
    bgv_id:  int,
    payload: BGVEducationCreate,
    db:      Session = Depends(get_db),
):
    return add_education(db, bgv_id, payload)


@router.delete("/{bgv_id}/education/{edu_id}")
def delete_education_record(
    bgv_id: int,
    edu_id: int,
    db:     Session = Depends(get_db),
):
    return delete_education(db, bgv_id, edu_id)



@router.post("/{bgv_id}/guardian")
def save_guardian_details(
    bgv_id:  int,
    payload: BGVGuardianCreate,
    db:      Session = Depends(get_db),
):
    return save_guardian(db, bgv_id, payload)



@router.post("/{bgv_id}/address")
def save_address_details(
    bgv_id:  int,
    payload: BGVAddressCreate,
    db:      Session = Depends(get_db),
):
    return save_address(db, bgv_id, payload)



@router.post("/{bgv_id}/send-email")
async def send_email(bgv_id: int, db: Session = Depends(get_db)):
    return await send_bgv_email(db, bgv_id)