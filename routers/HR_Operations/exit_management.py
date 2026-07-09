

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
import schema.HR_Operations.exit_management as schemas
import services.HR_Operations.exit_management_service as svc

router = APIRouter(prefix="/exit-management", tags=["Exit Management"])


@router.get("/kpi", response_model=schemas.ExitKPISummary, summary="Exit Management KPI Summary")
def get_kpi(db: Session = Depends(get_db)):

    return svc.get_exit_case_kpi(db)


@router.get(
    "/",
    response_model=schemas.PaginatedExitCases,
    summary="List Exit Cases",
)
def list_exit_cases(
    status: Optional[str]     = Query(None, description="Filter by case status"),
    department: Optional[str] = Query(None, description="Filter by department"),
    exit_reason: Optional[str]= Query(None, description="Filter by exit reason"),
    location: Optional[str]   = Query(None, description="Filter by location"),
    from_date: Optional[date] = Query(None, description="Resignation date from (YYYY-MM-DD)"),
    to_date: Optional[date]   = Query(None, description="Resignation date to (YYYY-MM-DD)"),
    search: Optional[str]     = Query(None, description="Search employee name or code"),
    page: int                 = Query(1, ge=1),
    page_size: int            = Query(10, ge=1, le=100),
    db: Session               = Depends(get_db),
):
    return svc.list_exit_cases(
        db,
        status=status,
        department=department,
        exit_reason=exit_reason,
        location=location,
        from_date=from_date,
        to_date=to_date,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/export", summary="Export Exit Cases to CSV")
def export_exit_cases(
    status: Optional[str]     = Query(None),
    department: Optional[str] = Query(None),
    db: Session               = Depends(get_db),
):
    csv_data = svc.export_exit_cases_csv(db, status=status, department=department)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=exit_cases.csv"},
    )


@router.post(
    "/",
    response_model=schemas.InitiateExitResponse,
    status_code=201,
    summary="Initiate New Exit Case",
)
def initiate_exit(
    payload: schemas.ExitCaseCreate,
    db: Session = Depends(get_db),
):

    return svc.initiate_exit(db, payload)


@router.get(
    "/{exit_case_id}",
    response_model=schemas.ExitCaseDetailResponse,
    summary="Get Exit Case Detail",
)
def get_exit_case(exit_case_id: int, db: Session = Depends(get_db)):
  
    return svc.get_exit_case_detail(db, exit_case_id)


