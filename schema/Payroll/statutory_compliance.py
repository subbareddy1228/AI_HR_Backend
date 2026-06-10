# schema/Payroll/statutory_compliance.py
# REPLACE your existing file with this

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


# ─────────────────────────────────────────────────────────────────────────────
# STATUTORY CONFIG
# ─────────────────────────────────────────────────────────────────────────────

class StatutoryConfigBase(BaseModel):
    config_name: Optional[str] = "default"
    # PF
    pf_wage_limit: Optional[Decimal] = Decimal("15000.00")
    pf_employee_rate: Optional[float] = 12.0
    pf_employer_rate: Optional[float] = 12.0
    eps_rate: Optional[float] = 3.67
    edli_rate: Optional[float] = 0.5
    vpf_enabled: Optional[bool] = True
    default_vpf_rate: Optional[float] = 0.0
    uan_mandatory: Optional[bool] = True
    auto_pf_calculation: Optional[bool] = True
    pf_min_salary: Optional[Decimal] = Decimal("0.00")
    pf_max_salary: Optional[Decimal] = None
    pf_employment_types: Optional[str] = "Permanent,Contract"
    pf_probation_days: Optional[int] = 0
    pf_auto_enroll: Optional[bool] = True
    # ESI
    esi_wage_limit: Optional[Decimal] = Decimal("21000.00")
    esi_employee_rate: Optional[float] = 0.75
    esi_employer_rate: Optional[float] = 3.25
    # LWF
    lwf_employee: Optional[Decimal] = Decimal("25.00")
    lwf_employer: Optional[Decimal] = Decimal("75.00")
    # PT
    professional_tax_slab: Optional[str] = None


class StatutoryConfigUpdate(BaseModel):
    pf_wage_limit: Optional[Decimal] = None
    pf_employee_rate: Optional[float] = None
    pf_employer_rate: Optional[float] = None
    eps_rate: Optional[float] = None
    edli_rate: Optional[float] = None
    vpf_enabled: Optional[bool] = None
    default_vpf_rate: Optional[float] = None
    uan_mandatory: Optional[bool] = None
    auto_pf_calculation: Optional[bool] = None
    pf_min_salary: Optional[Decimal] = None
    pf_max_salary: Optional[Decimal] = None
    pf_employment_types: Optional[str] = None
    pf_probation_days: Optional[int] = None
    pf_auto_enroll: Optional[bool] = None
    esi_wage_limit: Optional[Decimal] = None
    esi_employee_rate: Optional[float] = None
    esi_employer_rate: Optional[float] = None
    lwf_employee: Optional[Decimal] = None
    lwf_employer: Optional[Decimal] = None
    professional_tax_slab: Optional[str] = None


class StatutoryConfigResponse(StatutoryConfigBase):
    id: int
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# KPI SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

class ComplianceKPIResponse(BaseModel):
    total_pf_contribution: Decimal
    total_esi_contribution: Decimal
    total_tds_deduction: Decimal
    pending_declarations: int
    slip_month: Optional[int] = None
    slip_year: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# PF STATEMENT
# ─────────────────────────────────────────────────────────────────────────────

class PFStatementResponse(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    uan_number: Optional[str] = None
    slip_month: int
    slip_year: int
    basic_wages: Decimal
    pf_wage: Decimal
    employee_contribution: Decimal
    employer_contribution: Decimal
    eps_contribution: Decimal
    edli_contribution: Decimal
    vpf_amount: Decimal
    total_pf: Decimal
    status: str
    remittance_id: Optional[int] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class PFStatementCalculateRequest(BaseModel):
    slip_month: int
    slip_year: int

    @field_validator("slip_month")
    @classmethod
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("slip_month must be between 1 and 12")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# PF REMITTANCE
# ─────────────────────────────────────────────────────────────────────────────

class PFRemittanceCreate(BaseModel):
    slip_month: int
    slip_year: int
    challan_number: Optional[str] = None
    remittance_date: Optional[date] = None
    remarks: Optional[str] = None

    @field_validator("slip_month")
    @classmethod
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("slip_month must be between 1 and 12")
        return v


class PFRemittanceUpdate(BaseModel):
    challan_number: Optional[str] = None
    remittance_date: Optional[date] = None
    status: Optional[str] = None
    remarks: Optional[str] = None


class PFRemittanceResponse(BaseModel):
    id: int
    slip_month: int
    slip_year: int
    challan_number: Optional[str] = None
    remittance_date: Optional[date] = None
    total_employees: int
    total_contribution: Decimal
    employee_contribution: Decimal
    employer_contribution: Decimal
    eps_contribution: Decimal
    edli_contribution: Decimal
    status: str
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# ECR
# ─────────────────────────────────────────────────────────────────────────────

class ECRGenerateRequest(BaseModel):
    slip_month: int
    slip_year: int

    @field_validator("slip_month")
    @classmethod
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("slip_month must be between 1 and 12")
        return v


class ECRSubmissionResponse(BaseModel):
    id: int
    slip_month: int
    slip_year: int
    total_employees: int
    total_wages: Decimal
    epf_contribution: Decimal
    eps_contribution: Decimal
    edli_contribution: Decimal
    ecr_file_path: Optional[str] = None
    status: str
    submitted_date: Optional[date] = None
    acknowledgement_number: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# VPF
# ─────────────────────────────────────────────────────────────────────────────

class VPFEnrollmentCreate(BaseModel):
    employee_id: int
    vpf_rate: float
    effective_from: date

    @field_validator("vpf_rate")
    @classmethod
    def validate_rate(cls, v):
        if not 0 < v <= 100:
            raise ValueError("vpf_rate must be between 0 and 100")
        return v


class VPFEnrollmentResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    vpf_rate: float
    effective_from: date
    effective_to: Optional[date] = None
    status: str
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# UAN
# ─────────────────────────────────────────────────────────────────────────────

class UANActivationCreate(BaseModel):
    employee_id: int
    uan_number: str
    activation_date: date
    remarks: Optional[str] = None

    @field_validator("uan_number")
    @classmethod
    def validate_uan(cls, v):
        if not v.isdigit() or len(v) != 12:
            raise ValueError("UAN must be exactly 12 digits")
        return v


class UANActivationResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    uan_number: str
    activation_date: date
    status: str
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
