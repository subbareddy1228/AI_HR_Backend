from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
import services.HR_Operations.promotions_service as svc

from schema.HR_Operations.promotion import (
    
    CareerPageSummarySchema,
   
    ProbationKPISchema,
    ProbationRowSchema,
    ProbationDetailSchema,
    ProbationCreateSchema,
    ProbationUpdateSchema,
    ProbationMilestoneUpdateSchema,
    ProbationBulkActionSchema,
    
    ConfirmationKPISchema,
    ConfirmationRowSchema,
    ConfirmationActionSchema,
    ConfirmationBulkSchema,
   
    PromotionKPISchema,
    PromotionRowSchema,
    PromotionCreateSchema,
    PromotionUpdateSchema,
    PromotionApprovalSchema,
    PromotionBulkActionSchema,
   
    BuddyKPISchema,
    BuddyRowSchema,
    BuddyAssignmentSchema,
    BuddyFeedbackSchema,
    BuddyBulkActionSchema,
)

router = APIRouter(prefix="/career", tags=["Promotions & Career"])




@router.get("/summary", response_model=CareerPageSummarySchema)
def get_page_summary(db: Session = Depends(get_db)):
   
    return svc.get_page_summary(db)




@router.get("/probation/kpi", response_model=ProbationKPISchema)
def probation_kpi(db: Session = Depends(get_db)):
    
    return svc.get_probation_kpi(db)


@router.get("/probation", response_model=List[ProbationRowSchema])
def list_probation(
    search:     Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    skip:       int           = Query(0, ge=0),
    limit:      int           = Query(10, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return svc.list_probation(db, search, department, location, status, skip, limit)


@router.get("/probation/{confirmation_id}", response_model=ProbationDetailSchema)
def get_probation(confirmation_id: int, db: Session = Depends(get_db)):
    return svc.get_probation_detail(db, confirmation_id)


@router.post("/probation", response_model=ProbationDetailSchema, status_code=201)
def create_probation(payload: ProbationCreateSchema, db: Session = Depends(get_db)):
    return svc.create_probation(db, payload)


@router.patch("/probation/{confirmation_id}", response_model=ProbationDetailSchema)
def update_probation(
    confirmation_id: int,
    payload: ProbationUpdateSchema,
    db: Session = Depends(get_db),
):
    return svc.update_probation(db, confirmation_id, payload)


@router.post("/probation/milestone", response_model=ProbationDetailSchema)
def complete_milestone(payload: ProbationMilestoneUpdateSchema, db: Session = Depends(get_db)):
    
    return svc.complete_milestone(db, payload)


@router.post("/probation/bulk-action")
def probation_bulk(payload: ProbationBulkActionSchema, db: Session = Depends(get_db)):
    
    return svc.probation_bulk_action(db, payload)




@router.get("/confirmation/kpi", response_model=ConfirmationKPISchema)
def confirmation_kpi(db: Session = Depends(get_db)):
    
    return svc.get_confirmation_kpi(db)


@router.get("/confirmation", response_model=List[ConfirmationRowSchema])
def list_confirmations(
    search:     Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    skip:       int           = Query(0, ge=0),
    limit:      int           = Query(10, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return svc.list_confirmations(db, search, department, location, status, skip, limit)


@router.get("/confirmation/{confirmation_id}", response_model=ConfirmationRowSchema)
def get_confirmation(confirmation_id: int, db: Session = Depends(get_db)):
    return svc.get_confirmation_detail(db, confirmation_id)


@router.post("/confirmation/{confirmation_id}/approve", response_model=ConfirmationRowSchema)
def approve_confirmation(
    confirmation_id: int,
    payload: ConfirmationActionSchema,
    db: Session = Depends(get_db),
):
    return svc.process_confirmation_approval(db, confirmation_id, payload)


@router.post("/confirmation/bulk-action")
def confirmation_bulk(payload: ConfirmationBulkSchema, db: Session = Depends(get_db)):
    
    return svc.confirmation_bulk_action(db, payload)




@router.get("/promotions/kpi", response_model=PromotionKPISchema)
def promotion_kpi(db: Session = Depends(get_db)):
    
    return svc.get_promotion_kpi(db)


@router.get("/promotions", response_model=List[PromotionRowSchema])
def list_promotions(
    search:     Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    skip:       int           = Query(0, ge=0),
    limit:      int           = Query(10, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return svc.list_promotions(db, search, department, location, status, skip, limit)


@router.get("/promotions/{promotion_id}", response_model=PromotionRowSchema)
def get_promotion(promotion_id: int, db: Session = Depends(get_db)):
    return svc.get_promotion_detail(db, promotion_id)


@router.post("/promotions", response_model=PromotionRowSchema, status_code=201)
def create_promotion(payload: PromotionCreateSchema, db: Session = Depends(get_db)):
   
    return svc.create_promotion(db, payload)


@router.patch("/promotions/{promotion_id}", response_model=PromotionRowSchema)
def update_promotion(
    promotion_id: int,
    payload: PromotionUpdateSchema,
    db: Session = Depends(get_db),
):
    
    return svc.update_promotion(db, promotion_id, payload)


@router.post("/promotions/{promotion_id}/approve", response_model=PromotionRowSchema)
def approve_promotion_step(
    promotion_id: int,
    payload: PromotionApprovalSchema,
    db: Session = Depends(get_db),
):
    return svc.approve_promotion_step(db, promotion_id, payload)


@router.post("/promotions/bulk-action")
def promotion_bulk(payload: PromotionBulkActionSchema, db: Session = Depends(get_db)):
    
    return svc.promotion_bulk_action(db, payload)




@router.get("/buddy/kpi", response_model=BuddyKPISchema)
def buddy_kpi(db: Session = Depends(get_db)):
   
    return svc.get_buddy_kpi(db)


@router.get("/buddy", response_model=List[BuddyRowSchema])
def list_buddies(
    search:     Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    skip:       int           = Query(0, ge=0),
    limit:      int           = Query(10, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return svc.list_buddies(db, search, department, location, status, skip, limit)


@router.post("/buddy/assign")
def assign_buddy(payload: BuddyAssignmentSchema, db: Session = Depends(get_db)):
    
    return svc.assign_buddy(db, payload)


@router.post("/buddy/feedback")
def submit_feedback(payload: BuddyFeedbackSchema, db: Session = Depends(get_db)):
    
    return svc.submit_buddy_feedback(db, payload)


@router.get("/buddy/report")
def buddy_report(db: Session = Depends(get_db)):
    
    return svc.get_buddy_report(db)


@router.post("/buddy/bulk-action")
def buddy_bulk(payload: BuddyBulkActionSchema, db: Session = Depends(get_db)):
    
    return svc.buddy_bulk_action(db, payload)