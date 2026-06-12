from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict




class SalaryBreakdownSchema(BaseModel):
    basic:               Optional[Decimal] = None
    hra:                 Optional[Decimal] = None
    conveyance:          Optional[Decimal] = None
    special_allowance:   Optional[Decimal] = None
    performance_bonus:   Optional[Decimal] = None
    stipend:             Optional[Decimal] = None    
    other:               Optional[Decimal] = None
    gross_total:         Optional[Decimal] = None    




class TimelineEventSchema(BaseModel):
    event:     str        
    actor:     str        
    actor_role: Optional[str] = None
    timestamp: datetime




class OfferKPISchema(BaseModel):
    total_offers:      int
    draft:             int
    pending_approval:  int
    approved:          int
    sent:              int
    accepted:          int
    declined:          int
    expired:           int
    withdrawn:         int




class OfferTabCountsSchema(BaseModel):
    all_offers:       int
    draft:            int
    pending_approval: int
    approved:         int
    sent:             int
    accepted:         int
    declined:         int
    expired:          int
    withdrawn:        int




class OfferListItemSchema(BaseModel):
    
    id:                int
    candidate_id:      Optional[int]
    candidate_name:    str
    candidate_email:   str
    candidate_phone:   Optional[str]
    candidate_source:  Optional[str]  

   
    position:          str
    department:        Optional[str]
    employment_type:   Optional[str]  
    join_date:         Optional[date]
    grade:             Optional[str]  
    experience_required: Optional[str]  

    
    gross_salary:      Optional[Decimal]   
    salary_breakdown:  Optional[SalaryBreakdownSchema]

   
    status:            str    
                              
    timeline:          List[TimelineEventSchema] = []
    expiry_date:       Optional[date]
    sent_date:         Optional[datetime]
    response_date:     Optional[datetime]

    
    offer_content:     Optional[str]
    notes:             Optional[str]
    created_by:        Optional[int]
    created_at:        datetime
    updated_at:        datetime

    model_config = ConfigDict(from_attributes=True)




class OfferCreateSchema(BaseModel):
    candidate_id:      Optional[int] = None
    candidate_name:    str
    candidate_email:   str
    candidate_phone:   Optional[str] = None
    candidate_source:  Optional[str] = None

    position:          str
    department:        Optional[str] = None
    employment_type:   Optional[str] = "Full-time"
    join_date:         Optional[date] = None
    grade:             Optional[str] = None
    experience_required: Optional[str] = None

   
    gross_salary:      Optional[Decimal] = None
    basic:             Optional[Decimal] = None
    hra:               Optional[Decimal] = None
    conveyance:        Optional[Decimal] = None
    special_allowance: Optional[Decimal] = None
    performance_bonus: Optional[Decimal] = None
    stipend:           Optional[Decimal] = None

    offer_content:     str
    expiry_date:       Optional[date] = None
    notes:             Optional[str] = None
    template_id:       Optional[int] = None




class OfferUpdateSchema(BaseModel):
    candidate_name:    Optional[str] = None
    candidate_email:   Optional[str] = None
    candidate_phone:   Optional[str] = None
    candidate_source:  Optional[str] = None

    position:          Optional[str] = None
    department:        Optional[str] = None
    employment_type:   Optional[str] = None
    join_date:         Optional[date] = None
    grade:             Optional[str] = None
    experience_required: Optional[str] = None

    gross_salary:      Optional[Decimal] = None
    basic:             Optional[Decimal] = None
    hra:               Optional[Decimal] = None
    conveyance:        Optional[Decimal] = None
    special_allowance: Optional[Decimal] = None
    performance_bonus: Optional[Decimal] = None
    stipend:           Optional[Decimal] = None

    offer_content:     Optional[str] = None
    expiry_date:       Optional[date] = None
    notes:             Optional[str] = None
    status:            Optional[str] = None




class OfferStatusActionSchema(BaseModel):
    action:   str              
    remarks:  Optional[str] = None
    actor:    Optional[str] = None       
    actor_role: Optional[str] = None



class SendOfferEmailSchema(BaseModel):
    offer_id:          int
    recipient_email:   Optional[str] = None   
    subject:           Optional[str] = None
    extra_message:     Optional[str] = None
    expiry_days:       int = 30




class OfferBulkActionSchema(BaseModel):
    offer_ids: List[int]
    action:    str          
    remarks:   Optional[str] = None




class OfferAnalyticsSchema(BaseModel):
    acceptance_rate_pct:       float    
    acceptance_summary:        str      
    avg_time_to_accept_days:   float   
    avg_time_label:            str      
    top_department:            str      
    top_department_label:      str      
    monthly_trend_pct:         float    
    monthly_trend_label:       str      

    
    type_distribution: List[dict]       
   
    department_stats:  List[dict]       
    
    status_distribution: List[dict]     




class OfferFilterParams(BaseModel):
    search:          Optional[str] = None
    status:          Optional[str] = None
    department:      Optional[str] = None
    offer_type:      Optional[str] = None    
    skip:            int = 0
    limit:           int = 20