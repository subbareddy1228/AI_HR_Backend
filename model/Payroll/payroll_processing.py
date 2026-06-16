from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey, func
)
from sqlalchemy.orm import relationship

from core.database import Base


class PayrollConfig(Base):
    """
    Single-row configuration table for the Payroll Processing Engine.
    Covers Payroll Cycle Configuration, Schedule, Sales/Commission,
    and Statutory Compliance Settings visible on the UI.
    """
    __tablename__ = "payroll_config"

    id                          = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ── Payroll Status ────────────────────────────────────────────────────────
    # ACTIVE | LOCKED
    payroll_status              = Column(String(20), nullable=False, default="ACTIVE")

    # ── Payroll Cycle Settings ────────────────────────────────────────────────
    # Cycle Type: Monthly | Weekly | Bi-weekly | Semi-monthly
    cycle_type                  = Column(String(50), nullable=False, default="Monthly")
    # Pay Period: Standard Month (1st - Last) | Custom
    pay_period                  = Column(String(100), nullable=False, default="Standard Month (1st - Last)")

    # ── Payroll Schedule ──────────────────────────────────────────────────────
    processing_day              = Column(Integer, nullable=False, default=25)   # day of month e.g. 25
    payment_day                 = Column(Integer, nullable=False, default=30)   # day of month e.g. 30
    enable_off_cycle_payroll    = Column(Boolean, nullable=False, default=True)
    # Off-cycle covers: Bonuses, Advances, Exit Settlements
    enable_advance_scheduling   = Column(Boolean, nullable=False, default=False)

    # ── Sales / Commission Configuration ─────────────────────────────────────
    enable_commission           = Column(Boolean, nullable=False, default=True)
    commission_rate             = Column(Float, nullable=False, default=5.0)    # % e.g. 5
    bonus_threshold             = Column(Float, nullable=False, default=100000.0)

    # ── Statutory Compliance Settings ─────────────────────────────────────────
    enable_tax_calculation      = Column(Boolean, nullable=False, default=True)
    enable_epf_contribution     = Column(Boolean, nullable=False, default=True)
    enable_esi_contribution     = Column(Boolean, nullable=False, default=True)
    enable_tds_deduction        = Column(Boolean, nullable=False, default=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at                  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at                  = Column(DateTime(timezone=True), server_default=func.now(),
                                         onupdate=func.now(), nullable=False)


class SalaryComponent(Base):
    """
    Salary Component Configuration table visible on the UI.
    Each row is an earning or deduction component used during payroll calculation.
    """
    __tablename__ = "salary_components"

    id               = Column(Integer, primary_key=True, index=True, autoincrement=True)

    component_name   = Column(String(200), nullable=False)
    # Type: earnings | deductions
    component_type   = Column(String(50), nullable=False)
    # Calculation: percentage | fixed
    calculation_type = Column(String(50), nullable=False)
    # Value: e.g. 50 (for 50%) or 1600.0 (for fixed ₹1600)
    value            = Column(Float, nullable=False)
    is_taxable       = Column(Boolean, nullable=False, default=False)
    is_active        = Column(Boolean, nullable=False, default=True)
    description      = Column(Text, nullable=True)
    # Sort order for display
    display_order    = Column(Integer, nullable=False, default=0)

    # Audit
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now(), nullable=False)