# model/Payroll/statutory_compliance.py
# REPLACE your existing file with this
# Tables:
#   statutory_configs        — PF/ESI/LWF/PT global config  (already exists — extended)
#   pf_statements            — per-employee monthly PF record
#   pf_remittances           — monthly challan/remittance summary
#   ecr_submissions          — Electronic Challan-cum-Return
#   vpf_enrollments          — Voluntary PF per employee
#   uan_activations           — UAN activation records

from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Numeric, Text, ForeignKey, Date, Index
)
from core.database import Base
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# 1. STATUTORY CONFIG  (extended from existing)
# ─────────────────────────────────────────────────────────────────────────────
class StatutoryConfig(Base):
    __tablename__ = "statutory_configs"

    id                      = Column(Integer, primary_key=True, index=True)
    config_name             = Column(String(100), unique=True, default="default")

    # PF
    pf_wage_limit           = Column(Numeric(10, 2), default=15000)
    pf_employee_rate        = Column(Float, default=12.0)
    pf_employer_rate        = Column(Float, default=12.0)
    eps_rate                = Column(Float, default=3.67)   # Employees' Pension Scheme
    edli_rate               = Column(Float, default=0.5)    # Employee Deposit Linked Insurance
    vpf_enabled             = Column(Boolean, default=True)
    default_vpf_rate        = Column(Float, default=0.0)
    uan_mandatory           = Column(Boolean, default=True)
    auto_pf_calculation     = Column(Boolean, default=True)

    # PF eligibility
    pf_min_salary           = Column(Numeric(10, 2), default=0)
    pf_max_salary           = Column(Numeric(10, 2), nullable=True)  # NULL = no limit
    pf_employment_types     = Column(String(200), default="Permanent,Contract")
    pf_probation_days       = Column(Integer, default=0)
    pf_auto_enroll          = Column(Boolean, default=True)

    # ESI
    esi_wage_limit          = Column(Numeric(10, 2), default=21000)
    esi_employee_rate       = Column(Float, default=0.75)
    esi_employer_rate       = Column(Float, default=3.25)

    # LWF
    lwf_employee            = Column(Numeric(10, 2), default=25)
    lwf_employer            = Column(Numeric(10, 2), default=75)

    # PT
    professional_tax_slab   = Column(Text, nullable=True)  # JSON slab per state

    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# 2. PF STATEMENTS  (per-employee monthly)
# ─────────────────────────────────────────────────────────────────────────────
class PFStatement(Base):
    __tablename__ = "pf_statements"

    id                      = Column(Integer, primary_key=True, index=True)
    employee_id             = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    employee_code           = Column(String(50), nullable=False)
    employee_name           = Column(String(255), nullable=False)
    uan_number              = Column(String(20), nullable=True)
    slip_month              = Column(Integer, nullable=False)   # 1-12
    slip_year               = Column(Integer, nullable=False)
    basic_wages             = Column(Numeric(12, 2), nullable=False)
    pf_wage                 = Column(Numeric(12, 2), nullable=False)  # min(basic, wage_limit)
    employee_contribution   = Column(Numeric(12, 2), nullable=False)  # 12%
    employer_contribution   = Column(Numeric(12, 2), nullable=False)  # 12%
    eps_contribution        = Column(Numeric(12, 2), default=0)       # 3.67%
    edli_contribution       = Column(Numeric(12, 2), default=0)       # 0.5%
    vpf_amount              = Column(Numeric(12, 2), default=0)
    total_pf                = Column(Numeric(12, 2), nullable=False)  # emp + er
    status                  = Column(String(20), default="Pending")   # Pending | Paid
    remittance_id           = Column(Integer, ForeignKey("pf_remittances.id"), nullable=True)
    created_at              = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_pf_stmt_emp_period", "employee_id", "slip_month", "slip_year", unique=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. PF REMITTANCES  (monthly challan summary)
# ─────────────────────────────────────────────────────────────────────────────
class PFRemittance(Base):
    __tablename__ = "pf_remittances"

    id                      = Column(Integer, primary_key=True, index=True)
    slip_month              = Column(Integer, nullable=False)
    slip_year               = Column(Integer, nullable=False)
    challan_number          = Column(String(50), nullable=True)
    remittance_date         = Column(Date, nullable=True)
    total_employees         = Column(Integer, default=0)
    total_contribution      = Column(Numeric(12, 2), default=0)
    employee_contribution   = Column(Numeric(12, 2), default=0)
    employer_contribution   = Column(Numeric(12, 2), default=0)
    eps_contribution        = Column(Numeric(12, 2), default=0)
    edli_contribution       = Column(Numeric(12, 2), default=0)
    status                  = Column(String(20), default="Pending")  # Pending | Paid
    remarks                 = Column(Text, nullable=True)
    created_at              = Column(DateTime, default=datetime.utcnow)
    created_by              = Column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_pf_remit_period", "slip_month", "slip_year", unique=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. ECR SUBMISSIONS  (Electronic Challan-cum-Return)
# ─────────────────────────────────────────────────────────────────────────────
class ECRSubmission(Base):
    __tablename__ = "ecr_submissions"

    id                      = Column(Integer, primary_key=True, index=True)
    slip_month              = Column(Integer, nullable=False)
    slip_year               = Column(Integer, nullable=False)
    total_employees         = Column(Integer, default=0)
    total_wages             = Column(Numeric(14, 2), default=0)
    epf_contribution        = Column(Numeric(12, 2), default=0)
    eps_contribution        = Column(Numeric(12, 2), default=0)
    edli_contribution       = Column(Numeric(12, 2), default=0)
    ecr_file_path           = Column(String(500), nullable=True)  # generated txt/csv path
    status                  = Column(String(20), default="Draft")  # Draft | Submitted | Accepted
    submitted_date          = Column(Date, nullable=True)
    acknowledgement_number  = Column(String(100), nullable=True)
    created_at              = Column(DateTime, default=datetime.utcnow)
    created_by              = Column(String(255), nullable=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. VPF ENROLLMENTS  (Voluntary Provident Fund per employee)
# ─────────────────────────────────────────────────────────────────────────────
class VPFEnrollment(Base):
    __tablename__ = "vpf_enrollments"

    id                      = Column(Integer, primary_key=True, index=True)
    employee_id             = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    employee_name           = Column(String(255), nullable=False)
    employee_code           = Column(String(50), nullable=False)
    vpf_rate                = Column(Float, nullable=False)        # % of basic
    effective_from          = Column(Date, nullable=False)
    effective_to            = Column(Date, nullable=True)          # NULL = active
    status                  = Column(String(20), default="Active") # Active | Inactive
    created_at              = Column(DateTime, default=datetime.utcnow)
    created_by              = Column(String(255), nullable=True)


# ─────────────────────────────────────────────────────────────────────────────
# 6. UAN ACTIVATIONS
# ─────────────────────────────────────────────────────────────────────────────
class UANActivation(Base):
    __tablename__ = "uan_activations"

    id                      = Column(Integer, primary_key=True, index=True)
    employee_id             = Column(Integer, ForeignKey("employees.id"), nullable=False, unique=True)
    employee_name           = Column(String(255), nullable=False)
    employee_code           = Column(String(50), nullable=False)
    uan_number              = Column(String(20), nullable=False, unique=True)
    activation_date         = Column(Date, nullable=False)
    status                  = Column(String(20), default="Active")  # Active | Inactive | Transferred
    remarks                 = Column(Text, nullable=True)
    created_at              = Column(DateTime, default=datetime.utcnow)
    created_by              = Column(String(255), nullable=True)
