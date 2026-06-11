

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator



class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_name: str
    file_url: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    is_internal: bool = False
    author_name: Optional[str] = None


class CommentOut(CommentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    request_id: int
    author_id: Optional[int] = None
    created_at: datetime


class StatusLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    from_status: Optional[str] = None
    to_status: str
    changed_by: Optional[str] = None
    note: Optional[str] = None
    changed_at: datetime



class PersonalInfoDetailBase(BaseModel):

    bank_name:            Optional[str] = None
    account_number:       Optional[str] = None
    account_holder_name:  Optional[str] = None
    ifsc_code:            Optional[str] = None
    account_type:         Optional[str] = None
    branch_name:          Optional[str] = None
  
    address_type:         Optional[str] = None
    new_address_line1:    Optional[str] = None
    new_address_line2:    Optional[str] = None
    new_city:             Optional[str] = None
    new_state:            Optional[str] = None
    new_country:          Optional[str] = None
    new_pincode:          Optional[str] = None

    contact_name:         Optional[str] = None
    contact_relationship: Optional[str] = None
    contact_phone:        Optional[str] = None
    contact_email:        Optional[str] = None
  
    phone_type:           Optional[str] = None
    new_phone_number:     Optional[str] = None
  
    family_member_name:   Optional[str] = None
    relationship_type:    Optional[str] = None
    date_of_birth:        Optional[str] = None
    family_details_note:  Optional[str] = None
  
    nominee_name:         Optional[str] = None
    nominee_dob:          Optional[str] = None
    nominee_relationship: Optional[str] = None
    nominee_percentage:   Optional[Decimal] = None
    
    supporting_document_url: Optional[str] = None
    remarks:              Optional[str] = None


class PersonalInfoDetailCreate(PersonalInfoDetailBase):
    pass


class PersonalInfoDetailOut(PersonalInfoDetailBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class WorkRelatedDetailBase(BaseModel):
    start_date:               Optional[str] = None
    end_date:                 Optional[str] = None
    wfh_reason:               Optional[str] = None
    is_recurring:             Optional[bool] = False
    recurrence_pattern:       Optional[str] = None
    work_location_address:    Optional[str] = None
    current_shift:            Optional[str] = None
    requested_shift:          Optional[str] = None
    shift_change_reason:      Optional[str] = None
    shift_effective_date:     Optional[str] = None
    current_department:       Optional[str] = None
    requested_department:     Optional[str] = None
    transfer_reason:          Optional[str] = None
    transfer_effective_date:  Optional[str] = None
    current_manager:          Optional[str] = None
    current_reporting_manager:   Optional[str] = None
    requested_reporting_manager: Optional[str] = None
    manager_change_reason:    Optional[str] = None
    manager_change_effective_date: Optional[str] = None
    current_desk:             Optional[str] = None
    preferred_desk:           Optional[str] = None
    desk_change_reason:       Optional[str] = None
    remarks:                  Optional[str] = None


class WorkRelatedDetailCreate(WorkRelatedDetailBase):
    pass


class WorkRelatedDetailOut(WorkRelatedDetailBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AdminDetailBase(BaseModel):
    id_card_reason:       Optional[str] = None
    old_id_card_number:   Optional[str] = None
    access_areas:         Optional[str] = None
    access_level:         Optional[str] = None
    access_start_date:    Optional[str] = None
    access_end_date:      Optional[str] = None
    vehicle_type:         Optional[str] = None
    vehicle_number:       Optional[str] = None
    parking_location:     Optional[str] = None
    preferred_slot:       Optional[str] = None
    locker_floor:         Optional[str] = None
    preferred_locker:     Optional[str] = None
    locker_reason:        Optional[str] = None
    stationery_items:     Optional[str] = None
    cost_center:          Optional[str] = None
    card_name:            Optional[str] = None
    card_designation:     Optional[str] = None
    card_email:           Optional[str] = None
    card_phone:           Optional[str] = None
    card_quantity:        Optional[int] = None
    remarks:              Optional[str] = None


class AdminDetailCreate(AdminDetailBase):
    pass


class AdminDetailOut(AdminDetailBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class FinancialDetailBase(BaseModel):
    advance_amount:         Optional[Decimal] = None
    advance_reason:         Optional[str]     = None
    repayment_months:       Optional[int]     = None
    advance_month:          Optional[str]     = None
    expense_type:           Optional[str]     = None
    expense_date:           Optional[str]     = None
    expense_amount:         Optional[Decimal] = None
    expense_description:    Optional[str]     = None
    bill_reference:         Optional[str]     = None
    loan_type:              Optional[str]     = None
    loan_amount:            Optional[Decimal] = None
    loan_tenure_months:     Optional[int]     = None
    loan_purpose:           Optional[str]     = None
    financial_year:         Optional[str]     = None
    investment_type:        Optional[str]     = None
    declared_amount:        Optional[Decimal] = None
    investment_proof_note:  Optional[str]     = None
    current_regime:         Optional[str]     = None
    requested_regime:       Optional[str]     = None
    regime_change_reason:   Optional[str]     = None
    certificate_purpose:    Optional[str]     = None
    address_to:             Optional[str]     = None
    currency:               Optional[str]     = "INR"
    supporting_doc_url:     Optional[str]     = None
    remarks:                Optional[str]     = None


class FinancialDetailCreate(FinancialDetailBase):
    pass


class FinancialDetailOut(FinancialDetailBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TravelExpenseDetailBase(BaseModel):
    travel_from:            Optional[str]     = None
    travel_to:              Optional[str]     = None
    travel_start_date:      Optional[str]     = None
    travel_end_date:        Optional[str]     = None
    travel_purpose:         Optional[str]     = None
    trip_type:              Optional[str]     = None
    transport_mode:         Optional[str]     = None
    accommodation_required: Optional[bool]    = False
    estimated_cost:         Optional[Decimal] = None
    project_code:           Optional[str]     = None
    expense_category:       Optional[str]     = None
    total_expense_amount:   Optional[Decimal] = None
    expense_date:           Optional[str]     = None
    receipt_reference:      Optional[str]     = None
    advance_amount:         Optional[Decimal] = None
    advance_required_by:    Optional[str]     = None
    vehicle_type:           Optional[str]     = None
    start_odometer:         Optional[Decimal] = None
    end_odometer:           Optional[Decimal] = None
    total_km:               Optional[Decimal] = None
    rate_per_km:            Optional[Decimal] = None
    mileage_amount:         Optional[Decimal] = None
    per_diem_days:          Optional[int]     = None
    per_diem_rate:          Optional[Decimal] = None
    per_diem_amount:        Optional[Decimal] = None
    per_diem_city_tier:     Optional[str]     = None
    currency:               Optional[str]     = "INR"
    manager_approval_needed: Optional[bool]  = True
    supporting_doc_url:     Optional[str]     = None
    remarks:                Optional[str]     = None


class TravelExpenseDetailCreate(TravelExpenseDetailBase):
    pass


class TravelExpenseDetailOut(TravelExpenseDetailBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ITSystemsDetailBase(BaseModel):
    software_name:            Optional[str]  = None
    access_type:              Optional[str]  = None
    access_reason:            Optional[str]  = None
    access_duration:          Optional[str]  = None
    access_end_date:          Optional[str]  = None
    manager_approved:         Optional[bool] = False
    vpn_location:             Optional[str]  = None
    vpn_reason:               Optional[str]  = None
    device_type:              Optional[str]  = None
    distribution_list_name:   Optional[str]  = None
    distribution_action:      Optional[str]  = None
    email_to_add:             Optional[str]  = None
    hardware_type:            Optional[str]  = None
    hardware_model:           Optional[str]  = None
    hardware_quantity:        Optional[int]  = 1
    hardware_reason:          Optional[str]  = None
    urgency_level:            Optional[str]  = None
    cost_center:              Optional[str]  = None
    remarks:                  Optional[str]  = None


class ITSystemsDetailCreate(ITSystemsDetailBase):
    pass


class ITSystemsDetailOut(ITSystemsDetailBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class FeedbackDetailBase(BaseModel):
    is_anonymous:           Optional[bool] = False
    is_confidential:        Optional[bool] = False
    feedback_category:      Optional[str]  = None
    feedback_rating:        Optional[int]  = Field(None, ge=1, le=5)
    grievance_against:      Optional[str]  = None
    incident_date:          Optional[str]  = None
    incident_location:      Optional[str]  = None
    previous_escalations:   Optional[bool] = False
    accused_name:           Optional[str]  = None
    accused_designation:    Optional[str]  = None
    incident_description:   Optional[str]  = None
    witness_names:          Optional[str]  = None
    posh_report_date:       Optional[str]  = None
    violation_type:         Optional[str]  = None
    persons_involved:       Optional[str]  = None
    evidence_description:   Optional[str]  = None
  
    case_number:            Optional[str]  = None
    assigned_investigator:  Optional[str]  = None
    resolution_summary:     Optional[str]  = None
    remarks:                Optional[str]  = None


class FeedbackDetailCreate(FeedbackDetailBase):
    pass


class FeedbackDetailOut(FeedbackDetailBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class RequestManagementBase(BaseModel):
    category:       str = Field(..., description="RequestCategory value")
    request_type:   str = Field(..., description="RequestType value")
    subject:        str = Field(..., min_length=3, max_length=500)
    description:    Optional[str] = None
    employee_id:    Optional[int] = None
    employee_name:  Optional[str] = None
    employee_email: Optional[str] = None
    department:     Optional[str] = None
    location:       Optional[str] = None
    workflow:       Optional[str] = None
    priority:       Optional[str] = None  


class RequestManagementCreate(RequestManagementBase):

    personal_info_detail:  Optional[PersonalInfoDetailCreate]  = None
    work_related_detail:   Optional[WorkRelatedDetailCreate]   = None
    admin_detail:          Optional[AdminDetailCreate]         = None
    financial_detail:      Optional[FinancialDetailCreate]     = None
    travel_expense_detail: Optional[TravelExpenseDetailCreate] = None
    it_systems_detail:     Optional[ITSystemsDetailCreate]     = None
    feedback_detail:       Optional[FeedbackDetailCreate]      = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        from model.Forms_Workflows.request import RequestCategory
        valid = [e.value for e in RequestCategory]
        if v not in valid:
            raise ValueError(f"category must be one of {valid}")
        return v

    @field_validator("request_type")
    @classmethod
    def validate_request_type(cls, v: str) -> str:
        from model.Forms_Workflows.request import RequestType
        valid = [e.value for e in RequestType]
        if v not in valid:
            raise ValueError(f"request_type must be one of {valid}")
        return v


class RequestManagementUpdate(BaseModel):
  
    subject:         Optional[str] = None
    description:     Optional[str] = None
    status:          Optional[str] = None
    priority:        Optional[str] = None
    assigned_to:     Optional[str] = None
    workflow:        Optional[str] = None
    resolution_note: Optional[str] = None


    personal_info_detail:  Optional[PersonalInfoDetailBase]  = None
    work_related_detail:   Optional[WorkRelatedDetailBase]   = None
    admin_detail:          Optional[AdminDetailBase]         = None
    financial_detail:      Optional[FinancialDetailBase]     = None
    travel_expense_detail: Optional[TravelExpenseDetailBase] = None
    it_systems_detail:     Optional[ITSystemsDetailBase]     = None
    feedback_detail:       Optional[FeedbackDetailBase]      = None


class RequestManagementOut(RequestManagementBase):
 
    model_config = ConfigDict(from_attributes=True)

    id:          int
    request_id:  str
    status:      str
    priority:    str
    sla_days:    Optional[str]   = None
    assigned_to: Optional[str]   = None
    assigned_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    resolved_at:     Optional[datetime] = None
    resolved_by:     Optional[str]   = None
    auto_description_generated: bool = False
    submitted_at:    datetime
    created_at:      datetime
    updated_at:      datetime

    personal_info_detail:  Optional[PersonalInfoDetailOut]  = None
    work_related_detail:   Optional[WorkRelatedDetailOut]   = None
    admin_detail:          Optional[AdminDetailOut]         = None
    financial_detail:      Optional[FinancialDetailOut]     = None
    travel_expense_detail: Optional[TravelExpenseDetailOut] = None
    it_systems_detail:     Optional[ITSystemsDetailOut]     = None
    feedback_detail:       Optional[FeedbackDetailOut]      = None

    comments:    List[CommentOut]    = []
    attachments: List[AttachmentOut] = []
    status_logs: List[StatusLogOut]  = []


class RequestManagementListOut(BaseModel):
 
    model_config = ConfigDict(from_attributes=True)

    id:           int
    request_id:   str
    category:     str
    request_type: str
    subject:      str
    employee_id:  Optional[int]  = None
    employee_name:Optional[str]  = None
    department:   Optional[str]  = None
    location:     Optional[str]  = None
    workflow:     Optional[str]  = None
    status:       str
    priority:     str
    sla_days:     Optional[str]  = None
    assigned_to:  Optional[str]  = None
    submitted_at: datetime
    updated_at:   datetime


class StatusTransitionPayload(BaseModel):
    new_status:   str
    changed_by:   Optional[str] = None
    note:         Optional[str] = None


class AssignPayload(BaseModel):
    assigned_to: str
    assigned_by: Optional[str] = None


class ResolvePayload(BaseModel):
    resolution_note: str
    resolved_by:     Optional[str] = None


class RequestStatusCount(BaseModel):
    status: str
    count:  int


class RequestCategoryCount(BaseModel):
    category: str
    count:    int


class RequestDashboardStats(BaseModel):
    total:       int
    in_progress: int
    approved:    int
    completed:   int
    pending:     int
    rejected:    int
    by_category: List[RequestCategoryCount] = []
    by_status:   List[RequestStatusCount]   = []


class RequestTypeConfigBase(BaseModel):
    category:          str
    request_type:      str
    display_name:      str
    description:       Optional[str] = None
    default_priority:  str = "Medium"
    sla_days:          Optional[str] = None
    workflow_id:       Optional[int] = None
    auto_description_template: Optional[str] = None
    is_active:         bool = True
    requires_attachment:         bool = False
    requires_manager_approval:   bool = False


class RequestTypeConfigCreate(RequestTypeConfigBase):
    pass


class RequestTypeConfigUpdate(BaseModel):
    display_name:      Optional[str]  = None
    description:       Optional[str]  = None
    default_priority:  Optional[str]  = None
    sla_days:          Optional[str]  = None
    workflow_id:       Optional[int]  = None
    auto_description_template: Optional[str] = None
    is_active:         Optional[bool] = None
    requires_attachment:       Optional[bool] = None
    requires_manager_approval: Optional[bool] = None


class RequestTypeConfigOut(RequestTypeConfigBase):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    created_at: datetime
    updated_at: datetime
