from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db


from schema.HR_Operations.employee_confirmation import (
    ApprovalActionSchema,
    BulkConfirmationActionSchema,
    ConfirmationDetailSchema,
    ConfirmationKPISchema,
    ConfirmationListItemSchema,
    EmployeeConfirmationCreate,
    EmployeeConfirmationUpdate,
    BulkActionResultSchema,
    AutoTriggerResultSchema,
)


import services.HR_Operations.employee_confirmation_service as svc

router = APIRouter(prefix="/confirmations", tags=["Employee Confirmations"])




@router.get("/kpi", response_model=ConfirmationKPISchema)
def get_kpi(db: Session = Depends(get_db)):
    
    return svc.get_confirmation_kpi(db)



@router.get("/departments", response_model=List[str])
def get_departments(db: Session = Depends(get_db)):
    
    return svc.get_departments(db)



@router.get("/export")
def export_data(
    status:     Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    
    import csv, io

    rows    = svc.export_confirmations(db, status=status, department=department)
    output  = io.StringIO()
    writer  = csv.DictWriter(output, fieldnames=rows[0].keys() if rows else [])
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employee_confirmations.csv"},
    )



@router.post("/send-reminders")
def send_reminders(db: Session = Depends(get_db)):
   
    return svc.send_reminders(db)


@router.post("/auto-trigger", response_model=AutoTriggerResultSchema)
def auto_trigger_reviews(db: Session = Depends(get_db)):
    
    return svc.auto_trigger_reviews(db)




@router.post("/bulk-action", response_model=BulkActionResultSchema)
def bulk_action(
    payload: BulkConfirmationActionSchema,
    db: Session = Depends(get_db),
):
    return svc.bulk_action(db, payload)




@router.get("", response_model=List[ConfirmationListItemSchema])
def list_confirmations(
    search:      Optional[str] = Query(None, description="Name / code / email search"),
    status:      Optional[str] = Query(None, description="All Status | Confirmed | Overdue | …"),
    department:  Optional[str] = Query(None, description="All Departments | Engineering | …"),
    eligibility: Optional[str] = Query(None, description="All Eligibility | Eligible | Conditional | …"),
    sort_by:     str            = Query("due_date", description="due_date | name | days_remaining | status"),
    skip:        int            = Query(0, ge=0),
    limit:       int            = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return svc.list_confirmations(
        db,
        search=search,
        status=status,
        department=department,
        eligibility=eligibility,
        sort_by=sort_by,
        skip=skip,
        limit=limit,
    )


@router.get("/{confirmation_id}", response_model=ConfirmationDetailSchema)
def get_confirmation(confirmation_id: int, db: Session = Depends(get_db)):
    
    return svc.get_confirmation(db, confirmation_id)


@router.post("", response_model=ConfirmationDetailSchema, status_code=201)
def create_confirmation(
    payload: EmployeeConfirmationCreate,
    db: Session = Depends(get_db),
):
   
    return svc.create_confirmation(db, payload)


@router.patch("/{confirmation_id}", response_model=ConfirmationDetailSchema)
def update_confirmation(
    confirmation_id: int,
    payload: EmployeeConfirmationUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_confirmation(db, confirmation_id, payload)


@router.post("/{confirmation_id}/approve", response_model=ConfirmationDetailSchema)
def approve_confirmation(
    confirmation_id: int,
    payload: ApprovalActionSchema,
    db: Session = Depends(get_db),
):
    return svc.process_approval(db, confirmation_id, payload)