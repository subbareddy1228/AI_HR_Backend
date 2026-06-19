# from pydantic import BaseModel, Field, validator
# from typing import Optional, List
# from datetime import datetime
# from enum import Enum


# class ComponentType(str, Enum):
#     EARNING = "earning"
#     DEDUCTION = "deduction"
#     STATUTORY = "statutory"


# class CalculationType(str, Enum):
#     FIXED = "fixed"
#     PERCENTAGE = "percentage"
#     FORMULA = "formula"


# # ─────────────────────────────────────────────
# # Salary Component Schemas
# # ─────────────────────────────────────────────

# class SalaryComponentBase(BaseModel):
#     name: str = Field(..., max_length=100)
#     code: str = Field(..., max_length=20)
#     component_type: ComponentType
#     calculation_type: CalculationType = CalculationType.FIXED
#     value: float = Field(default=0.0, ge=0)
#     formula: Optional[str] = None
#     depends_on: Optional[str] = None
#     is_taxable: bool = False
#     is_active: bool = True
#     sequence: int = Field(default=1, ge=1)


# class SalaryComponentCreate(SalaryComponentBase):
#     pass


# class SalaryComponentUpdate(BaseModel):
#     name: Optional[str] = Field(None, max_length=100)
#     calculation_type: Optional[CalculationType] = None
#     value: Optional[float] = Field(None, ge=0)
#     formula: Optional[str] = None
#     depends_on: Optional[str] = None
#     is_taxable: Optional[bool] = None
#     is_active: Optional[bool] = None
#     sequence: Optional[int] = Field(None, ge=1)


# class SalaryComponentResponse(SalaryComponentBase):
#     id: int
#     structure_id: int
#     created_at: datetime
#     updated_at: Optional[datetime] = None

#     model_config = {"from_attributes": True}


# # ─────────────────────────────────────────────
# # Salary Structure Schemas
# # ─────────────────────────────────────────────

# class SalaryStructureBase(BaseModel):
#     name: str = Field(..., max_length=100)
#     description: Optional[str] = None
#     is_active: bool = True


# class SalaryStructureCreate(SalaryStructureBase):
#     components: Optional[List[SalaryComponentCreate]] = []


# class SalaryStructureUpdate(BaseModel):
#     name: Optional[str] = Field(None, max_length=100)
#     description: Optional[str] = None
#     is_active: Optional[bool] = None


# class SalaryStructureResponse(SalaryStructureBase):
#     id: int
#     components: List[SalaryComponentResponse] = []
#     created_at: datetime
#     updated_at: Optional[datetime] = None

#     model_config = {"from_attributes": True}


# class SalaryStructureListResponse(SalaryStructureBase):
#     id: int
#     created_at: datetime

#     model_config = {"from_attributes": True}


# # ─────────────────────────────────────────────
# # Employee Salary Structure Schemas
# # ─────────────────────────────────────────────

# class EmployeeSalaryStructureBase(BaseModel):
#     employee_id: int
#     structure_id: int
#     ctc: float = Field(..., gt=0)
#     basic_salary: float = Field(..., gt=0)
#     effective_from: datetime
#     effective_to: Optional[datetime] = None
#     is_active: bool = True

#     @validator("basic_salary")
#     def basic_must_be_less_than_ctc(cls, v, values):
#         if "ctc" in values and v > values["ctc"]:
#             raise ValueError("basic_salary cannot exceed CTC")
#         return v


# class EmployeeSalaryStructureCreate(EmployeeSalaryStructureBase):
#     pass


# class EmployeeSalaryStructureUpdate(BaseModel):
#     ctc: Optional[float] = Field(None, gt=0)
#     basic_salary: Optional[float] = Field(None, gt=0)
#     effective_from: Optional[datetime] = None
#     effective_to: Optional[datetime] = None
#     is_active: Optional[bool] = None


# class EmployeeSalaryStructureResponse(EmployeeSalaryStructureBase):
#     id: int
#     created_at: datetime
#     updated_at: Optional[datetime] = None

#     model_config = {"from_attributes": True}


# # ─────────────────────────────────────────────
# # Salary Breakdown (computed response)
# # ─────────────────────────────────────────────

