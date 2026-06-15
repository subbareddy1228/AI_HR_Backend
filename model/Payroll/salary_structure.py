

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Numeric, Date, ForeignKey, Enum, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime
import enum

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
    AUTO = "auto"         
    CUSTOM = "custom"      
    PROMOTION = "promotion"

class SalaryComponent(Base):

    __tablename__ = "salary_components"

    id = Column(Integer, primary_key=True, index=True)

    component_name = Column(String(255), unique=True, nullable=False)
    component_code = Column(String(50), unique=True, nullable=False)   
    description    = Column(Text, nullable=True)

    category       = Column(Enum(ComponentCategory), nullable=False)   
    component_type = Column(Enum(ComponentType), default=ComponentType.FIXED)
    is_taxable      = Column(Boolean, default=True)
    is_statutory    = Column(Boolean, default=False)  

    calculation_method = Column(Enum(CalculationMethod), default=CalculationMethod.PERCENT_OF_CTC)
    value              = Column(Float, nullable=True)   
    base_component_id  = Column(Integer, ForeignKey("salary_components.id"), nullable=True)

    is_pro_rata = Column(Boolean, default=True)
    rounding    = Column(String(50), default="nearest_1")  

    max_amount      = Column(Numeric(12, 2), nullable=True)   
    proof_required  = Column(Boolean, default=False)
    tax_exempt_upto = Column(Numeric(12, 2), nullable=True)

    # Admin
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    base_component = relationship("SalaryComponent", remote_side=[id])

    structure_lines = relationship("StructureComponentLine", back_populates="component")


class SalaryStructureTemplate(Base):

    __tablename__ = "salary_structure_templates"

    id = Column(Integer, primary_key=True, index=True)

    template_name = Column(String(255), nullable=False)
    template_code = Column(String(50), unique=True, nullable=False)  
    description   = Column(Text, nullable=True)

    grade        = Column(String(50), nullable=True)  
    level        = Column(String(50), nullable=True)   
    category     = Column(Enum(StructureCategory), default=StructureCategory.PERMANENT)


    annual_ctc       = Column(Numeric(14, 2), nullable=False)
    take_home_monthly = Column(Numeric(14, 2), nullable=True)  
    employer_cost_monthly = Column(Numeric(14, 2), nullable=True)
    ctc_to_take_home_pct  = Column(Float, nullable=True)       

    status  = Column(Enum(StructureStatus), default=StructureStatus.DRAFT)
    version = Column(String(20), default="v1.0")

   
    department = Column(String(100), nullable=True)   
    locations  = Column(Integer, default=0)           
    depth      = Column(Integer, default=0)          

    employee_count = Column(Integer, default=0)

  
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)


    component_lines = relationship(
        "StructureComponentLine", back_populates="template", cascade="all, delete-orphan"
    )
    assignments = relationship("StructureAssignment", back_populates="template")


class StructureComponentLine(Base):

    __tablename__ = "structure_component_lines"
    __table_args__ = (
        UniqueConstraint("template_id", "component_id", name="uq_template_component"),
    )

    id           = Column(Integer, primary_key=True, index=True)
    template_id  = Column(Integer, ForeignKey("salary_structure_templates.id"), nullable=False)
    component_id = Column(Integer, ForeignKey("salary_components.id"), nullable=False)


    override_value      = Column(Float, nullable=True)
    override_method     = Column(Enum(CalculationMethod), nullable=True)
    override_flat_amount = Column(Numeric(12, 2), nullable=True)

    display_order = Column(Integer, default=0)
    is_active     = Column(Boolean, default=True)

    template  = relationship("SalaryStructureTemplate", back_populates="component_lines")
    component = relationship("SalaryComponent", back_populates="structure_lines")



class StructureAssignment(Base):

    __tablename__ = "structure_assignments"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("salary_structure_templates.id"), nullable=False)


    annual_ctc        = Column(Numeric(14, 2), nullable=False)
    take_home_monthly = Column(Numeric(14, 2), nullable=True)

    allocation_source = Column(Enum(AllocationSource), default=AllocationSource.AUTO)
    is_individual_override = Column(Boolean, default=False)


    effective_from = Column(Date, nullable=False)
    effective_to   = Column(Date, nullable=True)    


    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)


    template = relationship("SalaryStructureTemplate", back_populates="assignments")


class SalaryStructure(Base):

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

    __tablename__ = "employee_salary_mappings"

    id                   = Column(Integer, primary_key=True, index=True)
    employee_id          = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)
    salary_structure_id  = Column(Integer, ForeignKey("salary_structures.id"), nullable=False)
    annual_ctc           = Column(Numeric(12, 2), nullable=False)
    effective_from       = Column(Date, nullable=False)
    created_at           = Column(DateTime, default=datetime.utcnow)