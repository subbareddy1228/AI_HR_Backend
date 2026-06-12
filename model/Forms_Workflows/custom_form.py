from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from core.database import Base
from datetime import datetime


class CustomForm(Base):
    """
    Stores every form definition created inside the Custom Form Builder.

    Frontend – Form Design Interface  (Image 1)
    ─────────────────────────────────────────────────────────────────────
    Field Types panel    : Text | Number | Email | Phone | Date | Dropdown
                           Multi Select | Radio | Checkbox | File Upload
                           Signature | Rich Text | Rating | Section
    Pre-populate panel   : Employee Name | Email Address |
                           Department | Designation / Position
    Canvas               : Multi-page builder  (Page 1 … Page N)
                           Add Section | Add Another Page buttons
    Toolbar buttons      : Preview | Save | Duplicate | Publish | Clear | Reset
    Version History      : Timestamped changelog at bottom of page

    Frontend – Form Configuration tab  (Image 2)
    ─────────────────────────────────────────────────────────────────────
    form_name         →  "Form Title" text input
    form_category     →  "Form Category" dropdown  (General …)
    description       →  "Form Description" textarea
    is_active         →  controlled by Publish button in toolbar

    Advanced Settings (Image 2 — right panel):
    ─────────────────────────────────────────────────────────────────────
    anonymous_submission    →  "Anonymous Submission" checkbox
    auto_save_draft         →  "Auto-save Draft" toggle
    confirmation_message    →  textarea  ("Thank you for your submission!")
    post_submission_actions →  Send Email Notification | Send In-app
                               Notification | Update Employee Data
    submission_type         →  Single Submission | Multiple Submissions
    availability            →  All Employees | specific group
    submission_window       →  Always Available | date range

    All canvas structure + Advanced Settings are persisted inside
    fields_schema (JSON) to avoid rigid column sprawl.
    """

    __tablename__ = "custom_forms"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id            = Column(Integer,     primary_key=True, index=True)

    # ── Form Configuration tab ────────────────────────────────────────────────
    form_name     = Column(String(255), nullable=False)
    form_category = Column(String(100), nullable=True)    # General | HR | Leave …
    description   = Column(Text,        nullable=True)

    # ── Canvas + Advanced Settings (JSON) ─────────────────────────────────────
    # Structure:
    # {
    #   "pages": [
    #     { "title": "Page 1", "fields": [
    #         { "id": "f1", "type": "text", "label": "Employee Name",
    #           "required": true, "placeholder": "...", "options": [] }
    #     ]}
    #   ],
    #   "advanced": {
    #     "anonymous_submission": false,
    #     "auto_save_draft": true,
    #     "confirmation_message": "Thank you for your submission!",
    #     "post_submission_actions": {
    #         "send_email_notification": true,
    #         "send_inapp_notification": false,
    #         "update_employee_data": false
    #     },
    #     "submission_type": "Single Submission",
    #     "availability": "All Employees",
    #     "submission_window": "Always Available"
    #   }
    # }
    fields_schema = Column(JSON,        nullable=True)

    # ── Publish state ─────────────────────────────────────────────────────────
    is_active     = Column(Boolean,     nullable=False, default=True)

    # ── Ownership ─────────────────────────────────────────────────────────────
    created_by    = Column(String(255), nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at    = Column(DateTime,    nullable=False, default=datetime.utcnow)
    updated_at    = Column(DateTime,    nullable=False, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def __repr__(self):
        return (
            f"<CustomForm id={self.id} "
            f"name={self.form_name!r} "
            f"active={self.is_active}>"
        )


class FormSubmission(Base):
    """
    One employee's submitted response to a CustomForm.

    form_data mirrors the fields_schema field structure:
        { "field_id": "answer_value", … }

    status lifecycle:
        Submitted → Reviewed → Processed
    """

    __tablename__ = "form_submissions"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id           = Column(Integer,     primary_key=True, index=True)

    # ── Which form was submitted ───────────────────────────────────────────────
    form_id      = Column(Integer,     ForeignKey("custom_forms.id"), nullable=False)

    # ── Who submitted it ──────────────────────────────────────────────────────
    employee_id  = Column(Integer,     nullable=False, index=True)
    submitted_by = Column(String(255), nullable=True)     # display name / email

    # ── Field answers ─────────────────────────────────────────────────────────
    form_data    = Column(JSON,        nullable=True)

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    status       = Column(String(30),  nullable=False, default="Submitted")

    # ── Audit ─────────────────────────────────────────────────────────────────
    submitted_at = Column(DateTime,    nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<FormSubmission id={self.id} "
            f"form_id={self.form_id} "
            f"employee_id={self.employee_id} "
            f"status={self.status!r}>"
        )