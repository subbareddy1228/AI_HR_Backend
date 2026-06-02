# FILE 9 (6/8) | schema/Payroll/statutory_compliance.py
# Schemas: StatutoryConfigBase/Create/Update/Response

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal


class StatutoryConfigBase(BaseModel):
    config_name: Optional[str] = "default"
    pf_wage_limit: Optional[Decimal] = Decimal("15000.00")
    esi_wage_limit: Optional[Decimal] = Decimal("21000.00")
    pf_employee_rate: Optional[float] = 12.0
    pf_employer_rate: Optional[float] = 12.0
    esi_employee_rate: Optional[float] = 0.75
    esi_employer_rate: Optional[float] = 3.25
    lwf_employee: Optional[Decimal] = Decimal("25.00")
    lwf_employer: Optional[Decimal] = Decimal("75.00")
    professional_tax_slab: Optional[str] = None


class StatutoryConfigCreate(StatutoryConfigBase):
    pass


class StatutoryConfigUpdate(BaseModel):
    pf_wage_limit: Optional[Decimal] = None
    esi_wage_limit: Optional[Decimal] = None
    pf_employee_rate: Optional[float] = None
    pf_employer_rate: Optional[float] = None
    esi_employee_rate: Optional[float] = None
    esi_employer_rate: Optional[float] = None
    lwf_employee: Optional[Decimal] = None
    lwf_employer: Optional[Decimal] = None
    professional_tax_slab: Optional[str] = None


class StatutoryConfigResponse(StatutoryConfigBase):
    id: int
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