# class ComponentBreakdown(BaseModel):
#     code: str
#     name: str
#     component_type: ComponentType
#     amount: float
#     is_taxable: bool


# class SalaryBreakdownResponse(BaseModel):
#     employee_id: int
#     structure_name: str
#     ctc: float
#     basic_salary: float
#     gross_earnings: float
#     total_deductions: float
#     net_salary: float
#     components: List[ComponentBreakdown]



# from pydantic import BaseModel, Field, validator
# from typing import Optional, List
# from datetime import datetime
# from enum import Enum


# class ComponentType(str, Enum):
#     EARNING = "earning"
#     DEDUCTION = "deduction"
#     STATUTORY = "statutory"


# class CalculationType(str, Enum):
#     FIXED = "fixed"
#     PERCENTAGE = "percentage"
#     FORMULA = "formula"


# # ─────────────────────────────────────────────
# # Salary Component Schemas
# # ─────────────────────────────────────────────

# class SalaryComponentBase(BaseModel):
#     name: str = Field(..., max_length=100)
#     code: str = Field(..., max_length=20)
#     component_type: ComponentType
#     calculation_type: CalculationType = CalculationType.FIXED
#     value: float = Field(default=0.0, ge=0)
#     formula: Optional[str] = None
#     depends_on: Optional[str] = None
#     is_taxable: bool = False
#     is_active: bool = True
#     sequence: int = Field(default=1, ge=1)


# class SalaryComponentCreate(SalaryComponentBase):
#     pass


# class SalaryComponentUpdate(BaseModel):
#     name: Optional[str] = Field(None, max_length=100)
#     calculation_type: Optional[CalculationType] = None
#     value: Optional[float] = Field(None, ge=0)
#     formula: Optional[str] = None
#     depends_on: Optional[str] = None
#     is_taxable: Optional[bool] = None
#     is_active: Optional[bool] = None
#     sequence: Optional[int] = Field(None, ge=1)


# class SalaryComponentResponse(SalaryComponentBase):
#     id: int
#     structure_id: int
#     created_at: datetime
#     updated_at: Optional[datetime] = None

#     model_config = {"from_attributes": True}


# # ─────────────────────────────────────────────
# # Salary Structure Schemas
# # ─────────────────────────────────────────────

# class SalaryStructureBase(BaseModel):
#     name: str = Field(..., max_length=100)
#     description: Optional[str] = None
#     is_active: bool = True


# class SalaryStructureCreate(SalaryStructureBase):
#     components: Optional[List[SalaryComponentCreate]] = []


# class SalaryStructureUpdate(BaseModel):
#     name: Optional[str] = Field(None, max_length=100)
#     description: Optional[str] = None
#     is_active: Optional[bool] = None


# class SalaryStructureResponse(SalaryStructureBase):
#     id: int
#     components: List[SalaryComponentResponse] = []
#     created_at: datetime
#     updated_at: Optional[datetime] = None

#     model_config = {"from_attributes": True}


# class SalaryStructureListResponse(SalaryStructureBase):
#     id: int
#     created_at: datetime

#     model_config = {"from_attributes": True}


# # ─────────────────────────────────────────────
# # Employee Salary Structure Schemas
# # ─────────────────────────────────────────────

# class EmployeeSalaryStructureBase(BaseModel):
#     employee_id: int
#     structure_id: int
#     ctc: float = Field(..., gt=0)
#     basic_salary: float = Field(..., gt=0)
#     effective_from: datetime
#     effective_to: Optional[datetime] = None
#     is_active: bool = True

#     @validator("basic_salary")
#     def basic_must_be_less_than_ctc(cls, v, values):
#         if "ctc" in values and v > values["ctc"]:
#             raise ValueError("basic_salary cannot exceed CTC")
#         return v


# class EmployeeSalaryStructureCreate(EmployeeSalaryStructureBase):
#     pass


# class EmployeeSalaryStructureUpdate(BaseModel):
#     ctc: Optional[float] = Field(None, gt=0)
#     basic_salary: Optional[float] = Field(None, gt=0)
#     effective_from: Optional[datetime] = None
#     effective_to: Optional[datetime] = None
#     is_active: Optional[bool] = None


