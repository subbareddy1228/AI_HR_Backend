from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# CustomForm – Base
# ─────────────────────────────────────────────────────────────────────────────

class CustomFormBase(BaseModel):
    """
    Shared fields used by Create and Response.

    Form Configuration tab (Image 2):
      form_name     →  "Form Title" text input
      form_category →  "Form Category" dropdown  (General …)
      description   →  "Form Description" textarea
      fields_schema →  Full canvas JSON  (pages → fields → config +
                        Advanced Settings block)
      is_active     →  Publish / unpublish state
      created_by    →  Builder's email / id
    """
    form_name:     str
    form_category: Optional[str] = None
    description:   Optional[str] = None
    fields_schema: Optional[Any] = None
    is_active:     bool          = True
    created_by:    Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# CustomForm – Create  →  POST /custom-forms/
# ─────────────────────────────────────────────────────────────────────────────

class CustomFormCreate(CustomFormBase):
    """Payload to save a new form definition from the Form Builder canvas."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# CustomForm – Update  →  PUT /custom-forms/{form_id}
# ─────────────────────────────────────────────────────────────────────────────

class CustomFormUpdate(BaseModel):
    """
    All fields optional — send only what changed.
    Triggered on every Save / Publish / canvas edit from the builder.
    """
    form_name:     Optional[str]  = None
    form_category: Optional[str]  = None
    description:   Optional[str]  = None
    fields_schema: Optional[Any]  = None
    is_active:     Optional[bool] = None


# ─────────────────────────────────────────────────────────────────────────────
# CustomForm – Response  →  GET endpoints
# ─────────────────────────────────────────────────────────────────────────────

class CustomFormResponse(CustomFormBase):
    """Full form definition returned to the client, including audit timestamps."""
    id:         int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# FormSubmission – Base
# ─────────────────────────────────────────────────────────────────────────────

class FormSubmissionBase(BaseModel):
    """
    Shared fields for a submitted form response:
      form_id      →  which CustomForm was filled
      employee_id  →  who filled it
      submitted_by →  display name / email
      form_data    →  { "field_id": "answer_value", … }
      status       →  Submitted | Reviewed | Processed
    """
    form_id:      int
    employee_id:  int
    submitted_by: Optional[str] = None
    form_data:    Optional[Any] = None
    status:       Optional[str] = "Submitted"


# ─────────────────────────────────────────────────────────────────────────────
# FormSubmission – Create  →  POST /custom-forms/{form_id}/submit
# ─────────────────────────────────────────────────────────────────────────────

class FormSubmissionCreate(FormSubmissionBase):
    """Payload when an employee submits a filled form."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# FormSubmission – Response  →  GET endpoints
# ─────────────────────────────────────────────────────────────────────────────

class FormSubmissionResponse(FormSubmissionBase):
    """Full submission record returned to the client."""
    id:           int
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)