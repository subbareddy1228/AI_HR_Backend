# schema/Forms_Workflows/custom_form.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, List
from datetime import datetime


# ── Field Definition ──────────────────────────────────────────────────────────
class FormFieldDefinition(BaseModel):
    field_id:      str
    label:         str
    field_type:    str          # text/number/email/phone/date/dropdown/multi_select/radio
                                # checkbox/file_upload/signature/rich_text/rating/section
    placeholder:   Optional[str]       = None
    is_required:   bool                = False
    options:       Optional[List[str]] = None   # for dropdown/radio/multi_select
    default_value: Optional[Any]       = None
    order:         int                 = 0
    width:         Optional[str]       = "full"  # full/half
    help_text:     Optional[str]       = None
    validation:    Optional[Any]       = None    # {min, max, pattern, etc.}


# ── Section Definition ────────────────────────────────────────────────────────
class FormSectionDefinition(BaseModel):
    section_id:  str
    title:       Optional[str]                   = None
    description: Optional[str]                   = None
    fields:      List[FormFieldDefinition]        = []
    order:       int                             = 0


# ── Page Definition ───────────────────────────────────────────────────────────
class FormPageDefinition(BaseModel):
    page_id:     str
    title:       Optional[str]                   = None
    description: Optional[str]                   = None
    sections:    List[FormSectionDefinition]      = []
    order:       int                             = 0


# ── Form Config ───────────────────────────────────────────────────────────────
class FormConfig(BaseModel):
    allow_multiple_submissions: bool         = False
    require_approval:           bool         = False
    approver_role:              Optional[str] = None
    show_progress_bar:          bool         = True
    allow_save_draft:           bool         = True
    prepopulate_fields:         Optional[List[str]] = None


# ── CRUD Schemas ──────────────────────────────────────────────────────────────
class CustomFormCreate(BaseModel):
    form_name:                 str
    form_category:             Optional[str]                 = None
    description:               Optional[str]                 = None
    pages:                     Optional[List[FormPageDefinition]] = None
    fields_schema:             Optional[List[FormFieldDefinition]] = None
    prepopulate_fields:        Optional[List[str]]            = None
    allow_multiple_submissions: bool                          = False
    require_approval:          bool                           = False
    approver_role:             Optional[str]                  = None
    show_progress_bar:         bool                           = True
    allow_save_draft:          bool                           = True
    is_active:                 bool                           = True
    is_published:              bool                           = False
    created_by:                Optional[str]                  = None


class CustomFormUpdate(BaseModel):
    form_name:                 Optional[str]                 = None
    form_category:             Optional[str]                 = None
    description:               Optional[str]                 = None
    pages:                     Optional[List[FormPageDefinition]] = None
    fields_schema:             Optional[List[FormFieldDefinition]] = None
    prepopulate_fields:        Optional[List[str]]            = None
    allow_multiple_submissions: Optional[bool]                = None
    require_approval:          Optional[bool]                 = None
    approver_role:             Optional[str]                  = None
    show_progress_bar:         Optional[bool]                 = None
    allow_save_draft:          Optional[bool]                 = None
    is_active:                 Optional[bool]                 = None
    is_published:              Optional[bool]                 = None


class CustomFormResponse(BaseModel):
    id:                        int
    form_name:                 str
    form_category:             Optional[str]  = None
    description:               Optional[str]  = None
    pages:                     Optional[Any]  = None
    fields_schema:             Optional[Any]  = None
    prepopulate_fields:        Optional[Any]  = None
    allow_multiple_submissions: bool
    require_approval:          bool
    approver_role:             Optional[str]  = None
    show_progress_bar:         bool
    allow_save_draft:          bool
    status:                    str
    is_active:                 bool
    is_published:              bool
    version:                   int
    created_by:                Optional[str]  = None
    created_at:                datetime
    updated_at:                datetime

    model_config = ConfigDict(from_attributes=True)


class CustomFormSummary(BaseModel):
    id:           int
    form_name:    str
    form_category: Optional[str] = None
    status:       str
    is_active:    bool
    is_published: bool
    version:      int
    created_by:   Optional[str]  = None
    created_at:   datetime

    model_config = ConfigDict(from_attributes=True)


# ── Submission Schemas ────────────────────────────────────────────────────────
class FormSubmissionCreate(BaseModel):
    employee_id:    Optional[int]  = None
    employee_name:  Optional[str]  = None
    employee_email: Optional[str]  = None
    department:     Optional[str]  = None
    submitted_by:   Optional[str]  = None
    form_data:      Optional[Any]  = None
    page_data:      Optional[Any]  = None
    status:         str            = "Submitted"


class FormSubmissionUpdate(BaseModel):
    form_data:    Optional[Any] = None
    page_data:    Optional[Any] = None
    status:       Optional[str] = None
    reviewed_by:  Optional[str] = None
    review_notes: Optional[str] = None


class FormSubmissionResponse(BaseModel):
    id:             int
    form_id:        int
    form_version:   Optional[int]  = None
    employee_id:    Optional[int]  = None
    employee_name:  Optional[str]  = None
    employee_email: Optional[str]  = None
    department:     Optional[str]  = None
    submitted_by:   Optional[str]  = None
    form_data:      Optional[Any]  = None
    page_data:      Optional[Any]  = None
    status:         str
    reviewed_by:    Optional[str]  = None
    review_notes:   Optional[str]  = None
    submitted_at:   datetime
    reviewed_at:    Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Version History Schema ────────────────────────────────────────────────────
class FormVersionResponse(BaseModel):
    id:             int
    form_id:        int
    version_number: int
    pages:          Optional[Any] = None
    fields_schema:  Optional[Any] = None
    changed_by:     Optional[str] = None
    change_notes:   Optional[str] = None
    created_at:     datetime

    model_config = ConfigDict(from_attributes=True)


# ── Dashboard Stats ───────────────────────────────────────────────────────────
class FormDashboardStats(BaseModel):
    total_forms:      int
    draft_forms:      int
    published_forms:  int
    archived_forms:   int
    total_submissions: int