
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete

from model.Forms_Workflows.custom_form import (
    CustomForm,
    FormPage,
    FormSection,
    FormField,
    FormConfiguration,
    FormVersionHistory,
    FormSubmission,
    FormSubmissionAnswer,
)
from schema.Forms_Workflows.custom_form import (
    CustomFormCreate,
    CustomFormUpdate,
    FormSubmissionCreate,
    ReviewSubmission,
    DuplicateFormRequest,
)

logger = logging.getLogger(__name__)


def _get_form_or_404(db: Session, form_id: int) -> CustomForm:
    form = db.execute(
        select(CustomForm).where(
            CustomForm.id == form_id,
            CustomForm.is_deleted.is_(False),
        )
    ).scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form


def _append_history(
    db:      Session,
    form:    CustomForm,
    action:  str,
    actor_id: Optional[int] = None,
) -> None:
    
    form.version    += 1
    form.last_modified = datetime.utcnow()
    entry = FormVersionHistory(
        form_id    = form.id,
        version    = form.version,
        action     = action,
        changed_by = "User" if actor_id else "System",
        actor_id   = actor_id,
    )
    db.add(entry)


def _upsert_pages(db: Session, form: CustomForm, page_numbers: set[int]) -> None:
    
    existing = {p.page_number for p in form.pages}
    for num in sorted(page_numbers):
        if num not in existing:
            db.add(FormPage(form_id=form.id, page_number=num,
                            title=f"Page {num}"))


def _sync_fields(db: Session, form: CustomForm, fields_data: list, actor_id: Optional[int]) -> None:
  
    section_lookup: dict[str, int] = {
        s.client_id: s.id for s in form.sections if s.client_id
    }

  
    db.execute(delete(FormField).where(FormField.form_id == form.id))

    page_numbers: set[int] = set()
    for idx, fd in enumerate(fields_data):
        if hasattr(fd, "model_dump"):
            fd = fd.model_dump()

        # Resolve section
        section_id = fd.get("section_id")
        if not section_id and fd.get("section"):
            section_id = section_lookup.get(fd["section"])

        page_num = fd.get("page_number") or fd.get("page") or 1
        page_numbers.add(int(page_num))

        validation = fd.get("validation")
        if hasattr(validation, "model_dump"):
            validation = validation.model_dump(exclude_none=True)

        conditional = fd.get("conditional")
        if hasattr(conditional, "model_dump"):
            conditional = conditional.model_dump()

        db.add(FormField(
            form_id         = form.id,
            client_field_id = fd.get("client_field_id") or fd.get("id"),
            page_number     = int(page_num),
            section_id      = section_id,
            display_order   = fd.get("display_order", idx),
            field_type      = fd.get("field_type") or fd.get("type", "text"),
            label           = fd.get("label", "Field"),
            placeholder     = fd.get("placeholder"),
            help_text       = fd.get("help_text") or fd.get("helpText"),
            default_value   = fd.get("default_value") or fd.get("defaultValue"),
            options         = fd.get("options"),
            is_required     = fd.get("is_required") or fd.get("required", False),
            validation      = validation,
            conditional     = conditional,
            pre_populate    = fd.get("pre_populate") or fd.get("prePopulate", False),
            pre_populate_type = fd.get("pre_populate_type") or fd.get("prePopulateType"),
        ))

 
    _upsert_pages(db, form, page_numbers)


def _sync_sections(db: Session, form: CustomForm, sections_data: list) -> None:
  
    db.execute(delete(FormSection).where(FormSection.form_id == form.id))
    for idx, sd in enumerate(sections_data):
        if hasattr(sd, "model_dump"):
            sd = sd.model_dump()
        db.add(FormSection(
            form_id       = form.id,
            client_id     = sd.get("client_id") or sd.get("id"),
            page_number   = sd.get("page_number") or sd.get("page", 1),
            title         = sd.get("title", "Section"),
            description   = sd.get("description"),
            display_order = sd.get("display_order", idx),
        ))
    db.flush()  


def _sync_pages(db: Session, form: CustomForm, pages_data: list) -> None:
  
    db.execute(delete(FormPage).where(FormPage.form_id == form.id))
    for pd in pages_data:
        if hasattr(pd, "model_dump"):
            pd = pd.model_dump()
        db.add(FormPage(
            form_id     = form.id,
            page_number = pd.get("page_number", 1),
            title       = pd.get("title"),
        ))


