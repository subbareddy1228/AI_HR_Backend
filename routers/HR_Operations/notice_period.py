
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from model.HR_Operations.notice_period import NoticeStatus
from schema.HR_Operations.notice_period import (
    BuyoutApprovalUpdate,
    BuyoutCalculatorRequest,
    BuyoutCalculatorResponse,
    BuyoutRequestCreate,
    BuyoutRequestResponse,
    CounterOfferCreate,
    CounterOfferResponse,
    CounterOfferResponseUpdate,
    DashboardResponse,
    ExtensionApprovalUpdate,
    ExtensionRequestCreate,
    ExtensionRequestResponse,
    LWDCalculatorRequest,
    LWDCalculatorResponse,
    NoticePeriodCreate,
    NoticePeriodResponse,
    NoticePeriodSummary,
    NoticePeriodUpdate,
    ShortfallCalculatorRequest,
    ShortfallCalculatorResponse,
    WaiverApprovalUpdate,
    WaiverRequestCreate,
    WaiverRequestResponse,
    WorkflowStepCreate,
    WorkflowStepResponse,
    WaiverCalculatorRequest,
    WaiverCalculatorResponse,
)
from services.HR_Operations import noticeperiod as svc

router = APIRouter(
    prefix="/notice-period",
    tags=["HR Ops - Notice Period Tracking"],
)


@router.post(
    "/",
    response_model=NoticePeriodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit resignation & create notice period",
)
def create_notice_period(
    payload: NoticePeriodCreate,
    db: Session = Depends(get_db),
):
    return svc.create_notice_period(db, payload)


@router.get(
    "/",
    response_model=List[NoticePeriodSummary],
    summary="List notice periods (filterable)",
)
def list_notice_periods(
    status_filter: Optional[NoticeStatus] = Query(None, alias="status"),
    employee_id:   Optional[int]           = Query(None),
    skip:          int                     = Query(0,  ge=0),
    limit:         int                     = Query(50, ge=1, le=200),
    db:            Session                 = Depends(get_db),
):
    return svc.list_notice_periods(db, status_filter, employee_id, skip, limit)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Dashboard — stats + countdown tracker",
)
def dashboard(db: Session = Depends(get_db)):
    return svc.get_dashboard(db)


@router.get(
    "/{notice_id}",
    response_model=NoticePeriodResponse,
    summary="Get single notice period",
)
def get_notice_period(notice_id: int, db: Session = Depends(get_db)):
    return svc.get_notice_period(db, notice_id)


@router.patch(
    "/{notice_id}",
    response_model=NoticePeriodResponse,
    summary="Update notice period",
)
def update_notice_period(
    notice_id: int,
    payload:   NoticePeriodUpdate,
    db:        Session = Depends(get_db),
):
    return svc.update_notice_period(db, notice_id, payload)


@router.delete(
    "/{notice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notice period (non-SERVING only)",
)
def delete_notice_period(notice_id: int, db: Session = Depends(get_db)):
    svc.delete_notice_period(db, notice_id)


@router.post(
    "/buyout",
    response_model=BuyoutRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notice buyout request",
)
def create_buyout(payload: BuyoutRequestCreate, db: Session = Depends(get_db)):
    return svc.create_buyout_request(db, payload)


