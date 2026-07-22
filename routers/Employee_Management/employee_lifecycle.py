
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from core.database import get_db
from schema.Employee_Management.employee_lifecycle import (

    LifecycleEventCreate, LifecycleEventUpdate, LifecycleEventResponse,
    LifecycleAnalyticsResponse,
    OnboardingTaskCreate, OnboardingTaskUpdate, OnboardingTaskResponse,
    ProbationReviewCreate, ProbationReviewUpdate, ProbationReviewResponse,
    TransferRequestCreate, TransferRequestUpdate, TransferRequestResponse,
    ExitProcessCreate, ExitProcessUpdate, ExitProcessWithClearance,
    ContractRenewalCreate, ContractRenewalUpdate, ContractRenewalResponse,
    LifecycleDashboardResponse, ExitAnalyticsResponse,
)
from services.Employee_Management.employee_lifecycle_service import (

    log_lifecycle_event, get_employee_lifecycle, get_lifecycle_event,
    update_lifecycle_event, delete_lifecycle_event,
    get_lifecycle_analytics, get_all_events_by_type,
    create_onboarding_task, list_onboarding_tasks, get_onboarding_task,
    update_onboarding_task, complete_onboarding_task, delete_onboarding_task,
    create_probation_review, list_probation_reviews, get_probation_review,
    update_probation_review, start_probation_review, complete_probation_review,
    create_transfer_request, list_transfer_requests, get_transfer_request,
    update_transfer_request, approve_transfer, reject_transfer, delete_transfer_request,
    initiate_exit, list_exit_processes, get_exit_process,
    update_exit_process, generate_relieving_letter, delete_exit_process,
    create_contract_renewal, list_contract_renewals, get_contract_renewal,
    update_contract_renewal, delete_contract_renewal,
    get_lifecycle_dashboard, get_exit_analytics,
)

router = APIRouter(prefix="/lifecycle", tags=["Employee Management"])


@router.get(
    "/dashboard",
    response_model=LifecycleDashboardResponse,
    summary="Lifecycle dashboard KPI summary",
)
def lifecycle_dashboard(db: Session = Depends(get_db)):
    """Returns all KPI counts for the Lifecycle Dashboard tab."""
    return get_lifecycle_dashboard(db)



@router.post(
    "/onboarding-tasks",
    response_model=OnboardingTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an onboarding checklist task",
)
def create_task(payload: OnboardingTaskCreate, db: Session = Depends(get_db)):
    return create_onboarding_task(db, payload)


