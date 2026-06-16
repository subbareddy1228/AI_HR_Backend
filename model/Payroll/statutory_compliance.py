"""
model/Payroll/statutory_compliance.py

Updated to cover every section of the Statutory Compliance Engine page:

  StatutoryConfig          → PF Configuration panel (rates, wage limits, EPS, EPS settings)
  PFEligibilityRule        → PF Eligibility Rules (min/max salary, employment types, probation)
  PFStatement              → PF Statements table (per employee per month)
  PFRemittanceSummary      → PF Remittance Summary table (monthly challan rows)
  ECRRecord                → ECR (Electronic Challan-cum-Return) table
  VPFRecord                → VPF (Voluntary Provident Fund) Management table
  UANRecord                → UAN Activation & Management table

All legacy fields from the original StatutoryConfig are kept intact.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Numeric,
    Text, ForeignKey, Float, Enum, Date, UniqueConstraint
)
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime
import enum


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class PFStatementStatus(str, enum.Enum):
    PAID      = "paid"
    PENDING   = "pending"
    FAILED    = "failed"


class RemittanceStatus(str, enum.Enum):
    PAID    = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"


class ECRStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    PENDING   = "pending"
    FAILED    = "failed"


class VPFStatus(str, enum.Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    PAUSED   = "paused"


class UANStatus(str, enum.Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    PENDING  = "pending"


# ─────────────────────────────────────────────
# 1. Statutory / PF Configuration  (updated)
# ─────────────────────────────────────────────

class StatutoryConfig(Base):
    """
    Global statutory configuration row.
    Extends the existing table with PF Settings panel fields
    (Ceiling Limit, checkboxes, Default VPF Rate).
    Original columns are preserved unchanged.
    """
    __tablename__ = "statutory_configs"

    id          = Column(Integer, primary_key=True, index=True)
    config_name = Column(String(100), unique=True, default="default")

    # ── Original fields (unchanged) ────────────
    pf_wage_limit       = Column(Numeric(10, 2), default=15000)
    esi_wage_limit      = Column(Numeric(10, 2), default=21000)
    pf_employee_rate    = Column(Float, default=12.0)
    pf_employer_rate    = Column(Float, default=12.0)
    esi_employee_rate   = Column(Float, default=0.75)
    esi_employer_rate   = Column(Float, default=3.25)
    lwf_employee        = Column(Numeric(10, 2), default=25)
    lwf_employer        = Column(Numeric(10, 2), default=75)
    professional_tax_slab = Column(Text, nullable=True)   # JSON slab

    # ── EPS (Employee Pension Scheme) ──────────
    eps_contribution_rate = Column(Float, default=8.33)  # % of basic; shown as "EPS Contribution" in UI
    edli_contribution_rate = Column(Float, default=0.5)  # EDLI employer rate

    # ── PF Settings panel ──────────────────────
    # Ceiling Limit (₹15,000 shown in screenshot)
    pf_ceiling_limit    = Column(Numeric(10, 2), default=15000)
    # Checkbox: "PF contribution calculated on basic up to this limit"
    pf_calc_on_ceiling       = Column(Boolean, default=True)
    # Checkbox: "Basic PF Calculation"
    enable_basic_pf_calc     = Column(Boolean, default=True)
    # Checkbox: "EDLI Employer Allocation"
    enable_edli_allocation   = Column(Boolean, default=True)
    # Checkbox: "Enable VPF (Voluntary Provident Fund)"
    enable_vpf               = Column(Boolean, default=True)

    # Default VPF Rate (%)
    default_vpf_rate    = Column(Float, default=0.0)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    eligibility_rules = relationship(
        "PFEligibilityRule", back_populates="config", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────
# 2. PF Eligibility Rules
# ─────────────────────────────────────────────

class PFEligibilityRule(Base):
    """
    PF Eligibility Rules panel:
      - Minimum / Maximum Salary
      - Employment Types (checkboxes: Permanent, Contract)
      - Probation Period
      - Auto-enroll toggle
    """
    __tablename__ = "pf_eligibility_rules"

    id        = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("statutory_configs.id"), nullable=False)

    # Salary range
    minimum_salary = Column(Numeric(10, 2), nullable=True)   # blank = no minimum
    maximum_salary = Column(Numeric(10, 2), nullable=True)   # blank = no maximum

    # Employment Types (checkboxes – stored as booleans)
    allow_permanent = Column(Boolean, default=True)
    allow_contract  = Column(Boolean, default=True)
    allow_intern    = Column(Boolean, default=False)
    allow_part_time = Column(Boolean, default=False)

    # Probation Period (days; 0 = no restriction)
    probation_period_days = Column(Integer, default=0)

    # Auto-enroll all eligible employees
    auto_enroll_eligible = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    config = relationship("StatutoryConfig", back_populates="eligibility_rules")


# ─────────────────────────────────────────────
# 3. PF Statements  (per employee per month)
# ─────────────────────────────────────────────

class PFStatement(Base):
    """
    PF Statements table rows visible in screenshot:
      Employee ID | Employee Name | Employee Contribution |
      Employer Contribution | Total PF | UAN Number | Status | Actions
    """
    __tablename__ = "pf_statements"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month       = Column(Integer, nullable=False)   # 1-12
    year        = Column(Integer, nullable=False)

    # UAN
    uan_number  = Column(String(20), nullable=True)

    # Contribution amounts
    employee_contribution = Column(Numeric(10, 2), default=0)
    employer_contribution = Column(Numeric(10, 2), default=0)
    eps_contribution      = Column(Numeric(10, 2), default=0)
    edli_contribution     = Column(Numeric(10, 2), default=0)
    total_pf              = Column(Numeric(10, 2), default=0)   # employee + employer

    # VPF (if opted)
    vpf_contribution = Column(Numeric(10, 2), default=0)

    status     = Column(Enum(PFStatementStatus), default=PFStatementStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("employee_id", "month", "year", name="uq_pf_statement_emp_month"),
    )


# ─────────────────────────────────────────────
# 4. PF Remittance Summary  (monthly challan)
# ─────────────────────────────────────────────

class PFRemittanceSummary(Base):
    """
    PF Remittance Summary table:
      Month | Total Contribution | Employee Contribution |
      Employer Contribution | Challan Number | Remittance Date | Status | Actions
    """
    __tablename__ = "pf_remittance_summaries"

    id    = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, nullable=False)
    year  = Column(Integer, nullable=False)

    total_contribution    = Column(Numeric(12, 2), default=0)
    employee_contribution = Column(Numeric(12, 2), default=0)
    employer_contribution = Column(Numeric(12, 2), default=0)
    eps_contribution      = Column(Numeric(12, 2), default=0)
    edli_contribution     = Column(Numeric(12, 2), default=0)

    challan_number    = Column(String(50), nullable=True)   # e.g. CH-0861
    remittance_date   = Column(Date, nullable=True)
    due_date          = Column(Date, nullable=True)

    status     = Column(Enum(RemittanceStatus), default=RemittanceStatus.PENDING)
    remarks    = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("month", "year", name="uq_remittance_month_year"),
    )


# ─────────────────────────────────────────────
# 5. ECR – Electronic Challan-cum-Return
# ─────────────────────────────────────────────

class ECRRecord(Base):
    """
    ECR table visible in screenshot:
      Month | Total Employees | Total Wages | EPF Contribution |
      EPS Contribution | EDLI Contribution | Status | Submitted Date | Actions
    """
    __tablename__ = "ecr_records"

    id    = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, nullable=False)
    year  = Column(Integer, nullable=False)

    total_employees    = Column(Integer, default=0)
    total_wages        = Column(Numeric(14, 2), default=0)
    epf_contribution   = Column(Numeric(12, 2), default=0)
    eps_contribution   = Column(Numeric(12, 2), default=0)
    edli_contribution  = Column(Numeric(12, 2), default=0)
    admin_charges      = Column(Numeric(12, 2), default=0)
    total_amount_due   = Column(Numeric(12, 2), default=0)

    status         = Column(Enum(ECRStatus), default=ECRStatus.PENDING)
    submitted_date = Column(Date, nullable=True)
    ack_number     = Column(String(100), nullable=True)   # EPFO acknowledgement

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("month", "year", name="uq_ecr_month_year"),
    )


# ─────────────────────────────────────────────
# 6. VPF – Voluntary Provident Fund
# ─────────────────────────────────────────────

class VPFRecord(Base):
    """
    VPF Management table:
      Employee | VPF Rate (%) | VPF Amount | Month | Status | Actions
    """
    __tablename__ = "vpf_records"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month       = Column(Integer, nullable=False)
    year        = Column(Integer, nullable=False)

    vpf_rate   = Column(Float, default=0.0)          # % of basic
    vpf_amount = Column(Numeric(10, 2), default=0)   # computed ₹ amount

    status     = Column(Enum(VPFStatus), default=VPFStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("employee_id", "month", "year", name="uq_vpf_emp_month"),
    )


# ─────────────────────────────────────────────
# 7. UAN Activation & Management
# ─────────────────────────────────────────────

class UANRecord(Base):
    """
    UAN Activation & Management table:
      Employee | UAN Number | Activation Date | Status | Actions
    """
    __tablename__ = "uan_records"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, unique=True)

    uan_number      = Column(String(20), unique=True, nullable=True)
    activation_date = Column(Date, nullable=True)
    linked_pf_account = Column(String(30), nullable=True)
    kyc_verified    = Column(Boolean, default=False)

    status     = Column(Enum(UANStatus), default=UANStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)