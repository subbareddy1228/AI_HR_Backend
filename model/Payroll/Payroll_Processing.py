
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from core.database import Base


class CycleType(str, enum.Enum):
    MONTHLY     = "monthly"
    BI_WEEKLY   = "bi_weekly"
    WEEKLY      = "weekly"
    SEMI_MONTHLY = "semi_monthly"


class PayPeriod(str, enum.Enum):
    STANDARD_MONTH   = "standard_month"      
    CUSTOM_DATE_RANGE = "custom_date_range"  
    CALENDAR_MONTH   = "calendar_month"


class PayrollStatus(str, enum.Enum):
    ACTIVE = "active"
    LOCKED = "locked"


class ComponentType(str, enum.Enum):
    EARNINGS   = "earnings"
    DEDUCTIONS = "deductions"


class CalculationMethod(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED      = "fixed"


class LockAction(str, enum.Enum):
    LOCK   = "lock"
    UNLOCK = "unlock"


class PayrollConfig(Base):

    __tablename__ = "payroll_config"

    id = Column(Integer, primary_key=True, index=True)

    cycle_type  = Column(Enum(CycleType),  nullable=False, default=CycleType.MONTHLY)
    pay_period  = Column(Enum(PayPeriod),  nullable=False, default=PayPeriod.STANDARD_MONTH)

    period_start_day = Column(Integer, nullable=True)  
    period_end_day   = Column(Integer, nullable=True)   

    processing_day = Column(Integer, nullable=False, default=25)   
    payment_day    = Column(Integer, nullable=False, default=30) 

    enable_off_cycle_payroll        = Column(Boolean, default=True,  nullable=False)
    enable_advance_payroll_scheduling = Column(Boolean, default=False, nullable=False)

    payroll_status   = Column(Enum(PayrollStatus), nullable=False,
                              default=PayrollStatus.ACTIVE)
    locked_by        = Column(Integer, ForeignKey("employees.id"), nullable=True)
    locked_at        = Column(DateTime, nullable=True)
    lock_reason      = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    def __repr__(self) -> str:
        return f"<PayrollConfig id={self.id} status={self.payroll_status} cycle={self.cycle_type}>"


class CommissionConfig(Base):
 
    __tablename__ = "commission_config"

    id = Column(Integer, primary_key=True, index=True)

    enable_commission_calculation = Column(Boolean, default=False, nullable=False)
    commission_rate_percent        = Column(Float, nullable=True, default=5.0)   # e.g. 5 → 5 %
    bonus_threshold                = Column(Numeric(14, 2), nullable=True,
                                            default=100000)                       # in company currency

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    def __repr__(self) -> str:
        return (f"<CommissionConfig enabled={self.enable_commission_calculation} "
                f"rate={self.commission_rate_percent}%>")


class StatutorySettings(Base):

    __tablename__ = "statutory_settings"

    id = Column(Integer, primary_key=True, index=True)

    enable_tax_calculation = Column(Boolean, default=True,  nullable=False)
    enable_epf_contribution = Column(Boolean, default=True,  nullable=False)
    enable_esi_contribution  = Column(Boolean, default=True,  nullable=False)
    enable_tds_deduction     = Column(Boolean, default=True,  nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    def __repr__(self) -> str:
        return (f"<StatutorySettings tax={self.enable_tax_calculation} "
                f"epf={self.enable_epf_contribution} "
                f"esi={self.enable_esi_contribution} "
                f"tds={self.enable_tds_deduction}>")


class PayrollComponent(Base):

    __tablename__ = "payroll_components"

    id             = Column(Integer, primary_key=True, index=True)
    component_name = Column(String(255), nullable=False)
    component_type = Column(Enum(ComponentType), nullable=False,
                            default=ComponentType.EARNINGS, index=True)

    calculation_method = Column(Enum(CalculationMethod), nullable=False,
                                default=CalculationMethod.PERCENTAGE)

   
    value     = Column(Float, nullable=False, default=0.0)
    is_taxable = Column(Boolean, default=False, nullable=False)

    display_order = Column(Integer, default=0)

    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    __table_args__ = (
        Index("ix_payroll_components_type_active", "component_type", "is_active"),
    )

    def __repr__(self) -> str:
        return (f"<PayrollComponent {self.component_name} "
                f"| {self.component_type} | {self.calculation_method} | {self.value}>")


class PayrollLockLog(Base):

    __tablename__ = "payroll_lock_logs"

    id         = Column(Integer, primary_key=True, index=True)
    action     = Column(Enum(LockAction), nullable=False)
    reason     = Column(String(500), nullable=True)
    actioned_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    actioned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    previous_status = Column(String(50), nullable=False)
    new_status      = Column(String(50), nullable=False)

    __table_args__ = (
        Index("ix_pll_actioned_at", "actioned_at"),
        Index("ix_pll_action", "action"),
    )

    def __repr__(self) -> str:
        return f"<PayrollLockLog {self.action} at={self.actioned_at}>"