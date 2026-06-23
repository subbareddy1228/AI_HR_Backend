
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Numeric,
    Text, ForeignKey, Float, Enum, Date, UniqueConstraint
)
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime
import enum


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


class StatutoryConfig(Base):

    __tablename__ = "statutory_configs"

    id          = Column(Integer, primary_key=True, index=True)
    config_name = Column(String(100), unique=True, default="default")
    pf_wage_limit       = Column(Numeric(10, 2), default=15000)
    esi_wage_limit      = Column(Numeric(10, 2), default=21000)
    pf_employee_rate    = Column(Float, default=12.0)
    pf_employer_rate    = Column(Float, default=12.0)
    esi_employee_rate   = Column(Float, default=0.75)
    esi_employer_rate   = Column(Float, default=3.25)
    lwf_employee        = Column(Numeric(10, 2), default=25)
    lwf_employer        = Column(Numeric(10, 2), default=75)
    professional_tax_slab = Column(Text, nullable=True)  
    eps_contribution_rate = Column(Float, default=8.33) 
    edli_contribution_rate = Column(Float, default=0.5)  
    pf_ceiling_limit    = Column(Numeric(10, 2), default=15000)
    pf_calc_on_ceiling       = Column(Boolean, default=True)
    enable_basic_pf_calc     = Column(Boolean, default=True)
    enable_edli_allocation   = Column(Boolean, default=True)
    enable_vpf               = Column(Boolean, default=True)
    default_vpf_rate    = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    eligibility_rules = relationship(
        "PFEligibilityRule", back_populates="config", cascade="all, delete-orphan"
    )

class PFEligibilityRule(Base):

    __tablename__ = "pf_eligibility_rules"

    id        = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("statutory_configs.id"), nullable=False)

    minimum_salary = Column(Numeric(10, 2), nullable=True)   
    maximum_salary = Column(Numeric(10, 2), nullable=True)   

    allow_permanent = Column(Boolean, default=True)
    allow_contract  = Column(Boolean, default=True)
    allow_intern    = Column(Boolean, default=False)
    allow_part_time = Column(Boolean, default=False)
    probation_period_days = Column(Integer, default=0)
    auto_enroll_eligible = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    config = relationship("StatutoryConfig", back_populates="eligibility_rules")

class PFStatement(Base):

    __tablename__ = "pf_statements"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month       = Column(Integer, nullable=False)   # 1-12
    year        = Column(Integer, nullable=False)

    uan_number  = Column(String(20), nullable=True)

    employee_contribution = Column(Numeric(10, 2), default=0)
    employer_contribution = Column(Numeric(10, 2), default=0)
    eps_contribution      = Column(Numeric(10, 2), default=0)
    edli_contribution     = Column(Numeric(10, 2), default=0)
    total_pf              = Column(Numeric(10, 2), default=0)   

    vpf_contribution = Column(Numeric(10, 2), default=0)

    status     = Column(Enum(PFStatementStatus), default=PFStatementStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("employee_id", "month", "year", name="uq_pf_statement_emp_month"),
    )

class PFRemittanceSummary(Base):

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

class ECRRecord(Base):

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


class VPFRecord(Base):

    __tablename__ = "vpf_records"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month       = Column(Integer, nullable=False)
    year        = Column(Integer, nullable=False)

    vpf_rate   = Column(Float, default=0.0)          
    vpf_amount = Column(Numeric(10, 2), default=0)   

    status     = Column(Enum(VPFStatus), default=VPFStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("employee_id", "month", "year", name="uq_vpf_emp_month"),
    )


class UANRecord(Base):

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