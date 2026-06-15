"""
schema/Payroll/salary_structure.py
Pydantic v2 schemas matching the updated model.
"""

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


# ─── Enums (mirrors model) ───────────────────

class ComponentCategory(str, Enum):
    EARNINGS = "earnings"
    DEDUCTIONS = "deductions"
    EMPLOYER_CONTRIBUTION = "employer_contribution"
    REIMBURSEMENT = "reimbursement"


class ComponentType(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"


class CalculationMethod(str, Enum):
    PERCENT_OF_CTC   = "percent_of_ctc"
    PERCENT_OF_BASE  = "percent_of_base"
    PERCENT_OF_GROSS = "percent_of_gross"
    FLAT_AMOUNT      = "flat_amount"


class StructureStatus(str, Enum):
    ACTIVE   = "active"
    DRAFT    = "draft"
    INACTIVE = "inactive"


class StructureCategory(str, Enum):
    PERMANENT = "permanent"
    CONTRACT  = "contract"
    INTERN    = "intern"


class AllocationSource(str, Enum):
    AUTO      = "auto"
    CUSTOM    = "custom"
    PROMOTION = "promotion"


# ─────────────────────────────────────────────
# 1. Salary Component schemas
# ─────────────────────────────────────────────

class SalaryComponentBase(BaseModel):
    component_name:     str
    component_code:     str
    description:        Optional[str] = None
    category:           ComponentCategory
    component_type:     ComponentType = ComponentType.FIXED
    is_taxable:         bool = True
    is_statutory:       bool = False
    calculation_method: CalculationMethod = CalculationMethod.PERCENT_OF_CTC
    value:              Optional[float] = None
    base_component_id:  Optional[int] = None
    is_pro_rata:        bool = True
    rounding:           str = "nearest_1"
    # Reimbursement extras
    max_amount:      Optional[Decimal] = None
    proof_required:  bool = False
    tax_exempt_upto: Optional[Decimal] = None
    is_active:       bool = True


class SalaryComponentCreate(SalaryComponentBase):
    pass


class SalaryComponentUpdate(BaseModel):
    component_name:     Optional[str] = None
    description:        Optional[str] = None
    component_type:     Optional[ComponentType] = None
    is_taxable:         Optional[bool] = None
    is_statutory:       Optional[bool] = None
    calculation_method: Optional[CalculationMethod] = None
    value:              Optional[float] = None
    base_component_id:  Optional[int] = None
    is_pro_rata:        Optional[bool] = None
    rounding:           Optional[str] = None
    max_amount:         Optional[Decimal] = None
    proof_required:     Optional[bool] = None
    tax_exempt_upto:    Optional[Decimal] = None
    is_active:          Optional[bool] = None


class SalaryComponentResponse(SalaryComponentBase):
    id:         int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Grouped response for the Components Master tab
class ComponentsMasterResponse(BaseModel):
    earnings:               List[SalaryComponentResponse]
    deductions:             List[SalaryComponentResponse]
    employer_contributions: List[SalaryComponentResponse]
    reimbursements:         List[SalaryComponentResponse]

    # Stats shown at the top
    total_components:    int
    active_components:   int
    taxable_components:  int
    statutory_components: int
    fixed_components:    int
    variable_components: int


# ─────────────────────────────────────────────
# 2. Structure Component Line schemas
# ─────────────────────────────────────────────

class StructureComponentLineBase(BaseModel):
    component_id:         int
    override_value:       Optional[float] = None
    override_method:      Optional[CalculationMethod] = None
    override_flat_amount: Optional[Decimal] = None
    display_order:        int = 0
    is_active:            bool = True


class StructureComponentLineCreate(StructureComponentLineBase):
    pass


class StructureComponentLineResponse(StructureComponentLineBase):
    id:           int
    template_id:  int
    component:    Optional[SalaryComponentResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────
# 3. Salary Structure Template schemas
# ─────────────────────────────────────────────

class SalaryStructureTemplateBase(BaseModel):
    template_name:  str
    template_code:  str
    description:    Optional[str] = None
    grade:          Optional[str] = None
    level:          Optional[str] = None
    category:       StructureCategory = StructureCategory.PERMANENT
    annual_ctc:     Decimal
    take_home_monthly:     Optional[Decimal] = None
    employer_cost_monthly: Optional[Decimal] = None
    ctc_to_take_home_pct:  Optional[float] = None
    status:         StructureStatus = StructureStatus.DRAFT
    version:        str = "v1.0"
    department:     Optional[str] = None
    locations:      int = 0
    depth:          int = 0
    employee_count: int = 0


class SalaryStructureTemplateCreate(SalaryStructureTemplateBase):
    component_lines: List[StructureComponentLineCreate] = []


class SalaryStructureTemplateUpdate(BaseModel):
    template_name:  Optional[str] = None
    description:    Optional[str] = None
    grade:          Optional[str] = None
    level:          Optional[str] = None
    category:       Optional[StructureCategory] = None
    annual_ctc:     Optional[Decimal] = None
    take_home_monthly:     Optional[Decimal] = None
    employer_cost_monthly: Optional[Decimal] = None
    ctc_to_take_home_pct:  Optional[float] = None
    status:         Optional[StructureStatus] = None
    version:        Optional[str] = None
    department:     Optional[str] = None
    locations:      Optional[int] = None
    depth:          Optional[int] = None


class SalaryStructureTemplateResponse(SalaryStructureTemplateBase):
    id:           int
    component_lines: List[StructureComponentLineResponse] = []
    created_at:   Optional[datetime] = None
    updated_at:   Optional[datetime] = None
    approved_at:  Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Grouped response for the Structure Templates tab
class StructureTemplatesOverview(BaseModel):
    total_structures:   int
    active_structures:  int
    draft_structures:   int
    inactive_structures: int
    templates:          List[SalaryStructureTemplateResponse]


# ─────────────────────────────────────────────
# 4. Structure Assignment schemas
# ─────────────────────────────────────────────

class StructureAssignmentBase(BaseModel):
    employee_id:       int
    template_id:       int
    annual_ctc:        Decimal
    take_home_monthly: Optional[Decimal] = None
    allocation_source: AllocationSource = AllocationSource.AUTO
    is_individual_override: bool = False
    effective_from:    date
    effective_to:      Optional[date] = None


class StructureAssignmentCreate(StructureAssignmentBase):
    pass


class StructureAssignmentUpdate(BaseModel):
    template_id:            Optional[int] = None
    annual_ctc:             Optional[Decimal] = None
    take_home_monthly:      Optional[Decimal] = None
    allocation_source:      Optional[AllocationSource] = None
    is_individual_override: Optional[bool] = None
    effective_from:         Optional[date] = None
    effective_to:           Optional[date] = None


class StructureAssignmentResponse(StructureAssignmentBase):
    id:         int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Detailed response joining employee + template info (for the Assignment table)
class StructureAssignmentDetail(BaseModel):
    id:              int
    employee_id:     int
    employee_code:   str
    employee_name:   str
    department:      Optional[str] = None
    grade:           Optional[str] = None
    template_id:     int
    template_name:   str
    annual_ctc:      Decimal
    take_home_monthly: Optional[Decimal] = None
    allocation_source:      AllocationSource
    is_individual_override: bool
    effective_from:  date
    created_at:      Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Dashboard stats shown at top of Salary Structure Management page
class SalaryStructureDashboard(BaseModel):
    total_structures:   int
    active_structures:  int
    draft_structures:   int
    active_assignments: int
    total_assignments:  int
    pending_assignments: int
    total_components:   int
    active_components:  int
    inactive_components: int


# ─────────────────────────────────────────────
# 5. Legacy schemas (backward-compat)
# ─────────────────────────────────────────────

class SalaryStructureBase(BaseModel):
    structure_name:             str
    basic_percent:              Optional[float] = 40.0
    hra_percent:                Optional[float] = 20.0
    special_allowance_percent:  Optional[float] = 20.0
    pf_employee_percent:        Optional[float] = 12.0
    pf_employer_percent:        Optional[float] = 12.0
    esi_employee_percent:       Optional[float] = 0.75
    esi_employer_percent:       Optional[float] = 3.25
    professional_tax_monthly:   Optional[Decimal] = Decimal("200.00")
    tds_percent:                Optional[float] = 0.0
    is_active:                  Optional[bool] = True


class SalaryStructureCreate(SalaryStructureBase):
    pass


class SalaryStructureUpdate(BaseModel):
    structure_name:            Optional[str] = None
    basic_percent:             Optional[float] = None
    hra_percent:               Optional[float] = None
    special_allowance_percent: Optional[float] = None
    pf_employee_percent:       Optional[float] = None
    pf_employer_percent:       Optional[float] = None
    esi_employee_percent:      Optional[float] = None
    esi_employer_percent:      Optional[float] = None
    professional_tax_monthly:  Optional[Decimal] = None
    tds_percent:               Optional[float] = None
    is_active:                 Optional[bool] = None


class SalaryStructureResponse(SalaryStructureBase):
    id:         int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeSalaryMappingBase(BaseModel):
    employee_id:         int
    salary_structure_id: int
    annual_ctc:          Decimal
    effective_from:      date


class EmployeeSalaryMappingCreate(EmployeeSalaryMappingBase):
    pass


class EmployeeSalaryMappingUpdate(BaseModel):
    salary_structure_id: Optional[int] = None
    annual_ctc:          Optional[Decimal] = None
    effective_from:      Optional[date] = None


class EmployeeSalaryMappingResponse(EmployeeSalaryMappingBase):
    id:         int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)