@router.patch(
    "/{exit_case_id}",
    response_model=schemas.ExitCaseResponse,
    summary="Update Exit Case",
)
def update_exit_case(
    exit_case_id: int,
    payload: schemas.ExitCaseUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_exit_case(db, exit_case_id, payload)


@router.post(
    "/{exit_case_id}/close",
    response_model=schemas.ExitCaseResponse,
    summary="Close Exit Case",
)
def close_exit_case(
    exit_case_id: int,
    payload: schemas.CloseExitRequest,
    db: Session = Depends(get_db),
):

    return svc.close_exit_case(db, exit_case_id, payload)


@router.post(
    "/{exit_case_id}/cancel",
    response_model=schemas.ExitCaseResponse,
    summary="Cancel Exit Case",
)
def cancel_exit_case(
    exit_case_id: int,
    remarks: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.cancel_exit_case(db, exit_case_id, remarks=remarks)


@router.delete(
    "/{exit_case_id}",
    summary="Delete Exit Case",
)
def delete_exit_case(exit_case_id: int, db: Session = Depends(get_db)):
    """Hard delete — only allowed for Initiated or Cancelled cases."""
    return svc.delete_exit_case(db, exit_case_id)


@router.get(
    "/{exit_case_id}/clearance",
    response_model=List[schemas.ClearanceItemResponse],
    summary="List Clearance Items for an Exit Case",
)
def list_clearance_items(exit_case_id: int, db: Session = Depends(get_db)):
    return svc.list_clearance_items(db, exit_case_id)


@router.patch(
    "/clearance/{item_id}",
    response_model=schemas.ClearanceItemResponse,
    summary="Update a Clearance Item",
)
def update_clearance_item(
    item_id: int,
    payload: schemas.ClearanceItemUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_clearance_item(db, item_id, payload)


@router.patch(
    "/clearance/bulk-update",
    summary="Bulk Update Clearance Items",
)
def bulk_update_clearance(
    payload: schemas.BulkClearanceUpdateRequest,
    db: Session = Depends(get_db),
):
    return svc.bulk_update_clearance_items(db, payload)


@router.post(
    "/{exit_case_id}/interview",
    response_model=schemas.ExitInterviewResponse,
    status_code=201,
    summary="Create Exit Interview",
)
def create_exit_interview(
    exit_case_id: int,
    payload: schemas.ExitInterviewCreate,
    db: Session = Depends(get_db),
):
    if payload.exit_case_id != exit_case_id:
        raise HTTPException(status_code=422, detail="exit_case_id mismatch in path and body")
    return svc.create_exit_interview(db, payload)


@router.get(
    "/{exit_case_id}/interview",
    response_model=schemas.ExitInterviewResponse,
    summary="Get Exit Interview",
)
def get_exit_interview(exit_case_id: int, db: Session = Depends(get_db)):
    return svc.get_exit_interview(db, exit_case_id)


@router.patch(
    "/interview/{interview_id}",
    response_model=schemas.ExitInterviewResponse,
    summary="Update Exit Interview",
)
def update_exit_interview(
    interview_id: int,
    payload: schemas.ExitInterviewUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_exit_interview(db, interview_id, payload)


@router.get(
    "/settlements",
    response_model=schemas.PaginatedSettlements,
    summary="List Settlements",
)
def list_settlements(
    department: Optional[str] = Query(None),
    status: Optional[str]     = Query(None),
    search: Optional[str]     = Query(None),
    page: int                 = Query(1, ge=1),
    page_size: int            = Query(10, ge=1, le=100),
    db: Session               = Depends(get_db),
):
    return svc.list_settlements(db, department=department, status=status, search=search, page=page, page_size=page_size)


@router.get("/settlements/export", summary="Export Settlements to CSV")
def export_settlements(
    status: Optional[str] = Query(None),
    db: Session           = Depends(get_db),
):
    csv_data = svc.export_settlements_csv(db, status=status)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=settlements.csv"},
    )


@router.post(
    "/settlements/calculate",
    response_model=schemas.ExitSettlementCreate,
    summary="Auto-Calculate Settlement (Dry Run)",
)
def calculate_settlement(
    req: schemas.SettlementCalculateRequest,
    db: Session = Depends(get_db),
):
    
    return svc.auto_calculate_settlement(db, req)


@router.post(
    "/settlements",
    response_model=schemas.ExitSettlementResponse,
    status_code=201,
    summary="Create Settlement",
)
def create_settlement(
    payload: schemas.ExitSettlementCreate,
    db: Session = Depends(get_db),
):
    return svc.create_settlement(db, payload)


@router.get(
    "/settlements/{settlement_id}",
    response_model=schemas.ExitSettlementResponse,
    summary="Get Settlement",
)
def get_settlement(settlement_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import select as sa_select
    from model.HR_Operations.exit_management import ExitSettlement
    s = db.execute(sa_select(ExitSettlement).where(ExitSettlement.id == settlement_id)).scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return schemas.ExitSettlementResponse.model_validate(s)


@router.patch(
    "/settlements/{settlement_id}",
    response_model=schemas.ExitSettlementResponse,
    summary="Update Settlement",
)
def update_settlement(
    settlement_id: int,
    payload: schemas.ExitSettlementUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_settlement(db, settlement_id, payload)


@router.post(
    "/settlements/{settlement_id}/approve",
    response_model=schemas.ExitSettlementResponse,
    summary="Approve Settlement",
)
def approve_settlement(
    settlement_id: int,
    payload: schemas.ApproveSettlementRequest,
    db: Session = Depends(get_db),
):
    return svc.approve_settlement(db, settlement_id, payload)


@router.post(
    "/settlements/{settlement_id}/mark-paid",
    response_model=schemas.ExitSettlementResponse,
    summary="Mark Settlement as Paid",
)
def mark_settlement_paid(
    settlement_id: int,
    payment_reference: str = Query(..., description="Bank transfer / payment reference"),
    payment_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.mark_settlement_paid(db, settlement_id, payment_reference, payment_date)


@router.get(
    "/alumni",
    response_model=schemas.PaginatedAlumni,
    summary="List Alumni",
)
def list_alumni(
    department: Optional[str]       = Query(None),
    rehire_eligible: Optional[bool] = Query(None),
    engagement_level: Optional[str] = Query(None),
    search: Optional[str]           = Query(None),
    page: int                       = Query(1, ge=1),
    page_size: int                  = Query(10, ge=1, le=100),
    db: Session                     = Depends(get_db),
):
    return svc.list_alumni(
        db,
        department=department,
        rehire_eligible=rehire_eligible,
        engagement_level=engagement_level,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/alumni",
    response_model=schemas.AlumniRecordResponse,
    status_code=201,
    summary="Create Alumni Record",
)
def create_alumni_record(
    payload: schemas.AlumniRecordCreate,
    db: Session = Depends(get_db),
):
    return svc.create_alumni_record(db, payload)


@router.get(
    "/alumni/{alumni_id}",
    response_model=schemas.AlumniRecordResponse,
    summary="Get Alumni Record",
)
def get_alumni_record(alumni_id: int, db: Session = Depends(get_db)):
    return svc.get_alumni_record(db, alumni_id)


@router.patch(
    "/alumni/{alumni_id}",
    response_model=schemas.AlumniRecordResponse,
    summary="Update Alumni Record",
)
def update_alumni_record(
    alumni_id: int,
    payload: schemas.AlumniRecordUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_alumni_record(db, alumni_id, payload)


@router.get(
    "/trends",
    response_model=schemas.TrendAnalysisResponse,
    summary="Exit Trend Analysis",
)
def get_trends(
    months: int           = Query(3, ge=1, le=24, description="Period in months: 3, 6, or 12"),
    department: Optional[str] = Query(None, description="Department filter (pass 'All Departments' to skip)"),
    db: Session           = Depends(get_db),
):

    return svc.get_trend_analysis(db, months=months, department=department)



@router.get(
    "/clearance-templates",
    response_model=List[schemas.ClearanceTemplateResponse],
    summary="List Clearance Templates",
)
def list_clearance_templates(db: Session = Depends(get_db)):
    return svc.list_clearance_templates(db)


@router.post(
    "/clearance-templates",
    response_model=schemas.ClearanceTemplateResponse,
    status_code=201,
    summary="Create Clearance Template",
)
def create_clearance_template(
    payload: schemas.ClearanceTemplateCreate,
    db: Session = Depends(get_db),
):
    return svc.create_clearance_template(db, payload)


@router.patch(
    "/clearance-templates/{template_id}",
    response_model=schemas.ClearanceTemplateResponse,
    summary="Update Clearance Template",
)
def update_clearance_template(
    template_id: int,
    payload: schemas.ClearanceTemplateUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_clearance_template(db, template_id, payload)


@router.delete(
    "/clearance-templates/{template_id}",
    summary="Delete Clearance Template",
)
def delete_clearance_template(template_id: int, db: Session = Depends(get_db)):
    return svc.delete_clearance_template(db, template_id)