def _sync_configuration(db: Session, form: CustomForm, config_data) -> None:
  
    if hasattr(config_data, "model_dump"):
        config_data = config_data.model_dump()

    post = config_data.get("post_actions") or config_data.get("postActions") or {}
    if hasattr(post, "model_dump"):
        post = post.model_dump()

    if form.configuration:
        cfg = form.configuration
    else:
        cfg = FormConfiguration(form_id=form.id)
        db.add(cfg)

    cfg.availability         = config_data.get("availability", "all")
    cfg.departments          = config_data.get("departments")
    cfg.grades               = config_data.get("grades")
    cfg.submission_window    = config_data.get("submission_window") or config_data.get("submissionWindow", "always")
    cfg.start_date           = config_data.get("start_date") or config_data.get("startDate")
    cfg.end_date             = config_data.get("end_date") or config_data.get("endDate")
    cfg.submission_type      = config_data.get("submission_type") or config_data.get("submissionType", "single")
    cfg.submission_limit     = config_data.get("submission_limit") or config_data.get("submissionLimit", 1)
    cfg.anonymous_submission = config_data.get("anonymous_submission") or config_data.get("anonymousSubmission", False)
    cfg.auto_save            = config_data.get("auto_save") if "auto_save" in config_data else config_data.get("autoSave", True)
    cfg.confirmation_message = config_data.get("confirmation_message") or config_data.get("confirmationMessage", "Thank you!")
    cfg.post_action_email        = post.get("email", False)
    cfg.post_action_notification = post.get("notification", True)
    cfg.post_action_update_data  = post.get("updateData", False) or post.get("update_data", False)


def create_form(
    db:       Session,
    data:     CustomFormCreate,
    actor_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
) -> CustomForm:
 
    form = CustomForm(
        client_form_id = data.client_form_id,
        title          = data.title,
        description    = data.description,
        category       = data.category,
        status         = data.status,
        version        = 1,
        created_by     = actor_id,
        tenant_id      = tenant_id,
    )
    db.add(form)
    db.flush()   

   
    if data.pages:
        _sync_pages(db, form, data.pages)
    else:
      
        db.add(FormPage(form_id=form.id, page_number=1, title="Page 1"))

 
    if data.sections:
        _sync_sections(db, form, data.sections)
        db.flush()

  
    if data.fields:
        _sync_fields(db, form, data.fields, actor_id)


    if data.configuration:
        _sync_configuration(db, form, data.configuration)
    else:
        db.add(FormConfiguration(form_id=form.id))

   
    action = data.history_action or ("Form Published" if data.status == "published" else "Form Created")
    db.add(FormVersionHistory(
        form_id    = form.id,
        version    = 1,
        action     = action,
        changed_by = "User" if actor_id else "System",
        actor_id   = actor_id,
    ))

    db.commit()
    db.refresh(form)
    logger.info("CustomForm %s created (status=%s)", form.id, form.status)
    return form


