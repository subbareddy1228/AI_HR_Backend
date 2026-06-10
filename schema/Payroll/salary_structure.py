
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class SalaryStructureBase(BaseModel):
    structure_name: str
    basic_percent: Optional[float] = 40.0
    hra_percent: Optional[float] = 20.0
    special_allowance_percent: Optional[float] = 20.0
    pf_employee_percent: Optional[float] = 12.0
    pf_employer_percent: Optional[float] = 12.0
    esi_employee_percent: Optional[float] = 0.75
    esi_employer_percent: Optional[float] = 3.25
    professional_tax_monthly: Optional[Decimal] = Decimal("200.00")
    tds_percent: Optional[float] = 0.0
    is_active: Optional[bool] = True


class SalaryStructureCreate(SalaryStructureBase):
    pass


class SalaryStructureUpdate(BaseModel):
    structure_name: Optional[str] = None
    basic_percent: Optional[float] = None
    hra_percent: Optional[float] = None
    special_allowance_percent: Optional[float] = None
    pf_employee_percent: Optional[float] = None
    pf_employer_percent: Optional[float] = None
    esi_employee_percent: Optional[float] = None
    esi_employer_percent: Optional[float] = None
    professional_tax_monthly: Optional[Decimal] = None
    tds_percent: Optional[float] = None
    is_active: Optional[bool] = None


class SalaryStructureResponse(SalaryStructureBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeSalaryMappingBase(BaseModel):
    employee_id: int
    salary_structure_id: int
    annual_ctc: Decimal
    effective_from: date


class EmployeeSalaryMappingCreate(EmployeeSalaryMappingBase):
    pass


class EmployeeSalaryMappingUpdate(BaseModel):
    salary_structure_id: Optional[int] = None
    annual_ctc: Optional[Decimal] = None
    effective_from: Optional[date] = None


class EmployeeSalaryMappingResponse(EmployeeSalaryMappingBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
