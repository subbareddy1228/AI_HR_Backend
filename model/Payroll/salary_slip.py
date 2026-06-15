from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    Numeric, Text, ForeignKey, Index
)
from core.database import Base
from datetime import datetime


class SalarySlip(Base):
    __tablename__ = "salary_slips"

    id = Column(Integer, primary_key=True, index=True)

    # ── Employee snapshot (frozen at generation time) ──────────────────────
    employee_id       = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    payroll_run_id    = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)
    slip_month        = Column(Integer, nullable=False)   # 1-12
    slip_year         = Column(Integer, nullable=False)
    employee_code     = Column(String(100), nullable=False)
    employee_name     = Column(String(255), nullable=False)
    department        = Column(String(255), nullable=True)
    designation       = Column(String(255), nullable=True)
    pan_number        = Column(String(20),  nullable=True)   # for Form 16
    uan_number        = Column(String(30),  nullable=True)   # for PF ECR
    bank_account      = Column(String(100), nullable=True)   # masked last 4
    bank_name         = Column(String(255), nullable=True)
    official_email    = Column(String(255), nullable=True)

    # ── Attendance ─────────────────────────────────────────────────────────
    days_in_month     = Column(Integer, nullable=False, default=30)
    days_worked       = Column(Integer, nullable=False, default=0)
    days_absent       = Column(Integer, nullable=False, default=0)
    lop_days          = Column(Integer, nullable=False, default=0)  # Loss of Pay

    # ── Computed totals ────────────────────────────────────────────────────
    gross_salary      = Column(Numeric(12, 2), nullable=False)
    total_earnings    = Column(Numeric(12, 2), nullable=False)
    total_deductions  = Column(Numeric(12, 2), nullable=False)
    net_pay           = Column(Numeric(12, 2), nullable=False)

    # ── Status flags ───────────────────────────────────────────────────────
    is_published      = Column(Boolean, default=False)   # visible to employee
    is_emailed        = Column(Boolean, default=False)
    pdf_path          = Column(String(500), nullable=True)  # S3 key or server path

    # ── Audit ──────────────────────────────────────────────────────────────
    generated_at      = Column(DateTime, default=datetime.utcnow)
    generated_by      = Column(String(255), nullable=True)  # HR user email
    is_deleted        = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_salary_slips_emp_period", "employee_id", "slip_month", "slip_year", unique=True),
    )


class SalarySlipComponent(Base):
    __tablename__ = "salary_slip_components"

    id               = Column(Integer, primary_key=True, index=True)
    salary_slip_id   = Column(Integer, ForeignKey("salary_slips.id", ondelete="CASCADE"), nullable=False, index=True)
    component_type   = Column(String(20), nullable=False)    # 'earning' | 'deduction'
    component_name   = Column(String(100), nullable=False)   # e.g. 'Basic Salary'
    component_code   = Column(String(50),  nullable=True)    # e.g. 'BASIC', 'PF_EMP'
    amount           = Column(Numeric(12, 2), nullable=False)
    is_statutory     = Column(Boolean, default=False)        # PF / ESI / PT / TDS / LWF
    sort_order       = Column(Integer, default=0)
