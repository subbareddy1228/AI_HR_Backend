from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, List
from datetime import datetime


class FormFieldDefinition(BaseModel):
    field_id: str
    label: str
    field_type: str
    placeholder: Optional[str] = None
    is_required: bool = False
    options: Optional[List[str]] = None
    default_value: Optional[Any] = None
    order: int = 0


class CustomFormCreate(BaseModel):
    form_name: str
    form_category: str
    description: Optional[str] = None
    fields_schema: Optional[List[FormFieldDefinition]] = None
    is_active: bool = True
    is_published: bool = False
    created_by: Optional[str] = None


class CustomFormUpdate(BaseModel):
    form_name: Optional[str] = None
    form_category: Optional[str] = None
    description: Optional[str] = None
    fields_schema: Optional[List[FormFieldDefinition]] = None
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None


class CustomFormResponse(BaseModel):
    id: int
    form_name: str
    form_category: str
    description: Optional[str] = None
    fields_schema: Optional[Any] = None
    is_active: bool
    is_published: bool
    version: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomFormSummary(BaseModel):
    id: int
    form_name: str
    form_category: str
    is_active: bool
    is_published: bool
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FormSubmissionCreate(BaseModel):
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    submitted_by: Optional[str] = None
    form_data: Optional[Any] = None
    status: str = "Submitted"


class FormSubmissionUpdate(BaseModel):
    form_data: Optional[Any] = None
    status: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None


class FormSubmissionResponse(BaseModel):
    id: int
    form_id: int
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    submitted_by: Optional[str] = None
    form_data: Optional[Any] = None
    status: str
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FormDashboardStats(BaseModel):
    total_forms: int
    active_forms: int
    published_forms: int
    total_submissions: int