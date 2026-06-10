# schema/Payroll/slip_distribution.py
# Schemas: SlipDistributionLog, SlipSettings

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# ── SlipDistributionLog ────────────────────────────────────────────────────

class DistributionLogResponse(BaseModel):
    id: int
    salary_slip_id: int
    employee_id: int
    distribution_method: str
    recipient_email: Optional[str] = None
    sent_at: Optional[datetime] = None
    sent_by: Optional[str] = None
    status: str
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── SlipSettings ───────────────────────────────────────────────────────────

class SlipSettingsBase(BaseModel):
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    signatory_name: Optional[str] = None
    footer_text: Optional[str] = None
    confidentiality_note: Optional[str] = None
    email_subject_template: Optional[str] = "Your Salary Slip for [Month Year]"
    email_body_template: Optional[str] = None
    password_protect: Optional[bool] = True
    password_type: Optional[str] = "dob"      # 'dob' | 'employee_id' | 'custom'
    custom_password: Optional[str] = None
    auto_email_on_publish: Optional[bool] = False
    retention_months: Optional[int] = 12
    allow_revisions: Optional[bool] = True
    revision_window_days: Optional[int] = 7


class SlipSettingsUpdate(SlipSettingsBase):
    pass


class SlipSettingsResponse(SlipSettingsBase):
    id: int
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
