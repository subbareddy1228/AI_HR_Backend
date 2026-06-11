

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Any, Dict, Union
from pydantic import BaseModel, field_validator, model_validator, ConfigDict

VALID_FIELD_TYPES = {
    "text", "number", "email", "phone", "date",
    "dropdown", "multi-select", "radio",
    "checkbox", "file", "signature",
    "rich-text", "rating", "section",
}

VALID_CATEGORIES = {
    "General", "HR", "Finance", "IT",
    "Operations", "Administrative", "Feedback",
}

VALID_STATUSES = {"draft", "published", "archived"}

VALID_AVAILABILITY = {"all", "departments", "grades"}

VALID_SUBMISSION_TYPES = {"single", "multiple"}

VALID_SUBMISSION_WINDOWS = {"always", "daterange"}

VALID_PREPOPULATE_TYPES = {
    "employee_name", "employee_email",
    "employee_department", "employee_grade",
}

VALID_CONDITIONS = {"equals", "not-equals", "contains", "greater-than", "less-than"}

class FieldValidation(BaseModel):
  
    pattern:   Optional[str]   = None
    minLength: Optional[int]   = None
    maxLength: Optional[int]   = None
    min:       Optional[float] = None
    max:       Optional[float] = None


class FieldConditional(BaseModel):
 
    dependsOn: str            
    condition:  str            
    value:      str

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v):
        if v not in VALID_CONDITIONS:
            raise ValueError(f"condition must be one of {VALID_CONDITIONS}")
        return v


class PostActions(BaseModel):
    email:        bool = False
    notification: bool = True
    updateData:   bool = False

class FormPageCreate(BaseModel):
    page_number: int
    title:       Optional[str] = None


class FormPageResponse(FormPageCreate):
    id:      int
    form_id: int
    model_config = ConfigDict(from_attributes=True)


class FormSectionCreate(BaseModel):
    client_id:     Optional[str] = None   # "section_<ts>" from frontend
    page_number:   int           = 1
    title:         str           = "Section"
    description:   Optional[str] = None
    display_order: int           = 0


class FormSectionResponse(FormSectionCreate):
    id:      int
    form_id: int
    model_config = ConfigDict(from_attributes=True)



class FormFieldCreate(BaseModel):
    client_field_id:  Optional[str]            = None   
    page_number:      int                       = 1
    section_id:       Optional[int]            = None
    display_order:    int                       = 0
    field_type:       str
    label:            str
    placeholder:      Optional[str]            = None
    help_text:        Optional[str]            = None
    default_value:    Optional[str]            = None
    options:          Optional[List[str]]      = None   
    is_required:      bool                      = False
    validation:       Optional[FieldValidation] = None
    conditional:      Optional[FieldConditional] = None
    pre_populate:     bool                      = False
    pre_populate_type: Optional[str]           = None

    @field_validator("field_type")
    @classmethod
    def validate_field_type(cls, v):
        if v not in VALID_FIELD_TYPES:
            raise ValueError(f"field_type must be one of {VALID_FIELD_TYPES}")
        return v

    @field_validator("pre_populate_type")
    @classmethod
    def validate_prepopulate_type(cls, v):
        if v and v not in VALID_PREPOPULATE_TYPES:
            raise ValueError(f"pre_populate_type must be one of {VALID_PREPOPULATE_TYPES}")
        return v

    @model_validator(mode="after")
    def options_required_for_choice_fields(self):
        choice_types = {"dropdown", "radio", "multi-select"}
        if self.field_type in choice_types and not self.options:
            self.options = ["Option 1", "Option 2", "Option 3"]
        return self


class FormFieldUpdate(BaseModel):
  
    page_number:      Optional[int]             = None
    section_id:       Optional[int]            = None
    display_order:    Optional[int]             = None
    label:            Optional[str]             = None
    placeholder:      Optional[str]             = None
    help_text:        Optional[str]             = None
    default_value:    Optional[str]             = None
    options:          Optional[List[str]]       = None
    is_required:      Optional[bool]            = None
    validation:       Optional[FieldValidation] = None
    conditional:      Optional[FieldConditional] = None
    pre_populate:     Optional[bool]            = None
    pre_populate_type: Optional[str]            = None


class FormFieldResponse(BaseModel):
    id:               int
    form_id:          int
    client_field_id:  Optional[str]
    page_number:      int
    section_id:       Optional[int]
    display_order:    int
    field_type:       str
    label:            str
    placeholder:      Optional[str]
    help_text:        Optional[str]
    default_value:    Optional[str]
    options:          Optional[List[str]]
    is_required:      bool
    validation:       Optional[Dict[str, Any]]
    conditional:      Optional[Dict[str, Any]]
    pre_populate:     bool
    pre_populate_type: Optional[str]
    created_at:       datetime
    updated_at:       datetime
    model_config = ConfigDict(from_attributes=True)


