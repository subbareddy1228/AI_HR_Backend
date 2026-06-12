from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict




class ApprovalStepSchema(BaseModel):
    role: str          
    label: str         
    status: str        




class ProbationKPISchema(BaseModel):
    total_probation: int
    at_risk: int
    ending_soon: int        
    extended: int
    avg_progress: float     
    reviews_due: int        


class MilestoneSchema(BaseModel):
    day: int                
    status: str             
    rating: Optional[str]   


class ProbationRowSchema(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    name: str
    designation: Optional[str]
    department: Optional[str]
    location: Optional[str]
    email: Optional[str]

    probation_status: str       
    milestones: List[MilestoneSchema]
    progress_percent: int
    days_remaining: int
    end_date: date
    risk_level: str            

    model_config = ConfigDict(from_attributes=True)


class ProbationDetailSchema(ProbationRowSchema):
    probation_start_date: date
    probation_end_date: date
    extended_till: Optional[date]
    performance_rating: Optional[str]
    remarks: Optional[str]
    reviewed_by: Optional[int]
    created_at: datetime
    updated_at: datetime



class ProbationCreateSchema(BaseModel):
    employee_id: int
    probation_start_date: date
    probation_end_date: date
    reviewed_by: Optional[int] = None
    remarks: Optional[str] = None


class ProbationUpdateSchema(BaseModel):
    status: Optional[str] = None
    performance_rating: Optional[str] = None
    extended_till: Optional[date] = None
    confirmation_date: Optional[date] = None
    remarks: Optional[str] = None


class ProbationMilestoneUpdateSchema(BaseModel):
    confirmation_id: int
    milestone_day: int         
    rating: str
    remarks: Optional[str] = None


class ProbationBulkActionSchema(BaseModel):
    confirmation_ids: List[int]
    action: str                 




class ConfirmationKPISchema(BaseModel):
    for_confirmation: int
    confirmed: int
    confirmed_rate_pct: float
    pending: int
    overdue: int
    auto_triggered: int
    letters_sent: int


class WorkflowStepSchema(BaseModel):
    step: int
    role: str               
    initial: str           
    status: str             
    actor_name: Optional[str] = None


class ConfirmationRowSchema(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    name: str
    designation: Optional[str]
    department: Optional[str]
    location: Optional[str]
    joined: Optional[date]

    confirmation_status: str        
    workflow_progress: int         
    workflow_total: int            
    workflow_steps: List[WorkflowStepSchema]

    days_remaining: Optional[int]
    due_date: Optional[date]
    time_label: str                 
    is_overdue: bool

    rating: Optional[str]           
    rating_stars: Optional[int]     

    model_config = ConfigDict(from_attributes=True)


class ConfirmationActionSchema(BaseModel):
    
    role: str
    action: str            
    remarks: Optional[str] = None


class ConfirmationBulkSchema(BaseModel):
    confirmation_ids: List[int]
    action: str            




class PromotionKPISchema(BaseModel):
    nominations: int
    approved: int
    approved_success_pct: float
    under_review: int
    avg_salary_increase_pct: float
    letters_generated: int
    rejected: int


class PromotionApprovalWorkflowSchema(BaseModel):
    steps: List[ApprovalStepSchema]
    completed_steps: int
    total_steps: int


class PromotionRowSchema(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    name: str
    designation: Optional[str]
    department: Optional[str]
    location: Optional[str]
    tenure_years: Optional[float]

    
    from_grade: Optional[str]
    to_grade: Optional[str]
    from_designation: str
    to_designation: str
    from_role: Optional[str]
    to_role: Optional[str]

    
    approval_workflow: PromotionApprovalWorkflowSchema
    status: str                 

    
    current_salary: Optional[Decimal]
    revised_salary: Optional[Decimal]
    salary_increase_pct: Optional[float]
    salary_range_label: Optional[str]  

   
    is_eligible: bool

    model_config = ConfigDict(from_attributes=True)


class PromotionCreateSchema(BaseModel):
    employee_id: int
    from_designation: str
    to_designation: str
    from_grade: Optional[str] = None
    to_grade: Optional[str] = None
    from_role: Optional[str] = None
    to_role: Optional[str] = None
    effective_date: date
    current_salary: Optional[Decimal] = None
    revised_salary: Optional[Decimal] = None
    reason: Optional[str] = None


class PromotionUpdateSchema(BaseModel):
    status: Optional[str] = None       
    approved_by: Optional[int] = None
    revised_salary: Optional[Decimal] = None
    remarks: Optional[str] = None


class PromotionApprovalSchema(BaseModel):
    role: str                           
    action: str                        
    remarks: Optional[str] = None


class PromotionBulkActionSchema(BaseModel):
    promotion_ids: List[int]
    action: str             




class BuddyKPISchema(BaseModel):
    active_buddies: int
    avg_rating: float
    assignments: int
    feedback: int
    avg_experience_years: float
    capacity_used_pct: float


class AssignedJoinerSchema(BaseModel):
    employee_id: int
    employee_code: str
    name: str


class BuddyRowSchema(BaseModel):
    id: int
    employee_id: int
    employee_code: str    
    name: str
    designation: Optional[str]
    department: Optional[str]
    email: Optional[str]

    status: str             

    assigned_joiners: List[AssignedJoinerSchema]
    assignments_count: int

    experience_years: float
    joined_date: Optional[date]

    rating: float          
    rating_out_of: float    
    rating_label: str       

    capacity_pct: int       
    max_capacity: int       

    model_config = ConfigDict(from_attributes=True)


class BuddyAssignmentSchema(BaseModel):
    
    buddy_employee_id: int
    joiner_employee_id: int
    notes: Optional[str] = None


class BuddyFeedbackSchema(BaseModel):
    buddy_employee_id: int
    joiner_employee_id: int
    rating: float               
    comments: Optional[str] = None


class BuddyBulkActionSchema(BaseModel):
    buddy_ids: List[int]
    action: str     




class CareerPageSummarySchema(BaseModel):
   
    probation_pending: int
    confirmation_pending: int
    promotions_pending: int
    buddy_active: int