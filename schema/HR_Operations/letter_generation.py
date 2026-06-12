from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, List




class LetterTemplateCreate(BaseModel):
    template_code: str
    name: str
    description: Optional[str] = None
    category: str                          # Employment | Financial | Exit | Legal | Career | Disciplinary
    body_template: str
    required_approvals: Optional[str] = None   # "Manager,HR,Finance"
    auto_approve: bool = False
    is_ai_optimised: bool = True


class LetterTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    body_template: Optional[str] = None
    required_approvals: Optional[str] = None
    auto_approve: Optional[bool] = None
    is_ai_optimised: Optional[bool] = None
    is_active: Optional[bool] = None


class LetterTemplateResponse(BaseModel):
    id: int
    template_code: str
    name: str
    description: Optional[str]
    category: str
    body_template: str
    required_approvals: Optional[str]
    auto_approve: bool
    is_ai_optimised: bool
    times_used: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




class LetterRequestCreate(BaseModel):
    template_id: int
    employee_id: int
    purpose: Optional[str] = None
    priority: str = "Medium"               


class LetterRequestUpdate(BaseModel):
    priority: Optional[str] = None
    status: Optional[str] = None          
    purpose: Optional[str] = None


class LetterRequestResponse(BaseModel):
    id: int
    request_code: str
    template_id: int
    employee_id: int
    purpose: Optional[str]
    priority: str
    status: str
    sla_hours: Optional[int]
    requested_at: datetime
    last_action_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




class LetterGenerationCreate(BaseModel):
    template_id: int
    employee_id: int
    letter_type: str
    letter_date: date
    subject: str
    body: str
    generated_by: Optional[int] = None
    request_id: Optional[int] = None
    digital_signature: bool = False


class LetterGenerationUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None           # DRAFT | ISSUED | REVOKED
    digital_signature: Optional[bool] = None
    is_signed: Optional[bool] = None


class LetterGenerationResponse(BaseModel):
    id: int
    letter_code: str
    request_id: Optional[int]
    template_id: int
    employee_id: int
    letter_type: str
    letter_date: date
    subject: str
    body: str
    generated_by: Optional[int]
    status: str
    verification_code: Optional[str]
    digital_signature: bool
    is_signed: bool
    download_count: int
    last_downloaded_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




class LetterWorkflowCreate(BaseModel):
    request_id: int
    step_number: int
    total_steps: int
    approver_role: str
    approver_id: Optional[int] = None


class LetterWorkflowUpdate(BaseModel):
    status: Optional[str] = None           # Pending | Approved | Rejected | Skipped
    remarks: Optional[str] = None
    approver_id: Optional[int] = None


class LetterWorkflowResponse(BaseModel):
    id: int
    request_id: int
    step_number: int
    total_steps: int
    approver_role: str
    approver_id: Optional[int]
    status: str
    remarks: Optional[str]
    actioned_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




class LetterSystemSettingsUpdate(BaseModel):
    default_digital_signature: Optional[str] = None
    audit_trail_retention_days: Optional[int] = None
    default_letter_format: Optional[str] = None        # PDF | DOCX
    default_workflow_sla_hours: Optional[int] = None
    high_priority_sla_hours: Optional[int] = None
    medium_priority_sla_hours: Optional[int] = None
    low_priority_sla_hours: Optional[int] = None
    email_on_new_request: Optional[bool] = None
    email_on_approval: Optional[bool] = None
    email_on_download: Optional[bool] = None


class LetterSystemSettingsResponse(BaseModel):
    id: int
    default_digital_signature: str
    audit_trail_retention_days: int
    default_letter_format: str
    default_workflow_sla_hours: int
    high_priority_sla_hours: int
    medium_priority_sla_hours: int
    low_priority_sla_hours: int
    email_on_new_request: bool
    email_on_approval: bool
    email_on_download: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




class DashboardStatsResponse(BaseModel):
    total_templates: int
    active_templates: int
    ai_optimised_templates: int
    total_requests: int
    approved_requests: int
    pending_requests: int
    rejected_requests: int
    auto_approved_count: int
    total_downloads: int


class LetterUsageReportItem(BaseModel):
    template_id: int
    template_code: str
    template_name: str
    category: str
    total_requests: int
    approved: int
    rejected: int
    pending: int
    total_downloads: int


class EmployeeLetterReportItem(BaseModel):
    employee_id: int
    total_requests: int
    approved: int
    pending: int
    rejected: int
    most_requested_type: Optional[str]
