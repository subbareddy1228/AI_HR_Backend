
from pydantic import BaseModel, ConfigDict, field_validator, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


class SlipStatus(str, Enum):
    GENERATED   = "generated"
    DISTRIBUTED = "distributed"
    REVOKED     = "revoked"


class DistributionMethod(str, Enum):
    EMAIL            = "email"
    PORTAL           = "portal"
    EMAIL_AND_PORTAL = "email_and_portal"
    MANUAL           = "manual"


class PasswordStrength(str, Enum):
    EMPLOYEE_ID = "employee_id"
    DOB         = "dob"
    LAST4_PAN   = "last4_pan"
    CUSTOM      = "custom"


class DistributionStatus(str, Enum):
    PENDING = "pending"
    SENT    = "sent"
    FAILED  = "failed"
    VIEWED  = "viewed"



class SalarySlipBase(BaseModel):
    # Original fields
    employee_id:      int
    payroll_run_id:   Optional[int]     = None
    slip_month:       int
    slip_year:        int
    employee_code:    str
    employee_name:    str
    department:       Optional[str]     = None
    designation:      Optional[str]     = None
    bank_account:     Optional[str]     = None
    bank_name:        Optional[str]     = None
    gross_salary:     Decimal
    total_deductions: Decimal
    net_pay:          Decimal
    earnings_json:    Optional[str]     = None
    deductions_json:  Optional[str]     = None
    is_published:     Optional[bool]    = False

    # New fields
    slip_code:             Optional[str]               = None
    status:                SlipStatus                  = SlipStatus.GENERATED
    distribution_method:   DistributionMethod          = DistributionMethod.EMAIL
    is_password_protected: bool                        = True
    pdf_path:              Optional[str]               = None
    generated_by:          Optional[int]               = None


class SalarySlipCreate(SalarySlipBase):
    pass


class SalarySlipUpdate(BaseModel):
    # Original
    bank_account:     Optional[str]     = None
    bank_name:        Optional[str]     = None
    gross_salary:     Optional[Decimal] = None
    total_deductions: Optional[Decimal] = None
    net_pay:          Optional[Decimal] = None
    earnings_json:    Optional[str]     = None
    deductions_json:  Optional[str]     = None
    is_published:     Optional[bool]    = None
    # New
    status:                Optional[SlipStatus]          = None
    distribution_method:   Optional[DistributionMethod]  = None
    is_password_protected: Optional[bool]                = None
    pdf_path:              Optional[str]                 = None


class SalarySlipResponse(SalarySlipBase):
    id:              int
    slip_code:       Optional[str]      = None
    generated_at:    Optional[datetime] = None
    distributed_at:  Optional[datetime] = None
    revised_at:      Optional[datetime] = None
    revision_count:  int                = 0

    model_config = ConfigDict(from_attributes=True)


class GenerateSlipRequest(BaseModel):

    employee_id:         int
    pay_period_month:    int    
    pay_period_year:     int
    distribution_method: DistributionMethod = DistributionMethod.EMAIL
    protect_with_dob:    bool  = True       


class GenerateAllRequest(BaseModel):

    pay_period_month:    int
    pay_period_year:     int
    distribution_method: DistributionMethod = DistributionMethod.EMAIL
    protect_with_dob:    bool  = True
    employee_ids:        Optional[List[int]] = None   


class GenerateSlipResponse(BaseModel):

    generated:  List[SalarySlipResponse]
    skipped:    int = 0    
    failed:     int = 0
    total_payout: Decimal = Decimal("0")

    model_config = ConfigDict(from_attributes=True)


class SalarySlipDistributionBase(BaseModel):
    slip_id:         int
    method:          DistributionMethod
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None


class SalarySlipDistributionCreate(SalarySlipDistributionBase):
    pass


class SalarySlipDistributionResponse(SalarySlipDistributionBase):
    id:             int
    status:         DistributionStatus
    sent_at:        Optional[datetime] = None
    viewed_at:      Optional[datetime] = None
    failure_reason: Optional[str]      = None
    created_at:     Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DistributeSlipRequest(BaseModel):

    slip_id:         int
    method:          DistributionMethod = DistributionMethod.EMAIL
    recipient_email: Optional[str]      = None
    recipient_phone: Optional[str]      = None


