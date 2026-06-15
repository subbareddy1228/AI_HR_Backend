"""
Payroll Processing Module — Model Layer
Covers every section on the Payroll Processing configuration page:

  1. PayrollConfig          — singleton company-level config (cycle, schedule, lock state)
  2. CommissionConfig       — Sales/Commission Configuration section
  3. StatutorySettings      — Statutory Compliance Settings section
  4. PayrollComponent       — Salary Component Configuration table
  5. PayrollLockLog         — Audit trail for every lock / unlock action
"""

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


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CycleType(str, enum.Enum):
    MONTHLY     = "monthly"
    BI_WEEKLY   = "bi_weekly"
    WEEKLY      = "weekly"
    SEMI_MONTHLY = "semi_monthly"


class PayPeriod(str, enum.Enum):
    STANDARD_MONTH   = "standard_month"      # 1st – last day
    CUSTOM_DATE_RANGE = "custom_date_range"  # e.g. 26th prev – 25th current
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


# ---------------------------------------------------------------------------
# 1. Payroll Cycle Configuration  (one row per company — upsert pattern)
# ---------------------------------------------------------------------------

class PayrollConfig(Base):
    """
    Singleton configuration that controls the overall payroll processing cycle.
    Sections:  Payroll Cycle Settings + Payroll Schedule + status banner.
    """
    __tablename__ = "payroll_config"

    id = Column(Integer, primary_key=True, index=True)

    # ---------- Payroll Cycle Settings ----------
    cycle_type  = Column(Enum(CycleType),  nullable=False, default=CycleType.MONTHLY)
    pay_period  = Column(Enum(PayPeriod),  nullable=False, default=PayPeriod.STANDARD_MONTH)

    # For CUSTOM_DATE_RANGE pay period
    period_start_day = Column(Integer, nullable=True)   # e.g. 26 (of previous month)
    period_end_day   = Column(Integer, nullable=True)   # e.g. 25 (of current month)

    # ---------- Payroll Schedule ----------
    processing_day = Column(Integer, nullable=False, default=25)   # day-of-month
    payment_day    = Column(Integer, nullable=False, default=30)   # day-of-month

    # Off-cycle & advance scheduling flags
    enable_off_cycle_payroll        = Column(Boolean, default=True,  nullable=False)
    enable_advance_payroll_scheduling = Column(Boolean, default=False, nullable=False)

    # ---------- Payroll Lock / Status Banner ----------
    payroll_status   = Column(Enum(PayrollStatus), nullable=False,
                              default=PayrollStatus.ACTIVE)
    locked_by        = Column(Integer, ForeignKey("employees.id"), nullable=True)
    locked_at        = Column(DateTime, nullable=True)
    lock_reason      = Column(String(500), nullable=True)

    # ---------- Lifecycle ----------
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    def __repr__(self) -> str:
        return f"<PayrollConfig id={self.id} status={self.payroll_status} cycle={self.cycle_type}>"


# ---------------------------------------------------------------------------
# 2. Sales / Commission Configuration
# ---------------------------------------------------------------------------

class CommissionConfig(Base):
    """
    Sales / Commission Configuration section.
    One active row per company (same singleton pattern as PayrollConfig).
    """
    __tablename__ = "commission_config"

    id = Column(Integer, primary_key=True, index=True)

    enable_commission_calculation = Column(Boolean, default=False, nullable=False)
    commission_rate_percent        = Column(Float, nullable=True, default=5.0)   # e.g. 5 → 5 %
    bonus_threshold                = Column(Numeric(14, 2), nullable=True,
                                            default=100000)                       # in company currency

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    def __repr__(self) -> str:
        return (f"<CommissionConfig enabled={self.enable_commission_calculation} "
                f"rate={self.commission_rate_percent}%>")


# ---------------------------------------------------------------------------
# 3. Statutory Compliance Settings
# ---------------------------------------------------------------------------

class StatutorySettings(Base):
    """
    Statutory Compliance Settings section — four on/off toggles visible in the UI.
    Singleton per company.
    """
    __tablename__ = "statutory_settings"

    id = Column(Integer, primary_key=True, index=True)

    enable_tax_calculation = Column(Boolean, default=True,  nullable=False)
    enable_epf_contribution = Column(Boolean, default=True,  nullable=False)
    enable_esi_contribution  = Column(Boolean, default=True,  nullable=False)
    enable_tds_deduction     = Column(Boolean, default=True,  nullable=False)

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    def __repr__(self) -> str:
        return (f"<StatutorySettings tax={self.enable_tax_calculation} "
                f"epf={self.enable_epf_contribution} "
                f"esi={self.enable_esi_contribution} "
                f"tds={self.enable_tds_deduction}>")


# ---------------------------------------------------------------------------
# 4. Salary Component Configuration  (the table at the bottom of the page)
# ---------------------------------------------------------------------------

class PayrollComponent(Base):
    """
    Salary Component Configuration table rows.
    Each row maps directly to one line in the UI table:
        Component Name | Type | Calculation | Value | Taxable | Actions
    
    NOTE: This is a *processing-level* component config (simpler, flat) that
    complements the full Salary Structure module's SalaryComponent master.
    It is the source of truth for the Payroll Processing page's component table.
    """
    __tablename__ = "payroll_components"

    id             = Column(Integer, primary_key=True, index=True)
    component_name = Column(String(255), nullable=False)
    component_type = Column(Enum(ComponentType), nullable=False,
                            default=ComponentType.EARNINGS, index=True)

    calculation_method = Column(Enum(CalculationMethod), nullable=False,
                                default=CalculationMethod.PERCENTAGE)

    # Value: percentage (0-100) OR flat monetary amount — interpreted by calculation_method
    value     = Column(Float, nullable=False, default=0.0)
    is_taxable = Column(Boolean, default=False, nullable=False)

    # Ordering in the table
    display_order = Column(Integer, default=0)

    # Lifecycle
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


# ---------------------------------------------------------------------------
# 5. Payroll Lock Audit Log
# ---------------------------------------------------------------------------

class PayrollLockLog(Base):
    """
    Immutable audit trail for every Lock / Unlock action on payroll.
    Created automatically by the service layer — never directly by the API.
    """
    __tablename__ = "payroll_lock_logs"

    id         = Column(Integer, primary_key=True, index=True)
    action     = Column(Enum(LockAction), nullable=False)
    reason     = Column(String(500), nullable=True)
    actioned_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    actioned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Snapshot of status before and after
    previous_status = Column(String(50), nullable=False)
    new_status      = Column(String(50), nullable=False)

    __table_args__ = (
        Index("ix_pll_actioned_at", "actioned_at"),
        Index("ix_pll_action", "action"),
    )

    def __repr__(self) -> str:
        return f"<PayrollLockLog {self.action} at={self.actioned_at}>"