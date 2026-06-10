# schema/Payroll/salary_slip.py
# Schemas: SalarySlip + SalarySlipComponent

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ── SalarySlipComponent ────────────────────────────────────────────────────

class SlipComponentBase(BaseModel):
    component_type: str          # 'earning' | 'deduction'
    component_name: str
    component_code: Optional[str] = None
    amount: Decimal
    is_statutory: Optional[bool] = False
    sort_order: Optional[int] = 0


class SlipComponentCreate(SlipComponentBase):
    salary_slip_id: int


class SlipComponentResponse(SlipComponentBase):
    id: int
    salary_slip_id: int

    model_config = ConfigDict(from_attributes=True)


# ── SalarySlip ─────────────────────────────────────────────────────────────

class SalarySlipBase(BaseModel):
    employee_id: int
    payroll_run_id: Optional[int] = None
    slip_month: int
    slip_year: int
    employee_code: str
    employee_name: str
    department: Optional[str] = None
    designation: Optional[str] = None
    pan_number: Optional[str] = None
    uan_number: Optional[str] = None
    bank_account: Optional[str] = None
    bank_name: Optional[str] = None
    official_email: Optional[str] = None
    days_in_month: int = 30
    days_worked: int = 0
    days_absent: int = 0
    lop_days: int = 0
    gross_salary: Decimal
    total_earnings: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    is_published: Optional[bool] = False
    is_emailed: Optional[bool] = False
    pdf_path: Optional[str] = None
    generated_by: Optional[str] = None

    @field_validator("slip_month")
    @classmethod
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("slip_month must be between 1 and 12")
        return v

    @field_validator("slip_year")
    @classmethod
    def validate_year(cls, v):
        if not 2000 <= v <= 2100:
            raise ValueError("slip_year must be between 2000 and 2100")
        return v


class SalarySlipCreate(SalarySlipBase):
    components: Optional[List[SlipComponentBase]] = []


class SalarySlipUpdate(BaseModel):
    bank_account: Optional[str] = None
    bank_name: Optional[str] = None
    gross_salary: Optional[Decimal] = None
    total_earnings: Optional[Decimal] = None
    total_deductions: Optional[Decimal] = None
    net_pay: Optional[Decimal] = None
    is_published: Optional[bool] = None
    is_emailed: Optional[bool] = None
    pdf_path: Optional[str] = None


class SalarySlipResponse(SalarySlipBase):
    id: int
    generated_at: Optional[datetime] = None
    is_deleted: Optional[bool] = False
    components: List[SlipComponentResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ── Generate requests ──────────────────────────────────────────────────────

class SalarySlipGenerateRequest(BaseModel):
    employee_id: int
    slip_month: int
    slip_year: int
    payroll_run_id: Optional[int] = None

    @field_validator("slip_month")
    @classmethod
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("slip_month must be between 1 and 12")
        return v


class SalarySlipBulkGenerateRequest(BaseModel):
    slip_month: int
    slip_year: int
    payroll_run_id: Optional[int] = None

    @field_validator("slip_month")
    @classmethod
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("slip_month must be between 1 and 12")
        return v


# ── Email / Distribution requests ─────────────────────────────────────────

class SendEmailRequest(BaseModel):
    recipient_email: Optional[str] = None   # override; defaults to employee's official email
    cc_hr: Optional[bool] = False


class BulkSendEmailRequest(BaseModel):
    slip_month: int
    slip_year: int

    @field_validator("slip_month")
    @classmethod
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("slip_month must be between 1 and 12")
        return v


# ── KPI Summary ────────────────────────────────────────────────────────────

class SalarySlipKPIResponse(BaseModel):
    total_slips_generated: int
    active_employees: int
    distributed_slips: int
    total_payout: Decimal
    slip_month: Optional[int] = None
    slip_year: Optional[int] = None