# class EmployeeSalaryStructureResponse(EmployeeSalaryStructureBase):
#     id: int
#     created_at: datetime
#     updated_at: Optional[datetime] = None

#     model_config = {"from_attributes": True}


# # ─────────────────────────────────────────────
# # Salary Breakdown (computed response)
# # ─────────────────────────────────────────────

# class ComponentBreakdown(BaseModel):
#     code: str
#     name: str
#     component_type: ComponentType
#     amount: float
#     is_taxable: bool


# class SalaryBreakdownResponse(BaseModel):
#     employee_id: int
#     structure_name: str
#     ctc: float
#     basic_salary: float
#     gross_earnings: float
#     total_deductions: float
#     net_salary: float
#     components: List[ComponentBreakdown]









# schema/Payroll/salary_structure.py
# REPLACE your entire existing file with this. Clean — no commented duplicates.

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ComponentType(str, Enum):
    EARNING = "earning"
    DEDUCTION = "deduction"
    STATUTORY = "statutory"


class CalculationType(str, Enum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    FORMULA = "formula"


# ─────────────────────────────────────────────
# Salary Component Schemas
# ─────────────────────────────────────────────

class SalaryComponentBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    component_type: ComponentType
    calculation_type: CalculationType = CalculationType.FIXED
    value: float = Field(default=0.0, ge=0)
    formula: Optional[str] = None
    depends_on: Optional[str] = None
    is_taxable: bool = False
    is_active: bool = True
    sequence: int = Field(default=1, ge=1)


class SalaryComponentCreate(SalaryComponentBase):
    pass


class SalaryComponentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    calculation_type: Optional[CalculationType] = None
    value: Optional[float] = Field(None, ge=0)
    formula: Optional[str] = None
    depends_on: Optional[str] = None
    is_taxable: Optional[bool] = None
    is_active: Optional[bool] = None
    sequence: Optional[int] = Field(None, ge=1)


class SalaryComponentResponse(SalaryComponentBase):
    id: int
    structure_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Salary Structure Schemas
# ─────────────────────────────────────────────

class SalaryStructureBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_active: bool = True


class SalaryStructureCreate(SalaryStructureBase):
    components: Optional[List[SalaryComponentCreate]] = []


class SalaryStructureUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SalaryStructureResponse(SalaryStructureBase):
    id: int
    components: List[SalaryComponentResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SalaryStructureListResponse(SalaryStructureBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Employee Salary Structure Schemas
# ─────────────────────────────────────────────

class EmployeeSalaryStructureBase(BaseModel):
    employee_id: int
    structure_id: int
    ctc: float = Field(..., gt=0)
    basic_salary: float = Field(..., gt=0)
    effective_from: datetime
    effective_to: Optional[datetime] = None
    is_active: bool = True

    @validator("basic_salary")
    def basic_must_be_less_than_ctc(cls, v, values):
        if "ctc" in values and v > values["ctc"]:
            raise ValueError("basic_salary cannot exceed CTC")
        return v


class EmployeeSalaryStructureCreate(EmployeeSalaryStructureBase):
    pass


class EmployeeSalaryStructureUpdate(BaseModel):
    ctc: Optional[float] = Field(None, gt=0)
    basic_salary: Optional[float] = Field(None, gt=0)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    is_active: Optional[bool] = None


class EmployeeSalaryStructureResponse(EmployeeSalaryStructureBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Salary Breakdown (computed response)
# ─────────────────────────────────────────────

class ComponentBreakdown(BaseModel):
    code: str
    name: str
    component_type: ComponentType
    amount: float
    is_taxable: bool


class SalaryBreakdownResponse(BaseModel):
    employee_id: int
    structure_name: str
    ctc: float
    basic_salary: float
    gross_earnings: float
    total_deductions: float
    net_salary: float
    components: List[ComponentBreakdown]


# ─────────────────────────────────────────────
# KPI Response  ← NEW (was missing)
# Powers the dashboard cards: Total Structures, Active Assignments, Total Components
# ─────────────────────────────────────────────

class SalaryStructureKPIResponse(BaseModel):
    total_structures: int
    active_structures: int
    draft_structures: int
    active_assignments: int
    total_assignments: int
    pending_assignments: int
    total_components: int
    active_components: int
    inactive_components: int
