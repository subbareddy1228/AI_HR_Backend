
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Text, ForeignKey
from core.database import Base
from datetime import datetime


class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_month = Column(Integer, nullable=False)  # 1-12
    run_year = Column(Integer, nullable=False)
    status = Column(String(50), default="Draft")  # Draft/Processing/Approved/Paid
    total_employees = Column(Integer, default=0)
    total_gross = Column(Numeric(14, 2), default=0)
    total_deductions = Column(Numeric(14, 2), default=0)
    total_net_pay = Column(Numeric(14, 2), default=0)
    run_by = Column(String(255), nullable=True)
    approved_by = Column(String(255), nullable=True)
    run_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)


class PayrollRunDetail(Base):
    __tablename__ = "payroll_run_details"

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    employee_code = Column(String(100), nullable=False)
    employee_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    designation = Column(String(255), nullable=True)
    days_in_month = Column(Integer, nullable=False)
    days_worked = Column(Integer, nullable=False)
    days_absent = Column(Integer, nullable=False)
    basic = Column(Numeric(10, 2), nullable=False)
    hra = Column(Numeric(10, 2), nullable=False)
    special_allowance = Column(Numeric(10, 2), nullable=False)
    gross_salary = Column(Numeric(10, 2), nullable=False)
    pf_employee = Column(Numeric(10, 2), nullable=False)
    esi_employee = Column(Numeric(10, 2), nullable=False)
    professional_tax = Column(Numeric(10, 2), nullable=False)
    tds = Column(Numeric(10, 2), nullable=False)
    total_deductions = Column(Numeric(10, 2), nullable=False)
    net_pay = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), default="Pending")