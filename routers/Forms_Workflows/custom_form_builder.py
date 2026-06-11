
from __future__ import annotations
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from model.models import User
from schema.Forms_Workflows.custom_form import (
    CustomFormCreate,
    CustomFormUpdate,
    CustomFormSummary,
    CustomFormResponse,
    FormFieldCreate,
    FormFieldUpdate,
    FormFieldResponse,
    FormSubmissionCreate,
    FormSubmissionResponse,
    ReviewSubmission,
    DuplicateFormRequest,
    PrePopulateResponse,
)
from services.Forms_Workflows.custom_form_service import (
    create_form,
    list_forms,
    get_form,
    update_form,
    delete_form,
    publish_form,
    archive_form,
    restore_form,
    duplicate_form,
    add_field,
    update_field,
    delete_field,
    submit_form,
    list_submissions,
    get_submission,
    review_submission,
    get_employee_prepopulate_data,
    get_form_stats,
)

router = APIRouter(
    prefix="/custom-forms",
    tags=["Forms & Workflows - Custom Form Builder"],
)


@router.get("/", response_model=List[CustomFormSummary])
def list_forms_endpoint(
    status_filter: Optional[str]  = Query(None, alias="status"),
    category:      Optional[str]  = Query(None),
    is_active:     Optional[bool] = Query(None),
    search:        Optional[str]  = Query(None, description="Search by title or description"),
    skip:          int            = Query(0,   ge=0),
    limit:         int            = Query(100, ge=1, le=500),
    current_user:  User           = Depends(get_current_user),
    db:            Session        = Depends(get_db),
):

    tenant_id = getattr(current_user, "tenant_id", None)
    forms = list_forms(
        db,
        tenant_id     = tenant_id,
        status_filter = status_filter,
        category      = category,
        is_active     = is_active,
        search        = search,
        skip          = skip,
        limit         = limit,
    )

   
    result = []
    for form in forms:
        total_fields = len(form.fields)
        total_pages  = len(form.pages)
        summary = CustomFormSummary(
            id             = form.id,
            client_form_id = form.client_form_id,
            title          = form.title,
            description    = form.description,
            category       = form.category,
            status         = form.status,
            version        = form.version,
            is_active      = form.is_active,
            total_fields   = total_fields,
            total_pages    = max(total_pages, 1),
            created_at     = form.created_at,
            updated_at     = form.updated_at,
            last_modified  = form.last_modified,
        )
        result.append(summary)
    return result


@router.post("/", response_model=CustomFormResponse, status_code=status.HTTP_201_CREATED)
def create_form_endpoint(
    payload:      CustomFormCreate,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
  
    tenant_id = getattr(current_user, "tenant_id", None)
    return create_form(db, payload, actor_id=current_user.id, tenant_id=tenant_id)


@router.get("/{form_id}", response_model=CustomFormResponse)
def get_form_endpoint(
    form_id:      int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
 
    return get_form(db, form_id)


@router.put("/{form_id}", response_model=CustomFormResponse)
def update_form_endpoint(
    form_id:      int,
    payload:      CustomFormUpdate,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):

    return update_form(db, form_id, payload, actor_id=current_user.id)


@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form_endpoint(
    form_id:      int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):

    delete_form(db, form_id, actor_id=current_user.id)


@router.patch("/{form_id}/publish", response_model=CustomFormResponse)
def publish_form_endpoint(
    form_id:      int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
  
    return publish_form(db, form_id, actor_id=current_user.id)


@router.patch("/{form_id}/archive", response_model=CustomFormResponse)
def archive_form_endpoint(
    form_id:      int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):

    return archive_form(db, form_id, actor_id=current_user.id)


@router.patch("/{form_id}/restore", response_model=CustomFormResponse)
def restore_form_endpoint(
    form_id:      int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
 
    return restore_form(db, form_id, actor_id=current_user.id)


@router.post("/{form_id}/duplicate", response_model=CustomFormResponse,
             status_code=status.HTTP_201_CREATED)
def duplicate_form_endpoint(
    form_id:      int,
    payload:      DuplicateFormRequest = DuplicateFormRequest(),
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
   
    tenant_id = getattr(current_user, "tenant_id", None)
    return duplicate_form(db, form_id, payload, actor_id=current_user.id, tenant_id=tenant_id)



@router.post("/{form_id}/fields", response_model=FormFieldResponse,
             status_code=status.HTTP_201_CREATED)
def add_field_endpoint(
    form_id:      int,
    payload:      FormFieldCreate,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
   
    return add_field(db, form_id, payload, actor_id=current_user.id)


@router.put("/{form_id}/fields/{field_id}", response_model=FormFieldResponse)
def update_field_endpoint(
    form_id:      int,
    field_id:     int,
    payload:      FormFieldUpdate,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    
    return update_field(db, form_id, field_id, payload, actor_id=current_user.id)


@router.delete("/{form_id}/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field_endpoint(
    form_id:      int,
    field_id:     int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
 
    delete_field(db, form_id, field_id, actor_id=current_user.id)


@router.get("/pre-populate/{employee_id}", response_model=PrePopulateResponse)
def get_prepopulate_data(
    employee_id:  int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):

    data = get_employee_prepopulate_data(db, employee_id)
    return PrePopulateResponse(**data)


@router.post("/{form_id}/submit", response_model=FormSubmissionResponse,
             status_code=status.HTTP_201_CREATED)
def submit_form_endpoint(
    form_id:      int,
    payload:      FormSubmissionCreate,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):

    payload.form_id = form_id   # path takes precedence
    return submit_form(db, payload, actor_id=current_user.id)


@router.get("/{form_id}/submissions", response_model=List[FormSubmissionResponse])
def list_submissions_endpoint(
    form_id:      int,
    status_filter: Optional[str] = Query(None, alias="status"),
    employee_id:  Optional[int]  = Query(None),
    current_user: User           = Depends(get_current_user),
    db:           Session        = Depends(get_db),
):
    
    return list_submissions(db, form_id, status=status_filter, employee_id=employee_id)


@router.get("/submissions/{submission_id}", response_model=FormSubmissionResponse)
def get_submission_endpoint(
    submission_id: int,
    current_user:  User    = Depends(get_current_user),
    db:            Session = Depends(get_db),
):
 
    return get_submission(db, submission_id)


@router.patch("/submissions/{submission_id}/review", response_model=FormSubmissionResponse)
def review_submission_endpoint(
    submission_id: int,
    payload:       ReviewSubmission,
    current_user:  User    = Depends(get_current_user),
    db:            Session = Depends(get_db),
):

    return review_submission(db, submission_id, payload, actor_id=current_user.id)



@router.get("/{form_id}/stats")
def form_stats_endpoint(
    form_id:      int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):

    return get_form_stats(db, form_id)