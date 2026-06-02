# FILE 9 (2/8) | schema/Payroll/payroll_run.py
# Schemas: PayrollRunBase/Create/Update/Response
#          PayrollRunDetailBase/Create/Response

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal


# ── PayrollRun ──────────────────────────────────────────────────────────────

class PayrollRunBase(BaseModel):
    run_month: int
    run_year: int
    status: Optional[str] = "Draft"
    total_employees: Optional[int] = 0
    total_gross: Optional[Decimal] = Decimal("0.00")
    total_deductions: Optional[Decimal] = Decimal("0.00")
    total_net_pay: Optional[Decimal] = Decimal("0.00")
    run_by: Optional[str] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None


class PayrollRunCreate(PayrollRunBase):
    pass


class PayrollRunUpdate(BaseModel):
    status: Optional[str] = None
    total_employees: Optional[int] = None
    total_gross: Optional[Decimal] = None
    total_deductions: Optional[Decimal] = None
    total_net_pay: Optional[Decimal] = None
    run_by: Optional[str] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None


class PayrollRunResponse(PayrollRunBase):
    id: int
    run_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── PayrollRunDetail ────────────────────────────────────────────────────────

class PayrollRunDetailBase(BaseModel):
    payroll_run_id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department: Optional[str] = None
    designation: Optional[str] = None
    days_in_month: int
    days_worked: int
    days_absent: int
    basic: Decimal
    hra: Decimal
    special_allowance: Decimal
    gross_salary: Decimal
    pf_employee: Decimal
    esi_employee: Decimal
    professional_tax: Decimal
    tds: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    status: Optional[str] = "Pending"


class PayrollRunDetailCreate(PayrollRunDetailBase):
    pass


class PayrollRunDetailResponse(PayrollRunDetailBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