class FormConfigurationCreate(BaseModel):
    availability:         str            = "all"
    departments:          Optional[List[str]] = None
    grades:               Optional[List[str]] = None
    submission_window:    str            = "always"
    start_date:           Optional[str] = None
    end_date:             Optional[str] = None
    submission_type:      str            = "single"
    submission_limit:     int            = 1
    anonymous_submission: bool           = False
    auto_save:            bool           = True
    confirmation_message: Optional[str] = "Thank you for your submission!"
    post_actions:         PostActions    = PostActions()

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, v):
        if v not in VALID_AVAILABILITY:
            raise ValueError(f"availability must be one of {VALID_AVAILABILITY}")
        return v

    @field_validator("submission_type")
    @classmethod
    def validate_submission_type(cls, v):
        if v not in VALID_SUBMISSION_TYPES:
            raise ValueError(f"submission_type must be one of {VALID_SUBMISSION_TYPES}")
        return v

    @field_validator("submission_window")
    @classmethod
    def validate_window(cls, v):
        if v not in VALID_SUBMISSION_WINDOWS:
            raise ValueError(f"submission_window must be one of {VALID_SUBMISSION_WINDOWS}")
        return v

    @field_validator("submission_limit")
    @classmethod
    def validate_limit(cls, v):
        if v < 1:
            raise ValueError("submission_limit must be at least 1")
        return v


class FormConfigurationResponse(BaseModel):
    id:                   int
    form_id:              int
    availability:         str
    departments:          Optional[List[str]]
    grades:               Optional[List[str]]
    submission_window:    str
    start_date:           Optional[str]
    end_date:             Optional[str]
    submission_type:      str
    submission_limit:     int
    anonymous_submission: bool
    auto_save:            bool
    confirmation_message: Optional[str]
    post_action_email:        bool
    post_action_notification: bool
    post_action_update_data:  bool
    model_config = ConfigDict(from_attributes=True)


class VersionHistoryResponse(BaseModel):
    id:         int
    version:    int
    action:     str
    changed_by: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)



class CustomFormCreate(BaseModel):
   
    client_form_id: Optional[str]  = None   # "form_<ts>"
    title:          str
    description:    Optional[str]  = None
    category:       str            = "General"
    status:         str            = "draft"
    version:        int            = 1

   
    pages:          Optional[List[FormPageCreate]]          = None
    sections:       Optional[List[FormSectionCreate]]       = None
    fields:         Optional[List[FormFieldCreate]]         = None
    configuration:  Optional[FormConfigurationCreate]       = None

  
    history_action: Optional[str] = None  

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v


class CustomFormUpdate(BaseModel):
  
    title:          Optional[str] = None
    description:    Optional[str] = None
    category:       Optional[str] = None
    status:         Optional[str] = None
    pages:          Optional[List[FormPageCreate]]    = None
    sections:       Optional[List[FormSectionCreate]] = None
    fields:         Optional[List[FormFieldCreate]]   = None
    configuration:  Optional[FormConfigurationCreate] = None
    history_action: Optional[str]                     = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v and v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        return v


class CustomFormSummary(BaseModel):
   
    id:            int
    client_form_id: Optional[str]
    title:          str
    description:    Optional[str]
    category:       str
    status:         str
    version:        int
    is_active:      bool
    total_fields:   int = 0
    total_pages:    int = 0
    created_at:     datetime
    updated_at:     datetime
    last_modified:  datetime
    model_config = ConfigDict(from_attributes=True)


class CustomFormResponse(BaseModel):
    
    id:             int
    client_form_id: Optional[str]
    title:          str
    description:    Optional[str]
    category:       str
    status:         str
    version:        int
    is_active:      bool
    pages:          List[FormPageResponse]          = []
    sections:       List[FormSectionResponse]       = []
    fields:         List[FormFieldResponse]         = []
    configuration:  Optional[FormConfigurationResponse] = None
    version_history: List[VersionHistoryResponse]   = []
    created_at:     datetime
    updated_at:     datetime
    last_modified:  datetime
    model_config = ConfigDict(from_attributes=True)


class AnswerCreate(BaseModel):
    """One field's answer inside a submission."""
    field_id:        Optional[int]  = None  
    client_field_id: Optional[str] = None   
    value:           Any           

    @model_validator(mode="after")
    def needs_field_ref(self):
        if not self.field_id and not self.client_field_id:
            raise ValueError("Either field_id or client_field_id is required")
        return self


class FormSubmissionCreate(BaseModel):
  
    form_id:           int
    employee_id:       Optional[int]        = None
    anonymous:         bool                 = False
    status:            str                  = "submitted"
    # draft | submitted
    answers:           List[AnswerCreate]   = []

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in {"draft", "submitted"}:
            raise ValueError("status must be 'draft' or 'submitted'")
        return v


class AnswerResponse(BaseModel):
    id:              int
    field_id:        int
    client_field_id: Optional[str]
    value:           Any
    model_config = ConfigDict(from_attributes=True)


class FormSubmissionResponse(BaseModel):
    id:                 int
    form_id:            int
    employee_id:        Optional[int]
    anonymous:          bool
    status:             str
    employee_snapshot:  Optional[Dict[str, Any]]
    answers:            List[AnswerResponse] = []
    started_at:         datetime
    submitted_at:       Optional[datetime]
    reviewed_at:        Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class ReviewSubmission(BaseModel):
    
    status:  str    
    remarks: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in {"reviewed", "approved", "rejected"}:
            raise ValueError("status must be reviewed | approved | rejected")
        return v


class DuplicateFormRequest(BaseModel):
    new_title: Optional[str] = None   


class PrePopulateResponse(BaseModel):
    employee_name:       Optional[str] = None
    employee_email:      Optional[str] = None
    employee_department: Optional[str] = None
    employee_grade:      Optional[str] = None
    