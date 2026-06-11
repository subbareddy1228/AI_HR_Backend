from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List

from core.database import get_db

from schema.onboarding.probation_management import (
    ProbationKPISchema,
    ProbationEmployeeSchema,
    ProbationAddEmployeeSchema,
    ProbationStatusUpdateSchema,
    ProbationBulkActionSchema,
    ProbationMilestoneSchema,
    ProbationReportSchema,
)

from services.probation_management import (
    get_probation_kpi,
    list_probation_employees,
    get_probation_employee,
    add_employee_probation,
    update_probation_status,
    bulk_action_probation,
    complete_milestone,
    get_probation_report,
    get_probation_departments,
)

router = APIRouter(
    prefix="/probation-management",
    tags=["Probation Management"],
)




@router.get("/kpi", response_model=ProbationKPISchema)
def kpi(db: Session = Depends(get_db)):
    
    return get_probation_kpi(db)




@router.get("/employees")
def list_employees(
    db:         Session        = Depends(get_db),
    search:     Optional[str] = Query(None,  description="Search by name, email or employee ID"),
    status:     Optional[str] = Query(None,  description="In Progress|Under Review|Extended|At Risk|Completed|Terminated"),
    department: Optional[str] = Query(None,  description="Engineering|HR|Sales|Marketing"),
    risk_level: Optional[str] = Query(None,  description="Low|Medium|High"),
    sort_by:    Optional[str] = Query("name",description="name|days_remaining|progress|joining_date"),
    skip:       int            = Query(0),
    limit:      int            = Query(50),
):
    
    return list_probation_employees(db, search, status, department, risk_level, sort_by, skip, limit)




@router.get("/employees/{confirmation_id}")
def get_employee(confirmation_id: int, db: Session = Depends(get_db)):
    
    return get_probation_employee(db, confirmation_id)



@router.post("/employees", status_code=status.HTTP_201_CREATED)
def add_employee(payload: ProbationAddEmployeeSchema, db: Session = Depends(get_db)):
    
    return add_employee_probation(db, payload)




@router.patch("/employees/{confirmation_id}/status")
def update_status(
    confirmation_id: int,
    payload:         ProbationStatusUpdateSchema,
    db:              Session = Depends(get_db),
):
    
    return update_probation_status(db, confirmation_id, payload)



@router.post("/bulk-action")
def bulk_action(payload: ProbationBulkActionSchema, db: Session = Depends(get_db)):
   
    return bulk_action_probation(db, payload)




@router.post("/employees/{confirmation_id}/milestone")
def record_milestone(
    confirmation_id: int,
    payload:         ProbationMilestoneSchema,
    db:              Session = Depends(get_db),
):
    
    payload.confirmation_id = confirmation_id
    return complete_milestone(db, payload)



@router.get("/departments")
def departments(db: Session = Depends(get_db)):
   
    return get_probation_departments(db)



@router.get("/reports")
def reports(db: Session = Depends(get_db)):
    
    return get_probation_report(db)