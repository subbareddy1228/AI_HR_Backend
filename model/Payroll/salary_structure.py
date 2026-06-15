from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from core.database import Base


class ComponentType(str, enum.Enum):
    EARNING = "earning"
    DEDUCTION = "deduction"
    STATUTORY = "statutory"


class CalculationType(str, enum.Enum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    FORMULA = "formula"


class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    components = relationship("SalaryComponent", back_populates="structure", cascade="all, delete-orphan")
    employee_assignments = relationship("EmployeeSalaryStructure", back_populates="structure")


class SalaryComponent(Base):
    __tablename__ = "salary_components"

    id = Column(Integer, primary_key=True, index=True)
    structure_id = Column(Integer, ForeignKey("salary_structures.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)  # e.g., BASIC, HRA, PF
    component_type = Column(Enum(ComponentType), nullable=False)
    calculation_type = Column(Enum(CalculationType), nullable=False, default=CalculationType.FIXED)
    value = Column(Float, nullable=False, default=0.0)  # Fixed amount or percentage
    formula = Column(Text, nullable=True)  # e.g., "BASIC * 0.4"
    depends_on = Column(String(50), nullable=True)  # component code it's based on
    is_taxable = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sequence = Column(Integer, default=1)  # order of calculation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    structure = relationship("SalaryStructure", back_populates="components")


class EmployeeSalaryStructure(Base):
    __tablename__ = "employee_salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    structure_id = Column(Integer, ForeignKey("salary_structures.id", ondelete="CASCADE"), nullable=False)
    ctc = Column(Float, nullable=False)  # Cost to Company
    basic_salary = Column(Float, nullable=False)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    structure = relationship("SalaryStructure", back_populates="employee_assignments")


# Alias for backward compatibility
EmployeeSalaryMapping = EmployeeSalaryStructure
