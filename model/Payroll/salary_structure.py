# FILE 1 of 18 | model/Payroll/salary_structure.py
# Models: SalaryStructure, EmployeeSalaryMapping
# Tables: salary_structures, employee_salary_mappings

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Numeric, Date, ForeignKey
from core.database import Base
from datetime import datetime


class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    structure_name = Column(String(255), unique=True, nullable=False)
    basic_percent = Column(Float, default=40.0)
    hra_percent = Column(Float, default=20.0)
    special_allowance_percent = Column(Float, default=20.0)
    pf_employee_percent = Column(Float, default=12.0)
    pf_employer_percent = Column(Float, default=12.0)
    esi_employee_percent = Column(Float, default=0.75)
    esi_employer_percent = Column(Float, default=3.25)
    professional_tax_monthly = Column(Numeric(10, 2), default=200)
    tds_percent = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmployeeSalaryMapping(Base):
    __tablename__ = "employee_salary_mappings"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)
    salary_structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=False)
    annual_ctc = Column(Numeric(12, 2), nullable=False)
    effective_from = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
