from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict




class ApprovalNodeSchema(BaseModel):
    role: str                 
    status: str               
    actor_name: Optional[str] = None
    acted_at: Optional[datetime] = None
    remarks: Optional[str] = None



class ConfirmationKPISchema(BaseModel):
    total: int
    pending_review: int
    pending_approval: int
    confirmed: int
    overdue: int
    due_this_week: int




class ConfirmationListItemSchema(BaseModel):
    
    
    id: int
    employee_id: int
    employee_code: str         
    name: str
    designation: Optional[str]
    department: Optional[str]
    location: Optional[str]

    
    confirmation_status: str    
    confirmation_date: Optional[date]
    extension_count: int = 0   

    
    eligibility: str           
    employment_type: str        

    
    approval_workflow: List[ApprovalNodeSchema]
    manager_recommendation: Optional[str]  

   
    days_remaining: Optional[int]   
    due_date: Optional[date]
    time_label: str                 
    is_overdue: bool

    model_config = ConfigDict(from_attributes=True)




class ConfirmationDetailSchema(ConfirmationListItemSchema):
    probation_start_date: date
    probation_end_date: date
    extended_till: Optional[date]
    performance_rating: Optional[str]
    remarks: Optional[str]
    reviewed_by: Optional[int]
    created_at: datetime
    updated_at: datetime




class EmployeeConfirmationCreate(BaseModel):
    employee_id: int
    probation_start_date: date
    probation_end_date: date
    reviewed_by: Optional[int] = None
    remarks: Optional[str] = None


class EmployeeConfirmationUpdate(BaseModel):
    confirmation_date: Optional[date] = None
    performance_rating: Optional[str] = None   
    status: Optional[str] = None               
    extended_till: Optional[date] = None
    reviewed_by: Optional[int] = None
    remarks: Optional[str] = None


class EmployeeConfirmationResponse(BaseModel):
    id: int
    employee_id: int
    probation_start_date: date
    probation_end_date: date
    confirmation_date: Optional[date]
    performance_rating: Optional[str]
    status: str
    extended_till: Optional[date]
    reviewed_by: Optional[int]
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



class ApprovalActionSchema(BaseModel):
    
    role: str
    action: str              
    remarks: Optional[str] = None




class BulkConfirmationActionSchema(BaseModel):
    
    confirmation_ids: List[int]
    action: str
    remarks: Optional[str] = None




class ConfirmationFilterParams(BaseModel):
    search: Optional[str] = None
    status: Optional[str] = None           
    department: Optional[str] = None       
    eligibility: Optional[str] = None      
    sort_by: Optional[str] = "due_date"    
    skip: int = 0
    limit: int = 50




class BulkActionResultSchema(BaseModel):
    action: str
    total: int
    success: int
    failed: List[dict]


class AutoTriggerResultSchema(BaseModel):
    triggered: int
    skipped: int
    details: List[dict]
