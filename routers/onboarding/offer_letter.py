from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from model.models import User

import services.offer_letter_service as svc

from schema.onboarding.offer_letter import (
    OfferAnalyticsSchema,
    OfferBulkActionSchema,
    OfferCreateSchema,
    OfferFilterParams,
    OfferKPISchema,
    OfferListItemSchema,
    OfferStatusActionSchema,
    OfferTabCountsSchema,
    OfferUpdateSchema,
    SendOfferEmailSchema,
)

router = APIRouter(prefix="/offer-letters", tags=["Offer Letters"])




@router.get("/kpi", response_model=OfferKPISchema)
def get_kpi(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    return svc.get_offer_kpi(db)


@router.get("/tab-counts", response_model=OfferTabCountsSchema)
def get_tab_counts(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    return svc.get_tab_counts(db)




@router.get("/analytics", response_model=OfferAnalyticsSchema)
def get_analytics(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    return svc.get_offer_analytics(db)




@router.get("/export")
def export_offers(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
   
    import csv, io

    rows   = svc.export_offers(db, user)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys() if rows else [])
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=offers.csv"},
    )




@router.post("/bulk-action")
def bulk_action(
    payload: OfferBulkActionSchema,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    return svc.bulk_action(db, payload, user)




@router.get("", response_model=List[OfferListItemSchema])
def list_offers(
    search:      Optional[str] = Query(None, description="Candidate name / position / email"),
    status:      Optional[str] = Query(None, description="All Status | Draft | Pending Approval | Approved | Sent | Accepted | Declined | Expired | Withdrawn"),
    department:  Optional[str] = Query(None, description="All Departments | Engineering | …"),
    offer_type:  Optional[str] = Query(None, description="All Offer Types | Full-time | Part-time | Internship | Contract"),
    skip:        int           = Query(0, ge=0),
    limit:       int           = Query(20, ge=1, le=200),
    db:          Session       = Depends(get_db),
    user:        User          = Depends(get_current_user),
):
    return svc.list_offers(db, user, search, status, department, offer_type, skip, limit)




@router.get("/{offer_id}", response_model=OfferListItemSchema)
def get_offer(
    offer_id: int,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    return svc.get_offer_detail(db, offer_id, user)



@router.post("", response_model=OfferListItemSchema, status_code=201)
def create_offer(
    payload: OfferCreateSchema,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    return svc.create_offer(db, payload, user)




@router.put("/{offer_id}", response_model=OfferListItemSchema)
def update_offer(
    offer_id: int,
    payload:  OfferUpdateSchema,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    return svc.update_offer(db, offer_id, payload, user)




@router.post("/{offer_id}/action", response_model=OfferListItemSchema)
def status_action(
    offer_id: int,
    payload:  OfferStatusActionSchema,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    return svc.process_status_action(db, offer_id, payload, user)




@router.post("/{offer_id}/send-email")
def send_offer_email(
    offer_id: int,
    payload:  SendOfferEmailSchema,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    payload.offer_id = offer_id
    return svc.send_offer_email(db, payload, user)




@router.post("/{offer_id}/duplicate", response_model=OfferListItemSchema, status_code=201)
def duplicate_offer(
    offer_id: int,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
   
    return svc.duplicate_offer(db, offer_id, user)




@router.delete("/{offer_id}")
def delete_offer(
    offer_id: int,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    
    return svc.delete_offer(db, offer_id, user)