def list_forms(
    db:           Session,
    tenant_id:    Optional[int] = None,
    status_filter: Optional[str] = None,
    category:     Optional[str] = None,
    is_active:    Optional[bool] = None,
    search:       Optional[str] = None,
    skip:         int = 0,
    limit:        int = 100,
) -> List[CustomForm]:
    stmt = select(CustomForm).where(CustomForm.is_deleted.is_(False))

    if tenant_id:
        stmt = stmt.where(CustomForm.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(CustomForm.status == status_filter)
    if category:
        stmt = stmt.where(CustomForm.category == category)
    if is_active is not None:
        stmt = stmt.where(CustomForm.is_active == is_active)
    if search:
        s = f"%{search.lower()}%"
        from sqlalchemy import func as sf, or_
        stmt = stmt.where(
            or_(
                sf.lower(CustomForm.title).like(s),
                sf.lower(CustomForm.description).like(s),
            )
        )

    stmt = stmt.order_by(CustomForm.updated_at.desc()).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_form(db: Session, form_id: int) -> CustomForm:
    return _get_form_or_404(db, form_id)

def update_form(
    db:       Session,
    form_id:  int,
    data:     CustomFormUpdate,
    actor_id: Optional[int] = None,
) -> CustomForm:

    form = _get_form_or_404(db, form_id)

    changes: list[str] = []

    if data.title is not None:
        form.title = data.title
        changes.append("title updated")
    if data.description is not None:
        form.description = data.description
    if data.category is not None:
        form.category = data.category
    if data.status is not None:
        form.status = data.status
        changes.append(f"status → {data.status}")

    if data.pages is not None:
        _sync_pages(db, form, data.pages)
        changes.append("pages updated")

    if data.sections is not None:
        _sync_sections(db, form, data.sections)
        db.flush()
        changes.append("sections updated")

    if data.fields is not None:
        _sync_fields(db, form, data.fields, actor_id)
        changes.append(f"{len(data.fields)} fields updated")

    if data.configuration is not None:
        _sync_configuration(db, form, data.configuration)
        changes.append("configuration updated")

    action = data.history_action or (", ".join(changes) if changes else "Form Updated")
    _append_history(db, form, action, actor_id)

    db.commit()
    db.refresh(form)
    logger.info("CustomForm %s updated: %s", form_id, action)
    return form


def delete_form(db: Session, form_id: int, actor_id: Optional[int] = None) -> None:
    form = _get_form_or_404(db, form_id)
    form.is_deleted = True
    form.is_active  = False
    form.deleted_at = datetime.utcnow()
    _append_history(db, form, "Form Deleted", actor_id)
    db.commit()
    logger.info("CustomForm %s soft-deleted", form_id)



def publish_form(db: Session, form_id: int, actor_id: Optional[int] = None) -> CustomForm:
    form = _get_form_or_404(db, form_id)
    if form.status == "published":
        raise HTTPException(status_code=400, detail="Form is already published")
    form.status = "published"
    _append_history(db, form, "Form Published", actor_id)
    db.commit()
    db.refresh(form)
    return form


def archive_form(db: Session, form_id: int, actor_id: Optional[int] = None) -> CustomForm:
    form = _get_form_or_404(db, form_id)
    form.status    = "archived"
    form.is_active = False
    _append_history(db, form, "Form Archived", actor_id)
    db.commit()
    db.refresh(form)
    return form


def restore_form(db: Session, form_id: int, actor_id: Optional[int] = None) -> CustomForm:
    form = _get_form_or_404(db, form_id)
    form.status    = "draft"
    form.is_active = True
    _append_history(db, form, "Form Restored to Draft", actor_id)
    db.commit()
    db.refresh(form)
    return form


def duplicate_form(
    db:       Session,
    form_id:  int,
    data:     DuplicateFormRequest,
    actor_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
) -> CustomForm:
   
    original = _get_form_or_404(db, form_id)

    new_form = CustomForm(
        client_form_id = None,
        title          = data.new_title or f"{original.title} (Copy)",
        description    = original.description,
        category       = original.category,
        status         = "draft",
        version        = 1,
        created_by     = actor_id,
        tenant_id      = tenant_id or original.tenant_id,
    )
    db.add(new_form)
    db.flush()

    # Pages
    for page in original.pages:
        db.add(FormPage(
            form_id=new_form.id, page_number=page.page_number, title=page.title
        ))


    section_map: dict[int, int] = {}
    for sec in original.sections:
        new_sec = FormSection(
            form_id       = new_form.id,
            client_id     = sec.client_id,
            page_number   = sec.page_number,
            title         = sec.title,
            description   = sec.description,
            display_order = sec.display_order,
        )
        db.add(new_sec)
        db.flush()
        section_map[sec.id] = new_sec.id

 
    for field in original.fields:
        new_section_id = section_map.get(field.section_id) if field.section_id else None
        db.add(FormField(
            form_id          = new_form.id,
            client_field_id  = field.client_field_id,
            page_number      = field.page_number,
            section_id       = new_section_id,
            display_order    = field.display_order,
            field_type       = field.field_type,
            label            = field.label,
            placeholder      = field.placeholder,
            help_text        = field.help_text,
            default_value    = field.default_value,
            options          = field.options,
            is_required      = field.is_required,
            validation       = field.validation,
            conditional      = field.conditional,
            pre_populate     = field.pre_populate,
            pre_populate_type = field.pre_populate_type,
        ))

   
    if original.configuration:
        cfg = original.configuration
        db.add(FormConfiguration(
            form_id              = new_form.id,
            availability         = cfg.availability,
            departments          = cfg.departments,
            grades               = cfg.grades,
            submission_window    = cfg.submission_window,
            start_date           = cfg.start_date,
            end_date             = cfg.end_date,
            submission_type      = cfg.submission_type,
            submission_limit     = cfg.submission_limit,
            anonymous_submission = cfg.anonymous_submission,
            auto_save            = cfg.auto_save,
            confirmation_message = cfg.confirmation_message,
            post_action_email        = cfg.post_action_email,
            post_action_notification = cfg.post_action_notification,
            post_action_update_data  = cfg.post_action_update_data,
        ))
    else:
        db.add(FormConfiguration(form_id=new_form.id))

    # History
    db.add(FormVersionHistory(
        form_id    = new_form.id,
        version    = 1,
        action     = f"Form duplicated from Form #{original.id}",
        changed_by = "User" if actor_id else "System",
        actor_id   = actor_id,
    ))

    db.commit()
    db.refresh(new_form)
    logger.info("Form %s duplicated → new Form %s", form_id, new_form.id)
    return new_form



def add_field(
    db:       Session,
    form_id:  int,
    field_data,
    actor_id: Optional[int] = None,
) -> FormField:
    form = _get_form_or_404(db, form_id)

    if hasattr(field_data, "model_dump"):
        fd = field_data.model_dump()
    else:
        fd = dict(field_data)

    validation = fd.get("validation")
    if hasattr(validation, "model_dump"):
        validation = validation.model_dump(exclude_none=True)

    conditional = fd.get("conditional")
    if hasattr(conditional, "model_dump"):
        conditional = conditional.model_dump()


    page_num = fd.get("page_number", 1)
    _upsert_pages(db, form, {page_num})

    field = FormField(
        form_id          = form_id,
        client_field_id  = fd.get("client_field_id"),
        page_number      = page_num,
        section_id       = fd.get("section_id"),
        display_order    = fd.get("display_order", 0),
        field_type       = fd.get("field_type", "text"),
        label            = fd.get("label", "New Field"),
        placeholder      = fd.get("placeholder"),
        help_text        = fd.get("help_text"),
        default_value    = fd.get("default_value"),
        options          = fd.get("options"),
        is_required      = fd.get("is_required", False),
        validation       = validation,
        conditional      = conditional,
        pre_populate     = fd.get("pre_populate", False),
        pre_populate_type = fd.get("pre_populate_type"),
    )
    db.add(field)
    _append_history(db, form, f"Added {field.field_type} field '{field.label}' to Page {page_num}", actor_id)
    db.commit()
    db.refresh(field)
    return field


def update_field(
    db:       Session,
    form_id:  int,
    field_id: int,
    field_data,
    actor_id: Optional[int] = None,
) -> FormField:
    _get_form_or_404(db, form_id)
    field = db.execute(
        select(FormField).where(FormField.id == field_id, FormField.form_id == form_id)
    ).scalar_one_or_none()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    fd = field_data.model_dump(exclude_none=True) if hasattr(field_data, "model_dump") else field_data

    for attr in ["page_number", "section_id", "display_order", "label", "placeholder",
                 "help_text", "default_value", "options", "is_required",
                 "pre_populate", "pre_populate_type"]:
        if attr in fd:
            setattr(field, attr, fd[attr])

    if "validation" in fd and fd["validation"]:
        v = fd["validation"]
        field.validation = v.model_dump(exclude_none=True) if hasattr(v, "model_dump") else v

    if "conditional" in fd:
        c = fd["conditional"]
        field.conditional = c.model_dump() if (c and hasattr(c, "model_dump")) else c

    form = _get_form_or_404(db, form_id)
    _append_history(db, form, f"Updated field '{field.label}'", actor_id)
    db.commit()
    db.refresh(field)
    return field


def delete_field(
    db:       Session,
    form_id:  int,
    field_id: int,
    actor_id: Optional[int] = None,
) -> None:
    form = _get_form_or_404(db, form_id)
    field = db.execute(
        select(FormField).where(FormField.id == field_id, FormField.form_id == form_id)
    ).scalar_one_or_none()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    label = field.label
    db.delete(field)
    _append_history(db, form, f"Deleted field '{label}'", actor_id)
    db.commit()


def get_employee_prepopulate_data(db: Session, employee_id: int) -> dict:

    from model.onboarding.employee import Employee
    from model.Employee_Management.employee_master import EmployeeMaster

    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()

    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    full_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip()

    master = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()

    return {
        "employee_name":       full_name or None,
        "employee_email":      emp.official_email or None,
        "employee_department": emp.department or None,
        "employee_grade":      emp.grade or (master.grade if master else None),
    }



def submit_form(
    db:       Session,
    data:     FormSubmissionCreate,
    actor_id: Optional[int] = None,
) -> FormSubmission:

    form = _get_form_or_404(db, data.form_id)

    if not form.is_active:
        raise HTTPException(status_code=400, detail="Form is not active")
    if form.status not in {"published"}:
        raise HTTPException(status_code=400, detail="Form is not published")

    cfg = form.configuration
    if cfg:
   
        if cfg.submission_window == "daterange":
            today = datetime.utcnow().date().isoformat()
            if cfg.start_date and today < cfg.start_date:
                raise HTTPException(status_code=400,
                                    detail=f"Form submissions open on {cfg.start_date}")
            if cfg.end_date and today > cfg.end_date:
                raise HTTPException(status_code=400,
                                    detail=f"Form submissions closed on {cfg.end_date}")

    
        if cfg.submission_type == "single" and data.employee_id:
            existing_count = db.execute(
                select(func.count(FormSubmission.id)).where(
                    FormSubmission.form_id    == data.form_id,
                    FormSubmission.employee_id == data.employee_id,
                    FormSubmission.status     == "submitted",
                )
            ).scalar_one()
            if existing_count >= 1:
                raise HTTPException(
                    status_code=409,
                    detail="This form allows only one submission per employee",
                )


    employee_snapshot: dict | None = None
    if data.employee_id and not data.anonymous:
        try:
            employee_snapshot = get_employee_prepopulate_data(db, data.employee_id)
        except HTTPException:
            pass

    submission = FormSubmission(
        form_id           = data.form_id,
        employee_id       = data.employee_id,
        submitted_by      = actor_id,
        anonymous         = data.anonymous,
        status            = data.status,
        employee_snapshot = employee_snapshot,
        submitted_at      = datetime.utcnow() if data.status == "submitted" else None,
    )
    db.add(submission)
    db.flush()


    field_lookup: dict[str, int] = {}
    form_fields = db.execute(
        select(FormField).where(FormField.form_id == data.form_id)
    ).scalars().all()
    for f in form_fields:
        if f.client_field_id:
            field_lookup[f.client_field_id] = f.id

   
    if data.status == "submitted":
        answered_ids = {
            a.field_id or field_lookup.get(a.client_field_id)
            for a in data.answers
        }
        for f in form_fields:
            if f.is_required and f.id not in answered_ids:
                raise HTTPException(
                    status_code=422,
                    detail=f"Required field '{f.label}' on Page {f.page_number} is missing",
                )

   
    for ans in data.answers:
        field_id = ans.field_id or field_lookup.get(ans.client_field_id)
        if not field_id:
            logger.warning("Skipping answer — field_id not found for %s", ans.client_field_id)
            continue
        db.add(FormSubmissionAnswer(
            submission_id   = submission.id,
            field_id        = field_id,
            client_field_id = ans.client_field_id,
            value           = ans.value,
        ))

    db.commit()
    db.refresh(submission)
    logger.info("FormSubmission %s created for form %s", submission.id, data.form_id)
    return submission


def list_submissions(
    db:        Session,
    form_id:   int,
    status:    Optional[str] = None,
    employee_id: Optional[int] = None,
) -> List[FormSubmission]:
    _get_form_or_404(db, form_id)
    stmt = select(FormSubmission).where(FormSubmission.form_id == form_id)
    if status:
        stmt = stmt.where(FormSubmission.status == status)
    if employee_id:
        stmt = stmt.where(FormSubmission.employee_id == employee_id)
    return db.execute(stmt.order_by(FormSubmission.started_at.desc())).scalars().all()


def get_submission(db: Session, submission_id: int) -> FormSubmission:
    sub = db.execute(
        select(FormSubmission).where(FormSubmission.id == submission_id)
    ).scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


def review_submission(
    db:            Session,
    submission_id: int,
    data:          ReviewSubmission,
    actor_id:      Optional[int] = None,
) -> FormSubmission:
    sub = get_submission(db, submission_id)
    if sub.status not in {"submitted"}:
        raise HTTPException(
            status_code=400,
            detail="Only submitted submissions can be reviewed",
        )
    sub.status      = data.status
    sub.reviewed_at = datetime.utcnow()
    sub.reviewed_by = actor_id
    db.commit()
    db.refresh(sub)
    return sub


def get_form_stats(db: Session, form_id: int) -> dict:
    _get_form_or_404(db, form_id)
    total      = db.execute(select(func.count(FormSubmission.id)).where(FormSubmission.form_id == form_id)).scalar_one()
    submitted  = db.execute(select(func.count(FormSubmission.id)).where(FormSubmission.form_id == form_id, FormSubmission.status == "submitted")).scalar_one()
    drafts     = db.execute(select(func.count(FormSubmission.id)).where(FormSubmission.form_id == form_id, FormSubmission.status == "draft")).scalar_one()
    approved   = db.execute(select(func.count(FormSubmission.id)).where(FormSubmission.form_id == form_id, FormSubmission.status == "approved")).scalar_one()
    fields_cnt = db.execute(select(func.count(FormField.id)).where(FormField.form_id == form_id)).scalar_one()
    pages_cnt  = db.execute(select(func.count(FormPage.id)).where(FormPage.form_id == form_id)).scalar_one()

    return {
        "form_id":          form_id,
        "total_submissions": total,
        "submitted":        submitted,
        "drafts":           drafts,
        "approved":         approved,
        "total_fields":     fields_cnt,
        "total_pages":      pages_cnt,
    }