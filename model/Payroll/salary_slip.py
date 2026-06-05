# FILE 3 of 18 | model/Payroll/salary_slip.py
# Model: SalarySlip
# Table: salary_slips

# from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Text, ForeignKey
# from core.database import Base
# from datetime import datetime


# class SalarySlip(Base):
#     __tablename__ = "salary_slips"

#     id = Column(Integer, primary_key=True, index=True)
#     employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)
#     slip_month = Column(Integer, nullable=False)
#     slip_year = Column(Integer, nullable=False)
#     employee_code = Column(String(100), nullable=False)
#     employee_name = Column(String(255), nullable=False)
#     department = Column(String(255), nullable=True)
#     designation = Column(String(255), nullable=True)
#     bank_account = Column(String(100), nullable=True)
#     bank_name = Column(String(255), nullable=True)
#     gross_salary = Column(Numeric(10, 2), nullable=False)
#     total_deductions = Column(Numeric(10, 2), nullable=False)
#     net_pay = Column(Numeric(10, 2), nullable=False)
#     earnings_json = Column(Text, nullable=True)   # JSON string of earnings breakdown
#     deductions_json = Column(Text, nullable=True)  # JSON string of deductions breakdown
#     generated_at = Column(DateTime, default=datetime.utcnow)
#     is_published = Column(Boolean, default=False)



from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Numeric,
    Text,
    ForeignKey
)

from core.database import Base
from datetime import datetime


class SalarySlip(Base):
    __tablename__ = "salary_slips"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )

    payroll_run_id = Column(
        Integer,
        ForeignKey("payroll_runs.id"),
        nullable=True
    )

    slip_month = Column(Integer, nullable=False)
    slip_year = Column(Integer, nullable=False)

    employee_code = Column(String(100), nullable=False)
    employee_name = Column(String(255), nullable=False)

    department = Column(String(255))
    designation = Column(String(255))

    bank_account = Column(String(100))
    bank_name = Column(String(255))

    gross_salary = Column(Numeric(10, 2), nullable=False)
    total_deductions = Column(Numeric(10, 2), nullable=False)
    net_pay = Column(Numeric(10, 2), nullable=False)

    earnings_json = Column(Text)
    deductions_json = Column(Text)

    generated_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    is_published = Column(
        Boolean,
        default=False
    )

    is_distributed = Column(
        Boolean,
        default=False
    )

    distribution_method = Column(
        String(50),
        nullable=True
    )

    distributed_at = Column(
        DateTime,
        nullable=True
    )

    password_protected = Column(
        Boolean,
        default=False
    )

    email_sent = Column(
        Boolean,
        default=False
    )

    pdf_path = Column(
        String(500),
        nullable=True
    )