class BulkDistributeRequest(BaseModel):

    pay_period_month: int
    pay_period_year:  int
    method:           DistributionMethod = DistributionMethod.EMAIL


class SalarySlipConfigBase(BaseModel):
    config_name:              str     = "default"
    # Company Info
    company_name:             Optional[str] = None
    company_address:          Optional[str] = None
    authorized_signatory:     Optional[str] = None
    # Document Settings
    footer_text:              Optional[str] = "Generated by HRMS Salary Slip System v2.0"
    confidentiality_text:     Optional[str] = (
        "This document is confidential and intended only for the employee. "
        "Unauthorized distribution is prohibited."
    )
    retention_period_months:  int           = 12
    # Advanced — Logo & Seal
    logo_url:                 Optional[str] = None
    seal_url:                 Optional[str] = None
    # Advanced — Security
    password_strength:        PasswordStrength = PasswordStrength.EMPLOYEE_ID
    # Advanced — Notifications
    auto_send_on_generation:  bool          = True
    auto_send_time:           str           = "09:00"
    # Advanced — Revisions
    allow_salary_slip_revisions: bool       = True
    revision_allowed_days:       int        = 7


class SalarySlipConfigCreate(SalarySlipConfigBase):
    pass


class SalarySlipConfigUpdate(BaseModel):
    company_name:               Optional[str]              = None
    company_address:            Optional[str]              = None
    authorized_signatory:       Optional[str]              = None
    footer_text:                Optional[str]              = None
    confidentiality_text:       Optional[str]              = None
    retention_period_months:    Optional[int]              = None
    logo_url:                   Optional[str]              = None
    seal_url:                   Optional[str]              = None
    password_strength:          Optional[PasswordStrength] = None
    auto_send_on_generation:    Optional[bool]             = None
    auto_send_time:             Optional[str]              = None
    allow_salary_slip_revisions: Optional[bool]            = None
    revision_allowed_days:      Optional[int]              = None


class SalarySlipConfigResponse(SalarySlipConfigBase):
    id:         int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)



class DistributionSettingsBase(BaseModel):
    config_name:                  str  = "default"
    send_automatic_email:         bool = True
    cc_hr_department:             bool = True
    bcc_accounts_department:      bool = False
    email_subject:                str  = "Your Salary Slip for [Month Year]"
    email_template:               Optional[str] = None
    # Portal & SMS
    default_password_type:        PasswordStrength = PasswordStrength.EMPLOYEE_ID
    send_sms_notification:        bool = True
    enable_employee_portal_access: bool = True
    auto_send_time:               str  = "09:00"


class DistributionSettingsCreate(DistributionSettingsBase):
    pass


class DistributionSettingsUpdate(BaseModel):
    send_automatic_email:         Optional[bool]              = None
    cc_hr_department:             Optional[bool]              = None
    bcc_accounts_department:      Optional[bool]              = None
    email_subject:                Optional[str]               = None
    email_template:               Optional[str]               = None
    default_password_type:        Optional[PasswordStrength]  = None
    send_sms_notification:        Optional[bool]              = None
    enable_employee_portal_access: Optional[bool]             = None
    auto_send_time:               Optional[str]               = None


class DistributionSettingsResponse(DistributionSettingsBase):
    id:         int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)



class SalarySlipDashboard(BaseModel):
    total_slips_generated: int
    active_employees:      int
    distributed_slips:     int
    total_payout:          Decimal



class SlipHistoryRow(BaseModel):

    id:              int
    slip_code:       Optional[str]    = None
    employee_id:     int
    employee_code:   str
    employee_name:   str
    department:      Optional[str]    = None
    designation:     Optional[str]    = None
    pay_period:      str             
    net_pay:         Decimal
    gross_salary:    Decimal
    status:          SlipStatus
    date_generated:  Optional[datetime] = None
    distributed_at:  Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SlipHistoryResponse(BaseModel):
    total:       int
    slips:       List[SlipHistoryRow]
    total_payout: Decimal

class ExportRequest(BaseModel):
    slip_ids:         Optional[List[int]] = None   
    pay_period_month: Optional[int]       = None
    pay_period_year:  Optional[int]       = None
    format:           str                 = "excel"  


class PrintReportRequest(BaseModel):
    pay_period_month: int
    pay_period_year:  int
    department:       Optional[str] = None