@router.get(
    "/onboarding-tasks",
    response_model=List[OnboardingTaskResponse],
    summary="List onboarding tasks (all or filtered by employee/status)",
)
def list_tasks(
    employee_id: Optional[int] = Query(None),
    task_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    return list_onboarding_tasks(db, employee_id, task_status)


@router.get(
    "/onboarding-tasks/{task_id}",
    response_model=OnboardingTaskResponse,
    summary="Get a single onboarding task",
)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return get_onboarding_task(db, task_id)


@router.put(
    "/onboarding-tasks/{task_id}",
    response_model=OnboardingTaskResponse,
    summary="Update an onboarding task",
)
def update_task(task_id: int, payload: OnboardingTaskUpdate, db: Session = Depends(get_db)):
    return update_onboarding_task(db, task_id, payload)


@router.patch(
    "/onboarding-tasks/{task_id}/complete",
    response_model=OnboardingTaskResponse,
    summary="Mark an onboarding task as completed",
)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    return complete_onboarding_task(db, task_id)


@router.delete(
    "/onboarding-tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an onboarding task",
)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    delete_onboarding_task(db, task_id)


@router.post(
    "/probation-reviews",
    response_model=ProbationReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a probation review",
)
def create_review(payload: ProbationReviewCreate, db: Session = Depends(get_db)):
    return create_probation_review(db, payload)


@router.get(
    "/probation-reviews",
    response_model=List[ProbationReviewResponse],
    summary="List probation reviews",
)
def list_reviews(
    employee_id: Optional[int] = Query(None),
    review_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    return list_probation_reviews(db, employee_id, review_status)


@router.get(
    "/probation-reviews/{review_id}",
    response_model=ProbationReviewResponse,
    summary="Get a single probation review",
)
def get_review(review_id: int, db: Session = Depends(get_db)):
    return get_probation_review(db, review_id)


@router.put(
    "/probation-reviews/{review_id}",
    response_model=ProbationReviewResponse,
    summary="Update a probation review",
)
def update_review(review_id: int, payload: ProbationReviewUpdate, db: Session = Depends(get_db)):
    return update_probation_review(db, review_id, payload)


@router.patch(
    "/probation-reviews/{review_id}/start",
    response_model=ProbationReviewResponse,
    summary="Start a probation review (set to in-progress)",
)
def start_review(review_id: int, db: Session = Depends(get_db)):
    return start_probation_review(db, review_id)


@router.patch(
    "/probation-reviews/{review_id}/complete",
    response_model=ProbationReviewResponse,
    summary="Complete a probation review with a rating",
)
def complete_review(
    review_id: int,
    rating: str = Query(..., description="e.g. Meets Expectations"),
    db: Session = Depends(get_db),
):
    return complete_probation_review(db, review_id, rating)


@router.post(
    "/transfers",
    response_model=TransferRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a transfer request",
)
def create_transfer(payload: TransferRequestCreate, db: Session = Depends(get_db)):
    return create_transfer_request(db, payload)


@router.get(
    "/transfers",
    response_model=List[TransferRequestResponse],
    summary="List transfer requests",
)
def list_transfers(
    employee_id: Optional[int] = Query(None),
    transfer_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    return list_transfer_requests(db, employee_id, transfer_status)


@router.get(
    "/transfers/{transfer_id}",
    response_model=TransferRequestResponse,
    summary="Get a single transfer request",
)
def get_transfer(transfer_id: int, db: Session = Depends(get_db)):
    return get_transfer_request(db, transfer_id)


@router.put(
    "/transfers/{transfer_id}",
    response_model=TransferRequestResponse,
    summary="Update a transfer request",
)
def update_transfer(transfer_id: int, payload: TransferRequestUpdate, db: Session = Depends(get_db)):
    return update_transfer_request(db, transfer_id, payload)


@router.patch(
    "/transfers/{transfer_id}/approve",
    response_model=TransferRequestResponse,
    summary="Approve a transfer request",
)
def approve_transfer_route(
    transfer_id: int,
    approver_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return approve_transfer(db, transfer_id, approver_id)


@router.patch(
    "/transfers/{transfer_id}/reject",
    response_model=TransferRequestResponse,
    summary="Reject a transfer request",
)
def reject_transfer_route(
    transfer_id: int,
    remarks: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return reject_transfer(db, transfer_id, remarks)


@router.delete(
    "/transfers/{transfer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a transfer request",
)
def delete_transfer(transfer_id: int, db: Session = Depends(get_db)):
    delete_transfer_request(db, transfer_id)



@router.post(
    "/exits",
    response_model=ExitProcessWithClearance,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate exit process for an employee",
)
def initiate_exit_route(payload: ExitProcessCreate, db: Session = Depends(get_db)):
    return initiate_exit(db, payload)


@router.get(
    "/exits",
    response_model=List[ExitProcessWithClearance],
    summary="List exit processes",
)
def list_exits(
    employee_id: Optional[int] = Query(None),
    exit_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    return list_exit_processes(db, employee_id, exit_status)


@router.get(
    "/exits/{exit_id}",
    response_model=ExitProcessWithClearance,
    summary="Get a single exit process",
)
def get_exit(exit_id: int, db: Session = Depends(get_db)):
    return get_exit_process(db, exit_id)


@router.put(
    "/exits/{exit_id}",
    response_model=ExitProcessWithClearance,
    summary="Update exit process (clearances, dates, status)",
)
def update_exit(exit_id: int, payload: ExitProcessUpdate, db: Session = Depends(get_db)):
    return update_exit_process(db, exit_id, payload)


@router.patch(
    "/exits/{exit_id}/relieving-letter",
    response_model=ExitProcessWithClearance,
    summary="Generate relieving letter for employee",
)
def relieving_letter(exit_id: int, db: Session = Depends(get_db)):
    return generate_relieving_letter(db, exit_id)


@router.delete(
    "/exits/{exit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an exit process",
)
def delete_exit(exit_id: int, db: Session = Depends(get_db)):
    delete_exit_process(db, exit_id)

@router.post(
    "/contracts",
    response_model=ContractRenewalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a contract renewal record",
)
def create_contract(payload: ContractRenewalCreate, db: Session = Depends(get_db)):
    return create_contract_renewal(db, payload)


@router.get(
    "/contracts",
    response_model=List[ContractRenewalResponse],
    summary="List contract renewals",
)
def list_contracts(
    employee_id: Optional[int] = Query(None),
    renewal_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return list_contract_renewals(db, employee_id, renewal_status)


@router.get(
    "/contracts/{contract_id}",
    response_model=ContractRenewalResponse,
    summary="Get a single contract renewal",
)
def get_contract(contract_id: int, db: Session = Depends(get_db)):
    return get_contract_renewal(db, contract_id)


@router.put(
    "/contracts/{contract_id}",
    response_model=ContractRenewalResponse,
    summary="Update a contract renewal",
)
def update_contract(contract_id: int, payload: ContractRenewalUpdate, db: Session = Depends(get_db)):
    return update_contract_renewal(db, contract_id, payload)


@router.delete(
    "/contracts/{contract_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a contract renewal",
)
def delete_contract(contract_id: int, db: Session = Depends(get_db)):
    delete_contract_renewal(db, contract_id)


@router.get(
    "/reports/exit-analytics",
    response_model=ExitAnalyticsResponse,
    summary="Exit analytics: attrition rate, voluntary/involuntary counts, top reasons",
)
def exit_analytics(db: Session = Depends(get_db)):
    return get_exit_analytics(db)


@router.get(
    "/report/by-type",
    response_model=List[LifecycleEventResponse],
    summary="Get all lifecycle events of a specific type (org-wide report)",
)
def report_by_type(
    event_type: str = Query(..., description="e.g. Promotion, Resignation, Transfer"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    return get_all_events_by_type(db, event_type, from_date, to_date)


@router.post(
    "/",
    response_model=LifecycleEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a core lifecycle event (joining, promotion, etc.)",
)
def create_lifecycle_event(payload: LifecycleEventCreate, db: Session = Depends(get_db)):
    return log_lifecycle_event(db, payload)


@router.get(
    "/employee/{employee_id}",
    response_model=List[LifecycleEventResponse],
    summary="Get all lifecycle events for an employee",
)
def list_employee_lifecycle(
    employee_id: int,
    event_type: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    return get_employee_lifecycle(db, employee_id, event_type, from_date, to_date)


@router.get(
    "/employee/{employee_id}/analytics",
    response_model=LifecycleAnalyticsResponse,
    summary="Get lifecycle analytics for an employee",
)
def lifecycle_analytics(employee_id: int, db: Session = Depends(get_db)):
    return get_lifecycle_analytics(db, employee_id)


@router.get(
    "/event/{event_id}",
    response_model=LifecycleEventResponse,
    summary="Get a single lifecycle event by ID",
)
def get_event(event_id: int, db: Session = Depends(get_db)):
    return get_lifecycle_event(db, event_id)


@router.put(
    "/event/{event_id}",
    response_model=LifecycleEventResponse,
    summary="Update a lifecycle event",
)
def update_event(event_id: int, payload: LifecycleEventUpdate, db: Session = Depends(get_db)):
    return update_lifecycle_event(db, event_id, payload)


@router.delete(
    "/event/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a lifecycle event",
)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    delete_lifecycle_event(db, event_id)
