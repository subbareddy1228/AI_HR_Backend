"""
model/Payroll/salary_structure.py
Updated to match the full Salary Structure Management UI:
  - Components Master  (earnings, deductions, employer contributions, reimbursements)
  - Structure Templates (Grade-based salary templates with version + approval status)
  - Structure Assignment (per-employee CTC assignment with allocation breakdown)
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Numeric, Date, ForeignKey, Enum, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime
import enum


# ─────────────────────────────────────────────
# Enumerations  (mirror the UI badge values)
# ─────────────────────────────────────────────

class ComponentCategory(str, enum.Enum):
    EARNINGS = "earnings"
    DEDUCTIONS = "deductions"
    EMPLOYER_CONTRIBUTION = "employer_contribution"
    REIMBURSEMENT = "reimbursement"


class ComponentType(str, enum.Enum):
    FIXED = "fixed"
    VARIABLE = "variable"


class CalculationMethod(str, enum.Enum):
    PERCENT_OF_CTC = "percent_of_ctc"
    PERCENT_OF_BASE = "percent_of_base"
    PERCENT_OF_GROSS = "percent_of_gross"
    FLAT_AMOUNT = "flat_amount"


class StructureStatus(str, enum.Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    INACTIVE = "inactive"


class StructureCategory(str, enum.Enum):
    PERMANENT = "permanent"
    CONTRACT = "contract"
    INTERN = "intern"


class AllocationSource(str, enum.Enum):
    AUTO = "auto"          # system-computed split
    CUSTOM = "custom"      # HR override
    PROMOTION = "promotion"


# ─────────────────────────────────────────────
# 1. Salary Components Master
# ─────────────────────────────────────────────

class SalaryComponent(Base):
    """
    Single row per payroll component (Basic Salary, HRA, PF, LTA …).
    Covers all four sections shown in the Components Master tab.
    """
    __tablename__ = "salary_components"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    component_name = Column(String(255), unique=True, nullable=False)
    component_code = Column(String(50), unique=True, nullable=False)   # e.g. "BASIC", "HRA"
    description    = Column(Text, nullable=True)

    # Classification
    category       = Column(Enum(ComponentCategory), nullable=False)   # earnings / deductions …
    component_type = Column(Enum(ComponentType), default=ComponentType.FIXED)
    is_taxable      = Column(Boolean, default=True)
    is_statutory    = Column(Boolean, default=False)   # PF, ESI = True

    # Calculation
    calculation_method = Column(Enum(CalculationMethod), default=CalculationMethod.PERCENT_OF_CTC)
    value              = Column(Float, nullable=True)   # % or flat ₹ amount
    base_component_id  = Column(Integer, ForeignKey("salary_components.id"), nullable=True)

    # Pro-rata & rounding
    is_pro_rata = Column(Boolean, default=True)
    rounding    = Column(String(50), default="nearest_1")   # nearest_1 / round_up / round_down

    # Reimbursement extras (visible only when category=REIMBURSEMENT)
    max_amount      = Column(Numeric(12, 2), nullable=True)   # e.g. ₹15,000 medical cap
    proof_required  = Column(Boolean, default=False)
    tax_exempt_upto = Column(Numeric(12, 2), nullable=True)

    # Admin
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Self-referential FK (base component)
    base_component = relationship("SalaryComponent", remote_side=[id])

    # Link to structure templates via association table
    structure_lines = relationship("StructureComponentLine", back_populates="component")


# ─────────────────────────────────────────────
# 2. Salary Structure Templates
# ─────────────────────────────────────────────

class SalaryStructureTemplate(Base):
    """
    A named, grade-based salary template (Grade A – Manager, Grade B – Senior …).
    One template can be assigned to many employees.
    Tracks versioning (v1.0, v1.1 …) and approval workflow.
    """
    __tablename__ = "salary_structure_templates"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    template_name = Column(String(255), nullable=False)
    template_code = Column(String(50), unique=True, nullable=False)  # e.g. "GRADE-A-MGR"
    description   = Column(Text, nullable=True)

    # Grade / level metadata (shown on the card)
    grade        = Column(String(50), nullable=True)   # A / B / C / D / Intern
    level        = Column(String(50), nullable=True)   # L1 / L2 / L3 …
    category     = Column(Enum(StructureCategory), default=StructureCategory.PERMANENT)

    # Financial summary (displayed on template card)
    annual_ctc       = Column(Numeric(14, 2), nullable=False)
    take_home_monthly = Column(Numeric(14, 2), nullable=True)  # computed / stored
    employer_cost_monthly = Column(Numeric(14, 2), nullable=True)
    ctc_to_take_home_pct  = Column(Float, nullable=True)        # e.g. 67.5 %

    # Status & versioning
    status  = Column(Enum(StructureStatus), default=StructureStatus.DRAFT)
    version = Column(String(20), default="v1.0")

    # Scope
    department = Column(String(100), nullable=True)   # null = all departments
    locations  = Column(Integer, default=0)           # count of applicable locations
    depth      = Column(Integer, default=0)           # org depth levels

    employee_count = Column(Integer, default=0)

    # Audit
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Relationships
    component_lines = relationship(
        "StructureComponentLine", back_populates="template", cascade="all, delete-orphan"
    )
    assignments = relationship("StructureAssignment", back_populates="template")


class StructureComponentLine(Base):
    """
    Defines which SalaryComponent appears in a template and at what value/%.
    Allows per-template overrides of the master component defaults.
    """
    __tablename__ = "structure_component_lines"
    __table_args__ = (
        UniqueConstraint("template_id", "component_id", name="uq_template_component"),
    )

    id           = Column(Integer, primary_key=True, index=True)
    template_id  = Column(Integer, ForeignKey("salary_structure_templates.id"), nullable=False)
    component_id = Column(Integer, ForeignKey("salary_components.id"), nullable=False)

    # Override the master component's value for this template
    override_value      = Column(Float, nullable=True)
    override_method     = Column(Enum(CalculationMethod), nullable=True)
    override_flat_amount = Column(Numeric(12, 2), nullable=True)

    display_order = Column(Integer, default=0)
    is_active     = Column(Boolean, default=True)

    template  = relationship("SalaryStructureTemplate", back_populates="component_lines")
    component = relationship("SalaryComponent", back_populates="structure_lines")


# ─────────────────────────────────────────────
# 3. Structure Assignment  (per-employee)
# ─────────────────────────────────────────────

class StructureAssignment(Base):
    """
    Maps an employee to a template + stores their individual CTC,
    take-home, allocation source, and effective date.
    Replaces the old EmployeeSalaryMapping.
    """
    __tablename__ = "structure_assignments"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("salary_structure_templates.id"), nullable=False)

    # CTC breakdown shown in the assignment table
    annual_ctc        = Column(Numeric(14, 2), nullable=False)
    take_home_monthly = Column(Numeric(14, 2), nullable=True)

    # Allocation bar (auto / custom / promotion badge)
    allocation_source = Column(Enum(AllocationSource), default=AllocationSource.AUTO)
    is_individual_override = Column(Boolean, default=False)

    # Dates
    effective_from = Column(Date, nullable=False)
    effective_to   = Column(Date, nullable=True)    # null = current

    # Admin
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Relationships
    template = relationship("SalaryStructureTemplate", back_populates="assignments")


# ─────────────────────────────────────────────
# 4. Legacy model kept for backward-compat
#    (still used by old payroll-run service)
# ─────────────────────────────────────────────

class SalaryStructure(Base):
    """Kept for backward compatibility with the payroll-run service."""
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    structure_name              = Column(String(255), unique=True, nullable=False)
    basic_percent               = Column(Float, default=40.0)
    hra_percent                 = Column(Float, default=20.0)
    special_allowance_percent   = Column(Float, default=20.0)
    pf_employee_percent         = Column(Float, default=12.0)
    pf_employer_percent         = Column(Float, default=12.0)
    esi_employee_percent        = Column(Float, default=0.75)
    esi_employer_percent        = Column(Float, default=3.25)
    professional_tax_monthly    = Column(Numeric(10, 2), default=200)
    tds_percent                 = Column(Float, default=0.0)
    is_active                   = Column(Boolean, default=True)
    created_at                  = Column(DateTime, default=datetime.utcnow)


class EmployeeSalaryMapping(Base):
    """Kept for backward compatibility."""
    __tablename__ = "employee_salary_mappings"

    id                   = Column(Integer, primary_key=True, index=True)
    employee_id          = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)
    salary_structure_id  = Column(Integer, ForeignKey("salary_structures.id"), nullable=False)
    annual_ctc           = Column(Numeric(12, 2), nullable=False)
    effective_from       = Column(Date, nullable=False)
    created_at           = Column(DateTime, default=datetime.utcnow)