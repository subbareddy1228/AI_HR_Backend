from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime


# ── CustomForm schemas ─────────────────────────────────────────────────────────

class CustomFormBase(BaseModel):
    form_name: str
    form_category: str
    description: Optional[str] = None
    fields_schema: Optional[Any] = None
    is_active: bool = True
    created_by: Optional[str] = None


class CustomFormCreate(CustomFormBase):
    pass


class CustomFormUpdate(BaseModel):
    form_name: Optional[str] = None
    form_category: Optional[str] = None
    description: Optional[str] = None
    fields_schema: Optional[Any] = None
    is_active: Optional[bool] = None


class CustomFormResponse(CustomFormBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── FormSubmission schemas ─────────────────────────────────────────────────────

class FormSubmissionBase(BaseModel):
    form_id: int
    employee_id: Optional[int] = None
    submitted_by: Optional[str] = None
    form_data: Optional[Any] = None
    status: str = "Submitted"


class FormSubmissionCreate(FormSubmissionBase):
    pass


class FormSubmissionResponse(FormSubmissionBase):
    id: int
    submitted_at: datetime
    model_config = ConfigDict(from_attributes=True)