@router.get(
    "/buyout",
    response_model=List[BuyoutRequestResponse],
    summary="List buyout requests",
)
def list_buyouts(
    notice_period_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.list_buyout_requests(db, notice_period_id)


@router.patch(
    "/buyout/{buyout_id}/approve",
    response_model=BuyoutRequestResponse,
    summary="Manager / HR / Finance approval step for buyout",
)
def approve_buyout(
    buyout_id: int,
    payload:   BuyoutApprovalUpdate,
    db:        Session = Depends(get_db),
):
    return svc.process_buyout_approval(db, buyout_id, payload)

@router.post(
    "/waiver",
    response_model=WaiverRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notice waiver request",
)
def create_waiver(payload: WaiverRequestCreate, db: Session = Depends(get_db)):
    return svc.create_waiver_request(db, payload)


@router.get(
    "/waiver",
    response_model=List[WaiverRequestResponse],
    summary="List waiver requests",
)
def list_waivers(
    notice_period_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.list_waiver_requests(db, notice_period_id)


@router.patch(
    "/waiver/{waiver_id}/approve",
    response_model=WaiverRequestResponse,
    summary="Manager / HR / Director approval step for waiver",
)
def approve_waiver(
    waiver_id: int,
    payload:   WaiverApprovalUpdate,
    db:        Session = Depends(get_db),
):
    return svc.process_waiver_approval(db, waiver_id, payload)


@router.post(
    "/counter-offer",
    response_model=CounterOfferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send counter offer to resigning employee",
)
def create_counter_offer(payload: CounterOfferCreate, db: Session = Depends(get_db)):
    return svc.create_counter_offer(db, payload)


@router.get(
    "/counter-offer",
    response_model=List[CounterOfferResponse],
    summary="List counter offers",
)
def list_counter_offers(
    notice_period_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.list_counter_offers(db, notice_period_id)


@router.patch(
    "/counter-offer/{offer_id}/respond",
    response_model=CounterOfferResponse,
    summary="Employee accepts or rejects counter offer",
)
def respond_to_counter_offer(
    offer_id: int,
    payload:  CounterOfferResponseUpdate,
    db:       Session = Depends(get_db),
):
    return svc.respond_to_counter_offer(db, offer_id, payload)


@router.post(
    "/extension",
    response_model=ExtensionRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notice extension request",
)
def create_extension(payload: ExtensionRequestCreate, db: Session = Depends(get_db)):
    return svc.create_extension_request(db, payload)


@router.get(
    "/extension",
    response_model=List[ExtensionRequestResponse],
    summary="List extension requests",
)
def list_extensions(
    notice_period_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.list_extension_requests(db, notice_period_id)


@router.patch(
    "/extension/{extension_id}/approve",
    response_model=ExtensionRequestResponse,
    summary="Approve or reject extension request",
)
def approve_extension(
    extension_id: int,
    payload:      ExtensionApprovalUpdate,
    db:           Session = Depends(get_db),
):
    return svc.process_extension_approval(db, extension_id, payload)

@router.get(
    "/{notice_id}/workflow",
    response_model=List[WorkflowStepResponse],
    summary="Get full resignation workflow timeline",
)
def get_workflow(notice_id: int, db: Session = Depends(get_db)):
    return svc.get_workflow(db, notice_id)


@router.post(
    "/workflow",
    response_model=WorkflowStepResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a workflow step (manual advance)",
)
def add_workflow_step(payload: WorkflowStepCreate, db: Session = Depends(get_db)):
    return svc.add_workflow_step(db, payload)


@router.post(
    "/calc/lwd",
    response_model=LWDCalculatorResponse,
    summary="Last Working Day calculator",
)
def calculator_lwd(payload: LWDCalculatorRequest, db: Session = Depends(get_db)):
    return svc.calc_lwd(db, payload)


@router.post(
    "/calc/buyout",
    response_model=BuyoutCalculatorResponse,
    summary="Buyout amount calculator",
)
def calculator_buyout(payload: BuyoutCalculatorRequest, db: Session = Depends(get_db)):
    return svc.calc_buyout(db, payload)


@router.post(
    "/calc/waiver",
    response_model=WaiverCalculatorResponse,
    summary="Waiver eligibility calculator",
)
def calculator_waiver(payload: WaiverCalculatorRequest, db: Session = Depends(get_db)):
    return svc.calc_waiver(db, payload)


@router.post(
    "/calc/shortfall",
    response_model=ShortfallCalculatorResponse,
    summary="Notice shortfall amount calculator",
)
def calculator_shortfall(payload: ShortfallCalculatorRequest, db: Session = Depends(get_db)):
    return svc.calc_shortfall(db, payload)
